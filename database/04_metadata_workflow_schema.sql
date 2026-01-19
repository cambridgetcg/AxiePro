-- AxiePro Database Schema - Metadata Workflow Integration
-- Run after 03_create_views_functions.sql
--
-- PURPOSE: Integrate Axie traits fetching into the data pipeline workflow
--
-- WORKFLOW DESIGN:
-- 1. Sales inserted → automatically queued for metadata fetch
-- 2. Metadata fetcher processes queue (with retry logic)
-- 3. On successful fetch → backfill denormalized columns in axie_sales
-- 4. Track fetch state, failures, and history

SET search_path TO axie, public;

-- ============================================
-- 1. METADATA FETCH QUEUE
-- Tracks which Axies need metadata fetched
-- ============================================
CREATE TABLE IF NOT EXISTS metadata_fetch_queue (
    axie_id         INTEGER PRIMARY KEY,

    -- Status tracking
    status          VARCHAR(20) DEFAULT 'pending',
                    -- pending: needs fetch
                    -- in_progress: currently being fetched
                    -- completed: successfully fetched
                    -- failed: fetch failed (will retry)
                    -- not_found: Axie doesn't exist (won't retry)

    priority        SMALLINT DEFAULT 0,             -- Higher = fetch first (e.g., recent sales)

    -- Retry logic
    retry_count     SMALLINT DEFAULT 0,
    max_retries     SMALLINT DEFAULT 3,
    next_retry_at   TIMESTAMP,

    -- Timing
    created_at      TIMESTAMP DEFAULT NOW(),
    first_seen_in   VARCHAR(50),                    -- Where we first saw this axie_id (sale, listing, etc)
    last_attempt_at TIMESTAMP,
    completed_at    TIMESTAMP,

    -- Error tracking
    last_error      TEXT
);

CREATE INDEX IF NOT EXISTS idx_fetch_queue_status ON metadata_fetch_queue(status);
CREATE INDEX IF NOT EXISTS idx_fetch_queue_pending ON metadata_fetch_queue(priority DESC, created_at ASC)
    WHERE status = 'pending';
CREATE INDEX IF NOT EXISTS idx_fetch_queue_retry ON metadata_fetch_queue(next_retry_at)
    WHERE status = 'failed' AND retry_count < max_retries;

-- ============================================
-- 2. AXIE PARTS MAPPING (Normalized)
-- Enables efficient queries by specific parts
-- ============================================
CREATE TABLE IF NOT EXISTS axie_parts_mapping (
    axie_id         INTEGER NOT NULL,
    part_id         VARCHAR(50) NOT NULL,
    part_type       VARCHAR(20) NOT NULL,           -- Eyes, Ears, Mouth, Horn, Back, Tail
    part_class      VARCHAR(20),                    -- Beast, Plant, etc.
    is_class_pure   BOOLEAN,                        -- Does this part match Axie's class?

    PRIMARY KEY (axie_id, part_id)
);

CREATE INDEX IF NOT EXISTS idx_parts_map_part ON axie_parts_mapping(part_id);
CREATE INDEX IF NOT EXISTS idx_parts_map_type ON axie_parts_mapping(part_type, part_id);
CREATE INDEX IF NOT EXISTS idx_parts_map_class ON axie_parts_mapping(part_class);

