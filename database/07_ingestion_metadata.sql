-- AxiePro Database Schema - Ingestion Metadata
-- Run after 06_valuation_tables.sql
--
-- PURPOSE: Track ingestion progress for blockchain-based data fetching
--
-- This table stores key-value metadata for Lambda ingestion functions,
-- primarily tracking the last processed block number for resumable syncs.

SET search_path TO axie, public;

-- ============================================
-- 1. INGESTION METADATA TABLE
-- Simple key-value store for ingestion state
-- ============================================
CREATE TABLE IF NOT EXISTS ingestion_metadata (
    key             VARCHAR(100) PRIMARY KEY,
    value           TEXT NOT NULL,
    updated_at      TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    created_at      TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Index for cleanup queries
CREATE INDEX IF NOT EXISTS idx_ingestion_metadata_updated
    ON ingestion_metadata(updated_at);

-- ============================================
-- 2. INITIAL VALUES
-- ============================================
-- These will be set by the Lambda functions on first run

INSERT INTO ingestion_metadata (key, value)
VALUES
    ('sales_last_block', '0'),
    ('listings_last_block', '0')
ON CONFLICT (key) DO NOTHING;

-- ============================================
-- 3. HELPER FUNCTIONS
-- ============================================

-- Function: Get ingestion metadata value
CREATE OR REPLACE FUNCTION get_ingestion_meta(p_key VARCHAR(100))
RETURNS TEXT AS $$
BEGIN
    RETURN (SELECT value FROM ingestion_metadata WHERE key = p_key);
END;
$$ LANGUAGE plpgsql;

-- Function: Set ingestion metadata value
CREATE OR REPLACE FUNCTION set_ingestion_meta(p_key VARCHAR(100), p_value TEXT)
RETURNS VOID AS $$
BEGIN
    INSERT INTO ingestion_metadata (key, value, updated_at)
    VALUES (p_key, p_value, NOW())
    ON CONFLICT (key) DO UPDATE SET
        value = EXCLUDED.value,
        updated_at = EXCLUDED.updated_at;
END;
$$ LANGUAGE plpgsql;

-- ============================================
-- COMMENTS
-- ============================================

COMMENT ON TABLE ingestion_metadata IS 'Key-value store for tracking Lambda ingestion progress (block numbers, timestamps, etc.)';
COMMENT ON FUNCTION get_ingestion_meta IS 'Get an ingestion metadata value by key';
COMMENT ON FUNCTION set_ingestion_meta IS 'Set an ingestion metadata value (upsert)';

SELECT 'Ingestion metadata schema created successfully' as status;
