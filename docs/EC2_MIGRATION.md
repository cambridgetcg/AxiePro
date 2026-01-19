# EC2 Migration Plan for Gap Backfill

**Date:** 2025-12-20
**Status:** Ready to Execute

## Current State

### Local (Mac)
- Backfill running: PID 2485
- Progress: Block 45,766,998 / 51,313,844
- Rate: 4.3 blk/s
- ETA: ~362 hours (~15 days)

### EC2 Instance
- **Instance ID:** i-0cbc98fa8fc906281
- **IP:** 3.91.12.195
- **Type:** t3.micro (1 vCPU, 1GB RAM)
- **Status:** Running (4 days uptime)
- **Python:** 3.9.25
- **Installed:** psycopg2-binary, requests
- **Missing:** httpx

## Migration Benefits

| Aspect | Local Mac | EC2 (us-east-1) |
|--------|-----------|-----------------|
| Sleep/lid issues | Yes | No |
| RDS latency | ~80ms | ~1ms |
| Network stability | Variable | Stable |
| Cost | Free | ~$7.50/month |
| Unattended | No | Yes |

## Migration Steps

### Step 1: Install Dependencies on EC2
```bash
ssh ec2-user@3.91.12.195 "pip3 install --user httpx"
```

### Step 2: Deploy Backfill Script
```bash
scp fetch_gap_backfill.py ec2-user@3.91.12.195:/home/ec2-user/axie/
```

### Step 3: Kill Local Process
```bash
kill <local_pid>
```

### Step 4: Start on EC2
```bash
ssh ec2-user@3.91.12.195 "cd /home/ec2-user/axie && \
  nohup python3 -u fetch_gap_backfill.py --resume > gap_backfill.log 2>&1 &"
```

### Step 5: Verify
```bash
ssh ec2-user@3.91.12.195 "pgrep -a python && tail -20 /home/ec2-user/axie/gap_backfill.log"
```

## Monitoring Commands

```bash
# Check status
./ec2/scripts/check-job.sh fetch_gap_backfill.py

# View live log
./ec2/scripts/ssh.sh "tail -f /home/ec2-user/axie/gap_backfill.log"

# Check DB progress
PGPASSWORD="12345Cardforum" psql -h cardforum.cn4c2su0o42n.us-east-1.rds.amazonaws.com \
  -U postgres -d postgres -c "SELECT * FROM axie.sync_state WHERE id = 'gap_backfill';"

# SSH to instance
./ec2/scripts/ssh.sh
```

## Rollback

If EC2 fails, resume locally:
```bash
source backend/venv/bin/activate
PYTHONUNBUFFERED=1 python3 fetch_gap_backfill.py --resume
```

## Expected Performance Improvement

EC2 in same region as RDS should reduce latency significantly:
- Local: ~4.3 blk/s (80ms RDS latency + API calls)
- EC2: Expected 6-10 blk/s (1ms RDS latency)
- Potential ETA reduction: 15 days → 10 days

## Cost Estimate

- t3.micro: $0.0104/hour
- 15 days continuous: $0.0104 × 24 × 15 = $3.74
- Already running: included in existing cost