-- ============================================
-- 3. METADATA CHANGE HISTORY
-- Track changes to mutable fields (name, owner, breed_count)
-- ============================================
CREATE TABLE IF NOT EXISTS axie_metadata_history (
    id              BIGSERIAL PRIMARY KEY,
    axie_id         INTEGER NOT NULL,
    field_name      VARCHAR(50) NOT NULL,
    old_value       TEXT,
    new_value       TEXT,
    changed_at      TIMESTAMP DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_meta_history_axie ON axie_metadata_history(axie_id, changed_at DESC);

-- ============================================
-- 4. SYNC STATE EXPANSION
-- Add metadata sync tracking
-- ============================================
INSERT INTO sync_state (id, last_block, last_timestamp, records_synced)
VALUES
    ('axie_metadata', 0, '2024-01-01'::timestamp, 0),
    ('metadata_queue', 0, '2024-01-01'::timestamp, 0)
ON CONFLICT (id) DO NOTHING;

-- ============================================
-- 5. FUNCTIONS: Queue Management
-- ============================================

-- Function: Add axie to fetch queue (idempotent)
CREATE OR REPLACE FUNCTION queue_metadata_fetch(
    p_axie_id INTEGER,
    p_source VARCHAR(50) DEFAULT 'unknown',
    p_priority SMALLINT DEFAULT 0
) RETURNS VOID AS $$
BEGIN
    INSERT INTO metadata_fetch_queue (axie_id, first_seen_in, priority)
    VALUES (p_axie_id, p_source, p_priority)
    ON CONFLICT (axie_id) DO UPDATE SET
        priority = GREATEST(metadata_fetch_queue.priority, EXCLUDED.priority);
END;
$$ LANGUAGE plpgsql;

-- Function: Get next batch to fetch
CREATE OR REPLACE FUNCTION get_fetch_batch(p_batch_size INTEGER DEFAULT 50)
RETURNS TABLE (axie_id INTEGER) AS $$
BEGIN
    RETURN QUERY
    WITH batch AS (
        SELECT q.axie_id
        FROM metadata_fetch_queue q
        LEFT JOIN axie_metadata m ON q.axie_id = m.axie_id
        WHERE q.status = 'pending'
          AND m.axie_id IS NULL  -- Not already fetched
        ORDER BY q.priority DESC, q.created_at ASC
        LIMIT p_batch_size
        FOR UPDATE SKIP LOCKED
    )
    UPDATE metadata_fetch_queue q
    SET status = 'in_progress', last_attempt_at = NOW()
    FROM batch b
    WHERE q.axie_id = b.axie_id
    RETURNING q.axie_id;
END;
$$ LANGUAGE plpgsql;

-- Function: Get retry batch (failed items ready for retry)
CREATE OR REPLACE FUNCTION get_retry_batch(p_batch_size INTEGER DEFAULT 20)
RETURNS TABLE (axie_id INTEGER) AS $$
BEGIN
    RETURN QUERY
    WITH batch AS (
        SELECT q.axie_id
        FROM metadata_fetch_queue q
        WHERE q.status = 'failed'
          AND q.retry_count < q.max_retries
          AND (q.next_retry_at IS NULL OR q.next_retry_at <= NOW())
        ORDER BY q.next_retry_at ASC NULLS FIRST
        LIMIT p_batch_size
        FOR UPDATE SKIP LOCKED
    )
    UPDATE metadata_fetch_queue q
    SET status = 'in_progress',
        last_attempt_at = NOW(),
        retry_count = retry_count + 1
    FROM batch b
    WHERE q.axie_id = b.axie_id
    RETURNING q.axie_id;
END;
$$ LANGUAGE plpgsql;

-- Function: Mark fetch as completed
CREATE OR REPLACE FUNCTION mark_fetch_completed(p_axie_id INTEGER)
RETURNS VOID AS $$
BEGIN
    UPDATE metadata_fetch_queue
    SET status = 'completed', completed_at = NOW()
    WHERE axie_id = p_axie_id;
END;
$$ LANGUAGE plpgsql;

-- Function: Mark fetch as failed
CREATE OR REPLACE FUNCTION mark_fetch_failed(
    p_axie_id INTEGER,
    p_error TEXT DEFAULT NULL,
    p_not_found BOOLEAN DEFAULT FALSE
) RETURNS VOID AS $$
DECLARE
    v_retry_delay INTERVAL;
BEGIN
    IF p_not_found THEN
        UPDATE metadata_fetch_queue
        SET status = 'not_found', last_error = p_error
        WHERE axie_id = p_axie_id;
    ELSE
        -- Exponential backoff: 1min, 5min, 30min
        SELECT CASE retry_count
            WHEN 0 THEN INTERVAL '1 minute'
            WHEN 1 THEN INTERVAL '5 minutes'
            ELSE INTERVAL '30 minutes'
        END INTO v_retry_delay
        FROM metadata_fetch_queue WHERE axie_id = p_axie_id;

        UPDATE metadata_fetch_queue
        SET status = 'failed',
            last_error = p_error,
            next_retry_at = NOW() + COALESCE(v_retry_delay, INTERVAL '1 minute')
        WHERE axie_id = p_axie_id;
    END IF;
END;
$$ LANGUAGE plpgsql;

-- ============================================
-- 6. FUNCTIONS: Backfill Sales Data
-- ============================================

-- Function: Backfill denormalized columns in axie_sales after metadata fetch
CREATE OR REPLACE FUNCTION backfill_sale_metadata(p_axie_id INTEGER)
RETURNS INTEGER AS $$
DECLARE
    v_updated INTEGER;
BEGIN
    UPDATE axie_sales s
    SET class = m.class,
        breed_count = m.breed_count
    FROM axie_metadata m
    WHERE s.axie_id = p_axie_id
      AND m.axie_id = p_axie_id
      AND (s.class IS NULL OR s.breed_count IS NULL);

    GET DIAGNOSTICS v_updated = ROW_COUNT;
    RETURN v_updated;
END;
$$ LANGUAGE plpgsql;

-- Function: Backfill all sales missing metadata
CREATE OR REPLACE FUNCTION backfill_all_sales_metadata()
RETURNS INTEGER AS $$
DECLARE
    v_updated INTEGER;
BEGIN
    UPDATE axie_sales s
    SET class = m.class,
        breed_count = m.breed_count
    FROM axie_metadata m
    WHERE s.axie_id = m.axie_id
      AND (s.class IS NULL OR s.breed_count IS NULL);

    GET DIAGNOSTICS v_updated = ROW_COUNT;
    RETURN v_updated;
END;
$$ LANGUAGE plpgsql;

-- ============================================
-- 7. FUNCTIONS: Populate Parts Mapping
-- ============================================

-- Function: Populate parts mapping from metadata
CREATE OR REPLACE FUNCTION populate_parts_mapping(p_axie_id INTEGER)
RETURNS VOID AS $$
DECLARE
    v_class VARCHAR(20);
    v_part RECORD;
BEGIN
    SELECT class INTO v_class FROM axie_metadata WHERE axie_id = p_axie_id;

    -- Delete existing mappings for this axie
    DELETE FROM axie_parts_mapping WHERE axie_id = p_axie_id;

    -- Insert from JSONB parts
    FOR v_part IN
        SELECT
            p->>'id' as part_id,
            p->>'type' as part_type,
            p->>'class' as part_class
        FROM axie_metadata m,
             jsonb_array_elements(m.parts_json) p
        WHERE m.axie_id = p_axie_id
    LOOP
        INSERT INTO axie_parts_mapping (axie_id, part_id, part_type, part_class, is_class_pure)
        VALUES (p_axie_id, v_part.part_id, v_part.part_type, v_part.part_class, v_part.part_class = v_class)
        ON CONFLICT (axie_id, part_id) DO NOTHING;
    END LOOP;
END;
$$ LANGUAGE plpgsql;

-- ============================================
-- 8. TRIGGERS: Auto-queue on new sale
-- ============================================

-- Trigger function: Queue metadata fetch when new sale inserted
CREATE OR REPLACE FUNCTION trigger_queue_sale_metadata()
RETURNS TRIGGER AS $$
BEGIN
    -- Queue with priority based on recency (newer = higher priority)
    PERFORM queue_metadata_fetch(
        NEW.axie_id,
        'axie_sale',
        CASE
            WHEN NEW.block_timestamp > NOW() - INTERVAL '1 hour' THEN 10
            WHEN NEW.block_timestamp > NOW() - INTERVAL '1 day' THEN 5
            ELSE 1
        END::SMALLINT
    );
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Create trigger on axie_sales
DROP TRIGGER IF EXISTS trg_queue_sale_metadata ON axie_sales;
CREATE TRIGGER trg_queue_sale_metadata
    AFTER INSERT ON axie_sales
    FOR EACH ROW
    EXECUTE FUNCTION trigger_queue_sale_metadata();

-- ============================================
-- 9. VIEWS: Queue Status
-- ============================================

CREATE OR REPLACE VIEW v_fetch_queue_status AS
SELECT
    status,
    COUNT(*) as count,
    MIN(created_at) as oldest,
    MAX(created_at) as newest
FROM metadata_fetch_queue
GROUP BY status
ORDER BY
    CASE status
        WHEN 'pending' THEN 1
        WHEN 'in_progress' THEN 2
        WHEN 'failed' THEN 3
        WHEN 'completed' THEN 4
        WHEN 'not_found' THEN 5
    END;

CREATE OR REPLACE VIEW v_fetch_queue_pending AS
SELECT
    axie_id,
    priority,
    first_seen_in,
    created_at,
    retry_count
FROM metadata_fetch_queue
WHERE status IN ('pending', 'failed')
  AND (status = 'pending' OR (retry_count < max_retries AND (next_retry_at IS NULL OR next_retry_at <= NOW())))
ORDER BY priority DESC, created_at ASC
LIMIT 100;

-- ============================================
-- 10. STORED PROCEDURE: Complete Metadata Workflow
-- Called after successful metadata insert
-- ============================================

CREATE OR REPLACE PROCEDURE process_metadata_complete(p_axie_id INTEGER)
LANGUAGE plpgsql AS $$
BEGIN
    -- 1. Mark queue as completed
    PERFORM mark_fetch_completed(p_axie_id);

    -- 2. Backfill sale denormalized columns
    PERFORM backfill_sale_metadata(p_axie_id);

    -- 3. Populate parts mapping
    PERFORM populate_parts_mapping(p_axie_id);

    -- 4. Update sync state
    UPDATE sync_state
    SET records_synced = records_synced + 1, updated_at = NOW()
    WHERE id = 'axie_metadata';
END;
$$;

-- ============================================
-- 11. MIGRATION: Queue existing sales without metadata
-- ============================================

-- Queue all existing sales that don't have metadata
INSERT INTO metadata_fetch_queue (axie_id, first_seen_in, priority, status)
SELECT DISTINCT
    s.axie_id,
    'migration',
    1,
    CASE WHEN m.axie_id IS NOT NULL THEN 'completed' ELSE 'pending' END
FROM axie_sales s
LEFT JOIN axie_metadata m ON s.axie_id = m.axie_id
ON CONFLICT (axie_id) DO NOTHING;

-- Populate parts mapping for existing metadata
DO $$
DECLARE
    v_axie_id INTEGER;
BEGIN
    FOR v_axie_id IN SELECT axie_id FROM axie_metadata LOOP
        PERFORM populate_parts_mapping(v_axie_id);
    END LOOP;
END;
$$;

-- Backfill existing sales
SELECT backfill_all_sales_metadata() as sales_backfilled;

-- ============================================
-- COMMENTS
-- ============================================

COMMENT ON TABLE metadata_fetch_queue IS 'Queue for tracking Axie metadata fetch status with retry logic';
COMMENT ON TABLE axie_parts_mapping IS 'Normalized parts mapping for efficient part-based queries';
COMMENT ON TABLE axie_metadata_history IS 'Track changes to mutable Axie fields over time';

COMMENT ON FUNCTION queue_metadata_fetch IS 'Add an Axie to the metadata fetch queue (idempotent)';
COMMENT ON FUNCTION get_fetch_batch IS 'Get next batch of Axies to fetch metadata for';
COMMENT ON FUNCTION backfill_sale_metadata IS 'Backfill denormalized columns in axie_sales from metadata';
COMMENT ON PROCEDURE process_metadata_complete IS 'Complete workflow after successful metadata fetch';

SELECT 'Metadata workflow schema created successfully' as status;
