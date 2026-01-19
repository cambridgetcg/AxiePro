"""
Axie Fetch Pipeline Orchestrator (Simplified)

Manages EC2-based Axie sales fetching pipeline.
Uses SSM to communicate with EC2, no direct database access needed.

Triggered by: EventBridge (hourly schedule)
"""

import json
import boto3
import os
import time
from datetime import datetime

# AWS clients
ec2 = boto3.client('ec2', region_name='us-east-1')
ssm = boto3.client('ssm', region_name='us-east-1')

# Configuration
EC2_INSTANCE_ID = os.environ.get('EC2_INSTANCE_ID', 'i-0cbc98fa8fc906281')
REMOTE_DIR = '/home/ec2-user/axie'


def get_ec2_state():
    """Get current EC2 instance state."""
    try:
        response = ec2.describe_instances(InstanceIds=[EC2_INSTANCE_ID])
        state = response['Reservations'][0]['Instances'][0]['State']['Name']
        return state
    except Exception as e:
        print(f"EC2 state check error: {e}")
        return 'unknown'


def start_ec2():
    """Start the EC2 instance and wait for it to be ready."""
    state = get_ec2_state()
    if state == 'running':
        print("EC2 already running")
        return True

    if state == 'stopped':
        print("Starting EC2 instance...")
        ec2.start_instances(InstanceIds=[EC2_INSTANCE_ID])
        waiter = ec2.get_waiter('instance_running')
        waiter.wait(InstanceIds=[EC2_INSTANCE_ID])
        print("EC2 instance started, waiting for SSM agent...")
        time.sleep(45)
        return True

    print(f"EC2 in unexpected state: {state}")
    return False


def stop_ec2():
    """Stop the EC2 instance to save costs."""
    state = get_ec2_state()
    if state == 'stopped':
        print("EC2 already stopped")
        return True

    if state == 'running':
        print("Stopping EC2 instance...")
        ec2.stop_instances(InstanceIds=[EC2_INSTANCE_ID])
        return True

    return False


