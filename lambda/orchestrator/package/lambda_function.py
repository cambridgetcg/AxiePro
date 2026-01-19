"""
Axie Fetch Pipeline Orchestrator

This Lambda function orchestrates the Axie sales data fetching pipeline:
1. Checks for pending jobs in the fetch_jobs table
2. Starts EC2 instance to run fetch scripts
3. Monitors job progress
4. Handles completion and failures

Triggered by: EventBridge (hourly schedule)
"""

import json
import boto3
import psycopg2
import os
import time
from datetime import datetime

# AWS clients
ec2 = boto3.client('ec2', region_name='us-east-1')
ssm = boto3.client('ssm', region_name='us-east-1')
secrets = boto3.client('secretsmanager', region_name='us-east-1')

# Configuration
EC2_INSTANCE_ID = os.environ.get('EC2_INSTANCE_ID', 'i-0cbc98fa8fc906281')
FETCH_SCRIPT = '/home/ec2-user/axie/fetch_continuous.py'


def get_db_connection():
    """Get database connection using secrets."""
    try:
        secret = secrets.get_secret_value(SecretId='axie-explorer/api-keys')
        creds = json.loads(secret['SecretString'])

        return psycopg2.connect(
            host=creds.get('RDS_HOST', 'cardforum.cn4c2su0o42n.us-east-1.rds.amazonaws.com'),
            port=5432,
            dbname=creds.get('RDS_DATABASE', 'postgres'),
            user=creds.get('RDS_USER', 'postgres'),
            password=creds.get('RDS_PASSWORD', '12345Cardforum')
        )
    except Exception as e:
        print(f"DB connection error: {e}")
        raise


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
    """Start the EC2 instance."""
    state = get_ec2_state()
    if state == 'running':
        print("EC2 already running")
        return True

    if state == 'stopped':
        print("Starting EC2 instance...")
        ec2.start_instances(InstanceIds=[EC2_INSTANCE_ID])

        # Wait for running state
        waiter = ec2.get_waiter('instance_running')
        waiter.wait(InstanceIds=[EC2_INSTANCE_ID])
        print("EC2 instance started")

        # Wait a bit for SSM agent to be ready
        time.sleep(30)
        return True

    print(f"EC2 in unexpected state: {state}")
    return False


def stop_ec2():
    """Stop the EC2 instance."""
    state = get_ec2_state()
    if state == 'stopped':
        print("EC2 already stopped")
        return True

    if state == 'running':
        print("Stopping EC2 instance...")
        ec2.stop_instances(InstanceIds=[EC2_INSTANCE_ID])
        return True

    return False


def run_command_on_ec2(command):
    """Run a command on EC2 via SSM."""
    try:
        response = ssm.send_command(
            InstanceIds=[EC2_INSTANCE_ID],
            DocumentName='AWS-RunShellScript',
            Parameters={'commands': [command]},
            TimeoutSeconds=60
        )
        command_id = response['Command']['CommandId']

        # Wait for command to complete
        time.sleep(5)

        output = ssm.get_command_invocation(
            CommandId=command_id,
            InstanceId=EC2_INSTANCE_ID
        )

        return {
            'status': output['Status'],
            'stdout': output.get('StandardOutputContent', ''),
            'stderr': output.get('StandardErrorContent', '')
        }
    except Exception as e:
        print(f"SSM command error: {e}")
        return None


def get_running_job(cur):
    """Check for currently running job."""
    cur.execute("""
        SELECT job_id, job_name, start_block, end_block, current_block, ec2_instance_id
        FROM axie.fetch_jobs
        WHERE status = 'running'
        LIMIT 1
    """)
    row = cur.fetchone()
    if row:
        return {
            'job_id': row[0],
            'job_name': row[1],
            'start_block': row[2],
            'end_block': row[3],
            'current_block': row[4],
            'ec2_instance_id': row[5]
        }
    return None


def get_next_pending_job(cur):
    """Get the next pending job by priority."""
    cur.execute("""
        SELECT job_id, job_name, start_block, end_block
        FROM axie.fetch_jobs
        WHERE status = 'pending'
        ORDER BY priority ASC
        LIMIT 1
    """)
    row = cur.fetchone()
    if row:
        return {
            'job_id': row[0],
            'job_name': row[1],
            'start_block': row[2],
            'end_block': row[3]
        }
    return None


