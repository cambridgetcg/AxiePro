# Axie Data Fetch Pipeline - Lambda Architecture

## Overview

Automated pipeline to continuously fetch Axie sales data from the Ronin blockchain.
Uses Lambda for orchestration and EC2 for heavy processing (avoiding Lambda's 15-min timeout).

## Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           SCHEDULED PIPELINE                                │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│   EventBridge                    Lambda                      EC2            │
│   ┌─────────┐              ┌─────────────────┐         ┌──────────────┐    │
│   │ Schedule│──(hourly)───►│ axie-fetch-     │────────►│ axie-fetcher │    │
│   │ Rule    │              │ orchestrator    │ start   │ (t3.micro)   │    │
│   └─────────┘              └────────┬────────┘         └──────┬───────┘    │
│                                     │                         │            │
│                                     │ check/update            │ fetch      │
│                                     ▼                         ▼            │
│                            ┌─────────────────┐         ┌──────────────┐    │
│                            │     RDS         │◄────────│ Sky Mavis    │    │
│                            │  PostgreSQL     │ insert  │    API       │    │
│                            │                 │         └──────────────┘    │
│                            │ • fetch_jobs    │                             │
│                            │ • axie_sales    │                             │
│                            │ • axie_metadata │                             │
│                            └─────────────────┘                             │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

## Components

### 1. EventBridge Rule
- **Schedule**: Every hour (rate(1 hour))
- **Target**: Lambda orchestrator
- **Purpose**: Regular check for new blocks to process

### 2. Lambda Orchestrator (`axie-fetch-orchestrator`)
- **Runtime**: Python 3.12
- **Timeout**: 5 minutes (only orchestration, no heavy work)
- **Memory**: 256 MB
- **Responsibilities**:
  - Check for active jobs in `fetch_jobs` table
  - Calculate next block range if work pending
  - Start/stop EC2 instance
  - Update job status
  - Trigger metadata fetch on completion

### 3. EC2 Worker (`axie-fetcher`)
- **Instance**: t3.micro (existing)
- **Purpose**: Run long-running fetch scripts
- **Auto-managed**: Started/stopped by Lambda
- **Scripts**: fetch_june2025_parallel.py (parameterized)

### 4. RDS Tables

#### `fetch_jobs` (new table)
```sql
CREATE TABLE axie.fetch_jobs (
    job_id          SERIAL PRIMARY KEY,
    job_type        VARCHAR(50) NOT NULL,      -- 'historical', 'incremental'
    start_block     BIGINT NOT NULL,
    end_block       BIGINT NOT NULL,
    current_block   BIGINT,
    status          VARCHAR(20) DEFAULT 'pending',  -- pending, running, completed, failed
    ec2_instance_id VARCHAR(50),
    started_at      TIMESTAMP,
    completed_at    TIMESTAMP,
    sales_found     INTEGER DEFAULT 0,
    error_message   TEXT,
    created_at      TIMESTAMP DEFAULT NOW()
);
```

## Job Types

### Historical Backfill
- One-time jobs to fetch past data
- Example: July-December 2025 after June completes
- Runs until end_block reached, then marks complete

### Incremental (Future)
- Continuous jobs to stay current
- Runs daily/hourly to fetch new blocks
- end_block = latest chain block

## Flow

```
1. EventBridge triggers Lambda (hourly)
2. Lambda checks fetch_jobs table:

   IF no running job AND pending jobs exist:
      - Get highest priority pending job
      - Start EC2 instance
      - Update job status to 'running'
      - EC2 runs fetch script with job parameters

   IF job running:
      - Check EC2 status
      - If EC2 stopped unexpectedly → mark failed, restart
      - If progress file exists → update current_block

   IF job completed (progress file shows 100%):
      - Stop EC2 instance
      - Mark job complete
      - Queue metadata fetch for new sales
      - Check for next pending job

3. EC2 runs fetch_continuous.py:
   - Reads job parameters from RDS
   - Fetches blocks start_block → end_block
   - Updates progress in RDS periodically
   - Exits when complete
```

## Block Ranges to Process

| Period | Start Block | End Block | Est. Sales | Est. Time |
|--------|-------------|-----------|------------|-----------|
| June 2025 | 45,626,000 | 46,461,000 | ~22,000 | ~2h (done) |
| July 2025 | 46,461,001 | 47,296,000 | ~22,000 | ~2h |
| Aug 2025 | 47,296,001 | 48,182,000 | ~22,000 | ~2h |
| Sep 2025 | 48,182,001 | 49,018,000 | ~22,000 | ~2h |
| Oct 2025 | 49,018,001 | 49,904,000 | ~22,000 | ~2h |
| Nov 2025 | 49,904,001 | 50,740,000 | ~22,000 | ~2h |
| Dec 2025 | 50,740,001 | 51,322,583 | ~15,000 | ~1.5h |

**Total remaining**: ~4.86M blocks, ~13 hours of processing

## Cost Analysis

| Component | Cost |
|-----------|------|
| Lambda (hourly checks) | ~$0.10/month |
| EC2 t3.micro (13h total) | ~$0.14 |
| RDS (existing) | $0 additional |
| Data transfer | ~$0.05 |
| **Total for backfill** | **~$0.30** |

## Deployment Steps

1. Create `fetch_jobs` table in RDS
2. Create Lambda function with IAM role
3. Create parameterized fetch script for EC2
4. Set up EventBridge rule
5. Insert initial job records for July-Dec 2025
6. Enable pipeline