def run_ssm_command(command, timeout=60):
    """Run a shell command on EC2 via SSM."""
    try:
        response = ssm.send_command(
            InstanceIds=[EC2_INSTANCE_ID],
            DocumentName='AWS-RunShellScript',
            Parameters={'commands': [command]},
            TimeoutSeconds=timeout
        )
        command_id = response['Command']['CommandId']

        for _ in range(timeout // 2):
            time.sleep(2)
            try:
                result = ssm.get_command_invocation(
                    CommandId=command_id,
                    InstanceId=EC2_INSTANCE_ID
                )
                if result['Status'] in ['Success', 'Failed', 'TimedOut', 'Cancelled']:
                    return {
                        'status': result['Status'],
                        'stdout': result.get('StandardOutputContent', ''),
                        'stderr': result.get('StandardErrorContent', '')
                    }
            except ssm.exceptions.InvocationDoesNotExist:
                continue

        return {'status': 'Timeout', 'stdout': '', 'stderr': ''}

    except Exception as e:
        print(f"SSM command error: {e}")
        return {'status': 'Error', 'stdout': '', 'stderr': str(e)}


def check_running_fetch():
    """Check if a fetch job is currently running on EC2."""
    result = run_ssm_command("pgrep -f 'fetch_continuous.py' && echo 'FETCH_ACTIVE' || echo 'FETCH_INACTIVE'")
    if result['status'] == 'Success':
        return 'FETCH_ACTIVE' in result['stdout']
    return False


def get_job_status():
    """Get status of current/last job from EC2."""
    result = run_ssm_command(f"cat {REMOTE_DIR}/current_job.json 2>/dev/null || echo 'NO_JOB'")

    if result['status'] == 'Success' and 'NO_JOB' not in result['stdout']:
        try:
            return json.loads(result['stdout'].strip())
        except:
            pass

    return None


def get_next_pending_job():
    """Get next pending job from database via EC2."""
    result = run_ssm_command(f"python3 {REMOTE_DIR}/get_pending_job.py", timeout=30)

    if result['status'] == 'Success' and 'NO_PENDING_JOB' not in result['stdout']:
        try:
            return json.loads(result['stdout'].strip())
        except:
            pass

    return None


def start_fetch_job(job):
    """Start a fetch job on EC2."""
    job_id = job['job_id']

    # Mark job as running in database
    run_ssm_command(f"python3 {REMOTE_DIR}/start_job.py {job_id} {EC2_INSTANCE_ID}", timeout=15)

    # Save current job info
    job_info = json.dumps(job)
    run_ssm_command(f"echo '{job_info}' > {REMOTE_DIR}/current_job.json")

    # Start the fetch script
    start_cmd = f"cd {REMOTE_DIR} && nohup python3 -u fetch_continuous.py --job-id {job['job_id']} --start-block {job['start_block']} --end-block {job['end_block']} > fetch_continuous.log 2>&1 &"

    result = run_ssm_command(start_cmd)
    return result['status'] == 'Success'


def check_job_completion():
    """Check if the running job has completed."""
    result = run_ssm_command(f"tail -5 {REMOTE_DIR}/fetch_continuous.log 2>/dev/null")

    if result['status'] == 'Success':
        output = result['stdout']
        if 'COMPLETE' in output:
            return 'completed'
        if 'Error' in output or 'Exception' in output:
            return 'failed'

    return 'running'


def clear_job_marker():
    """Clear the current job marker file."""
    run_ssm_command(f"rm -f {REMOTE_DIR}/current_job.json")


def lambda_handler(event, context):
    """Main Lambda handler."""
    print(f"Orchestrator triggered at {datetime.utcnow().isoformat()}")

    result = {
        'status': 'ok',
        'action': None,
        'job': None,
        'timestamp': datetime.utcnow().isoformat()
    }

    try:
        ec2_state = get_ec2_state()
        print(f"EC2 state: {ec2_state}")

        if ec2_state == 'running':
            if check_running_fetch():
                print("Fetch job is running")

                status = check_job_completion()
                if status == 'completed':
                    print("Job completed!")
                    clear_job_marker()
                    result['action'] = 'job_completed'

                    next_job = get_next_pending_job()
                    if next_job:
                        print(f"Starting next job: {next_job['job_name']}")
                        if start_fetch_job(next_job):
                            result['next_job'] = next_job['job_name']
                    else:
                        print("No more pending jobs, stopping EC2")
                        stop_ec2()
                        result['action'] = 'all_jobs_complete'

                elif status == 'failed':
                    print("Job failed!")
                    result['action'] = 'job_failed'

                else:
                    result['action'] = 'monitoring'
                    job = get_job_status()
                    if job:
                        result['job'] = job.get('job_name')

            else:
                print("EC2 running but no fetch job active")

                pending_job = get_next_pending_job()
                if pending_job:
                    print(f"Starting job: {pending_job['job_name']}")
                    if start_fetch_job(pending_job):
                        result['action'] = 'started_job'
                        result['job'] = pending_job['job_name']
                    else:
                        result['action'] = 'failed_to_start'
                else:
                    print("No pending jobs, stopping idle EC2")
                    stop_ec2()
                    result['action'] = 'stopped_idle_ec2'

        elif ec2_state == 'stopped':
            print("EC2 is stopped, checking for pending jobs")

            if start_ec2():
                pending_job = get_next_pending_job()
                if pending_job:
                    print(f"Starting job: {pending_job['job_name']}")
                    if start_fetch_job(pending_job):
                        result['action'] = 'started_job'
                        result['job'] = pending_job['job_name']
                else:
                    print("No pending jobs, stopping EC2")
                    stop_ec2()
                    result['action'] = 'no_pending_jobs'
            else:
                result['action'] = 'ec2_start_failed'
                result['status'] = 'error'

        else:
            print(f"EC2 in transitional state: {ec2_state}")
            result['action'] = 'waiting'

    except Exception as e:
        print(f"Error: {e}")
        result['status'] = 'error'
        result['error'] = str(e)

    print(f"Result: {result}")
    return result
