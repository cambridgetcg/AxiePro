-- AxiePro Database Schema - Sync State Enhancements
-- Run after 02_create_analysis_tables.sql
-- Adds columns for enhanced checkpoint tracking

SET search_path TO axie, public;

-- ============================================
-- ENHANCE SYNC_STATE TABLE
-- ============================================

-- Add error tracking columns
ALTER TABLE sync_state
ADD COLUMN IF NOT EXISTS error_count INTEGER DEFAULT 0,
ADD COLUMN IF NOT EXISTS last_error TEXT,
ADD COLUMN IF NOT EXISTS processing_rate NUMERIC(10, 2);

COMMENT ON COLUMN sync_state.error_count IS 'Number of errors during sync';
COMMENT ON COLUMN sync_state.last_error IS 'Last error message';
COMMENT ON COLUMN sync_state.processing_rate IS 'Blocks per second processing rate';

-- ============================================
-- RPC METRICS TABLE
-- Track provider performance for optimization
-- ============================================

CREATE TABLE IF NOT EXISTS rpc_metrics (
    id BIGSERIAL PRIMARY KEY,
    provider VARCHAR(50) NOT NULL,
    request_type VARCHAR(50) NOT NULL,
    response_time_ms INTEGER,
    success BOOLEAN DEFAULT TRUE,
    error_message TEXT,
    blocks_fetched INTEGER,
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_rpc_metrics_provider
ON rpc_metrics(provider, created_at DESC);

CREATE INDEX IF NOT EXISTS idx_rpc_metrics_time
ON rpc_metrics(created_at DESC);

COMMENT ON TABLE rpc_metrics IS 'RPC provider performance metrics for optimization';

-- ============================================
-- FETCH JOBS TABLE (Enhanced)
-- For parallel job orchestration
-- ============================================

CREATE TABLE IF NOT EXISTS fetch_jobs (
    id SERIAL PRIMARY KEY,
    job_type VARCHAR(50) NOT NULL DEFAULT 'sales_fetch',

    -- Block range
    start_block BIGINT NOT NULL,
    end_block BIGINT NOT NULL,
    current_block BIGINT,

    -- Progress
    status VARCHAR(20) DEFAULT 'pending',  -- pending, running, completed, failed
    records_found INTEGER DEFAULT 0,
    records_inserted INTEGER DEFAULT 0,

    -- Timing
    created_at TIMESTAMP DEFAULT NOW(),
    started_at TIMESTAMP,
    completed_at TIMESTAMP,

    -- Error tracking
    error_count INTEGER DEFAULT 0,
    last_error TEXT,

    -- Performance
    processing_rate NUMERIC(10, 2)
);

CREATE INDEX IF NOT EXISTS idx_fetch_jobs_status
ON fetch_jobs(status, created_at DESC);

-- ============================================
-- HELPER FUNCTIONS
-- ============================================

-- Update job progress
CREATE OR REPLACE FUNCTION update_job_progress(
    p_job_id INTEGER,
    p_current_block BIGINT,
    p_records_found INTEGER,
    p_records_inserted INTEGER
) RETURNS VOID AS $$
BEGIN
    UPDATE fetch_jobs
    SET current_block = p_current_block,
        records_found = p_records_found,
        records_inserted = p_records_inserted,
        status = 'running'
    WHERE id = p_job_id;
END;
$$ LANGUAGE plpgsql;

-- Complete job
CREATE OR REPLACE FUNCTION complete_job(
    p_job_id INTEGER,
    p_records_found INTEGER,
    p_records_inserted INTEGER
) RETURNS VOID AS $$
BEGIN
    UPDATE fetch_jobs
    SET status = 'completed',
        records_found = p_records_found,
        records_inserted = p_records_inserted,
        completed_at = NOW()
    WHERE id = p_job_id;
END;
$$ LANGUAGE plpgsql;

-- Create new fetch job
CREATE OR REPLACE FUNCTION create_fetch_job(
    p_start_block BIGINT,
    p_end_block BIGINT,
    p_job_type VARCHAR DEFAULT 'sales_fetch'
) RETURNS INTEGER AS $$
DECLARE
    v_job_id INTEGER;
BEGIN
    INSERT INTO fetch_jobs (job_type, start_block, end_block, status)
    VALUES (p_job_type, p_start_block, p_end_block, 'pending')
    RETURNING id INTO v_job_id;

    RETURN v_job_id;
END;
$$ LANGUAGE plpgsql;

SELECT 'Sync state enhancements applied successfully' as status;