def check_job_progress(job):
    """Check progress of running job on EC2."""
    # Check if fetch process is running
    result = run_command_on_ec2("pgrep -f 'fetch_continuous.py' || echo 'not_running'")

    if not result or 'not_running' in result.get('stdout', ''):
        # Process not running - check if completed or failed
        log_result = run_command_on_ec2("tail -20 /home/ec2-user/axie/fetch_continuous.log 2>/dev/null || echo 'no_log'")

        if log_result and 'COMPLETE' in log_result.get('stdout', ''):
            return 'completed'
        elif log_result and 'no_log' not in log_result.get('stdout', ''):
            # Has log but process stopped - might have crashed
            return 'stopped'
        return 'not_started'

    return 'running'


def start_fetch_job(cur, conn, job):
    """Start a new fetch job on EC2."""
    # Start EC2 if needed
    if not start_ec2():
        return False

    # Mark job as running
    cur.execute("""
        SELECT axie.start_job(%s, %s)
    """, (job['job_id'], EC2_INSTANCE_ID))
    conn.commit()

    # Start the fetch script with job parameters
    command = f"""
        cd /home/ec2-user/axie && \
        nohup python3 -u fetch_continuous.py \
            --job-id {job['job_id']} \
            --start-block {job['start_block']} \
            --end-block {job['end_block']} \
            > fetch_continuous.log 2>&1 &
    """

    result = run_command_on_ec2(command)

    if result and result['status'] == 'Success':
        print(f"Started job {job['job_id']}: {job['job_name']}")
        return True

    print(f"Failed to start job: {result}")
    return False


def lambda_handler(event, context):
    """Main Lambda handler."""
    print(f"Orchestrator triggered at {datetime.utcnow().isoformat()}")

    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("SET search_path TO axie, public")

    result = {
        'status': 'ok',
        'action': None,
        'job': None
    }

    try:
        # Check for running job
        running_job = get_running_job(cur)

        if running_job:
            print(f"Found running job: {running_job['job_name']}")

            # Check EC2 state
            ec2_state = get_ec2_state()

            if ec2_state != 'running':
                print(f"EC2 not running (state: {ec2_state}), restarting job...")
                # EC2 stopped unexpectedly - restart it
                if start_ec2():
                    # Restart the fetch script
                    command = f"""
                        cd /home/ec2-user/axie && \
                        nohup python3 -u fetch_continuous.py \
                            --job-id {running_job['job_id']} \
                            --start-block {running_job['current_block'] or running_job['start_block']} \
                            --end-block {running_job['end_block']} \
                            > fetch_continuous.log 2>&1 &
                    """
                    run_command_on_ec2(command)
                    result['action'] = 'restarted_job'
            else:
                # Check job progress
                progress = check_job_progress(running_job)

                if progress == 'completed':
                    print("Job completed!")
                    # Get final stats from log
                    cur.execute("""
                        UPDATE axie.fetch_jobs
                        SET status = 'completed', completed_at = NOW()
                        WHERE job_id = %s
                    """, (running_job['job_id'],))
                    conn.commit()

                    # Stop EC2 to save costs
                    stop_ec2()

                    result['action'] = 'completed_job'
                    result['job'] = running_job['job_name']

                    # Check for next job
                    next_job = get_next_pending_job(cur)
                    if next_job:
                        print(f"Starting next job: {next_job['job_name']}")
                        start_fetch_job(cur, conn, next_job)
                        result['next_job'] = next_job['job_name']

                elif progress == 'stopped':
                    print("Job stopped unexpectedly, restarting...")
                    # Restart from current position
                    command = f"""
                        cd /home/ec2-user/axie && \
                        nohup python3 -u fetch_continuous.py \
                            --job-id {running_job['job_id']} \
                            --start-block {running_job['current_block'] or running_job['start_block']} \
                            --end-block {running_job['end_block']} \
                            > fetch_continuous.log 2>&1 &
                    """
                    run_command_on_ec2(command)
                    result['action'] = 'restarted_stopped_job'

                else:
                    print("Job still running")
                    result['action'] = 'monitoring'
                    result['job'] = running_job['job_name']

        else:
            # No running job - check for pending
            pending_job = get_next_pending_job(cur)

            if pending_job:
                print(f"Starting new job: {pending_job['job_name']}")
                if start_fetch_job(cur, conn, pending_job):
                    result['action'] = 'started_new_job'
                    result['job'] = pending_job['job_name']
                else:
                    result['action'] = 'failed_to_start'
                    result['status'] = 'error'
            else:
                print("No pending jobs")
                result['action'] = 'no_work'

                # Make sure EC2 is stopped to save costs
                if get_ec2_state() == 'running':
                    print("Stopping idle EC2...")
                    stop_ec2()

    except Exception as e:
        print(f"Error: {e}")
        result['status'] = 'error'
        result['error'] = str(e)

    finally:
        cur.close()
        conn.close()

    print(f"Result: {result}")
    return result
