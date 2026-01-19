-- AxiePro Database Schema - Views & Functions
-- Run after 02_create_analysis_tables.sql

SET search_path TO axie, public;

-- ============================================
-- MATERIALIZED VIEWS
-- ============================================

-- Floor Price History (for charts)
CREATE MATERIALIZED VIEW IF NOT EXISTS mv_floor_history AS
SELECT
    date_trunc('hour', snapshot_at) as hour,
    class,
    MIN(floor_price_usd) as floor_usd,
    AVG(total_listed)::INTEGER as avg_listed
FROM class_metrics
WHERE snapshot_at > NOW() - INTERVAL '90 days'
GROUP BY 1, 2
ORDER BY 1 DESC, 2;

CREATE UNIQUE INDEX IF NOT EXISTS idx_mv_floor_history ON mv_floor_history(hour, class);

-- Daily Volume Summary
CREATE MATERIALIZED VIEW IF NOT EXISTS mv_daily_volume AS
SELECT
    date_trunc('day', block_timestamp) as day,
    class,
    COUNT(*) as sales,
    SUM(price_usd) as volume_usd,
    AVG(price_usd)::NUMERIC(12,2) as avg_price,
    PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY price_usd)::NUMERIC(12,2) as median_price,
    MIN(price_usd) as min_price,
    MAX(price_usd) as max_price
FROM axie_sales
WHERE block_timestamp > NOW() - INTERVAL '90 days'
GROUP BY 1, 2
ORDER BY 1 DESC, 2;

CREATE UNIQUE INDEX IF NOT EXISTS idx_mv_daily_volume ON mv_daily_volume(day, class);

-- Undervalued Listings (Arbitrage)
CREATE MATERIALIZED VIEW IF NOT EXISTS mv_undervalued AS
SELECT
    l.axie_id,
    l.class,
    l.breed_count,
    l.price_usd as listing_price,
    l.last_sale_price,
    l.price_vs_last,
    l.price_vs_floor,
    m.parts_json,
    m.pure_part_count
FROM axie_listings l
LEFT JOIN axie_metadata m ON l.axie_id = m.axie_id
WHERE l.price_vs_last < 0.85
   OR (l.price_vs_floor < 1.05 AND COALESCE(m.pure_part_count, 0) >= 4)
ORDER BY l.price_vs_last ASC NULLS LAST
LIMIT 200;

CREATE UNIQUE INDEX IF NOT EXISTS idx_mv_undervalued ON mv_undervalued(axie_id);

-- Hot Parts (Trending Meta)
CREATE MATERIALIZED VIEW IF NOT EXISTS mv_hot_parts AS
SELECT
    p.part_id,
    p.part_name,
    p.part_type,
    p.part_class,
    pp.floor_price_usd,
    pp.volume_24h_usd,
    pp.volume_change_24h,
    pp.floor_change_24h,
    pp.axies_listed,
    pp.sales_24h
FROM parts_pricing pp
JOIN axie_parts p ON pp.part_id = p.part_id
WHERE pp.snapshot_at = (SELECT MAX(snapshot_at) FROM parts_pricing)
ORDER BY pp.volume_change_24h DESC NULLS LAST
LIMIT 100;

CREATE UNIQUE INDEX IF NOT EXISTS idx_mv_hot_parts ON mv_hot_parts(part_id);

-- Recent Large Sales
CREATE MATERIALIZED VIEW IF NOT EXISTS mv_large_sales AS
SELECT
    s.axie_id,
    s.class,
    s.breed_count,
    s.price_usd,
    s.price_token,
    s.token_type,
    s.buyer,
    s.seller,
    s.block_timestamp,
    s.tx_hash
FROM axie_sales s
WHERE s.block_timestamp > NOW() - INTERVAL '24 hours'
  AND s.price_usd > 50
ORDER BY s.price_usd DESC
LIMIT 100;

CREATE UNIQUE INDEX IF NOT EXISTS idx_mv_large_sales ON mv_large_sales(tx_hash, axie_id);

-- ============================================
-- HELPER FUNCTIONS
-- ============================================

-- Get floor price for a class
CREATE OR REPLACE FUNCTION get_floor_price(p_class VARCHAR)
RETURNS NUMERIC AS $$
    SELECT floor_price_usd
    FROM class_metrics
    WHERE class = p_class
    ORDER BY snapshot_at DESC
    LIMIT 1;
$$ LANGUAGE SQL STABLE;

-- Get recent sales for an axie
CREATE OR REPLACE FUNCTION get_axie_sales(p_axie_id INTEGER, p_limit INTEGER DEFAULT 10)
RETURNS TABLE (
    sale_date TIMESTAMP,
    price_usd NUMERIC,
    buyer VARCHAR,
    seller VARCHAR,
    tx_hash VARCHAR
) AS $$
    SELECT block_timestamp, price_usd, buyer, seller, tx_hash
    FROM axie_sales
    WHERE axie_id = p_axie_id
    ORDER BY block_timestamp DESC
    LIMIT p_limit;
$$ LANGUAGE SQL STABLE;

-- Estimate axie value based on class/breed/purity
CREATE OR REPLACE FUNCTION estimate_axie_value(p_axie_id INTEGER)
RETURNS NUMERIC AS $$
DECLARE
    v_class VARCHAR;
    v_breed_count SMALLINT;
    v_pure_count SMALLINT;
    v_base_price NUMERIC;
    v_breed_mult NUMERIC;
    v_pure_mult NUMERIC;
BEGIN
    SELECT class, breed_count, pure_part_count
    INTO v_class, v_breed_count, v_pure_count
    FROM axie_metadata WHERE axie_id = p_axie_id;

    IF v_class IS NULL THEN
        RETURN NULL;
    END IF;

    v_base_price := get_floor_price(v_class);
    IF v_base_price IS NULL THEN
        RETURN NULL;
    END IF;

    -- Breed count multiplier
    v_breed_mult := CASE v_breed_count
        WHEN 0 THEN 1.5
        WHEN 1 THEN 1.2
        WHEN 2 THEN 1.1
        WHEN 3 THEN 1.05
        ELSE 1.0
    END;

    -- Purity multiplier
    v_pure_mult := 1.0 + (COALESCE(v_pure_count, 0) * 0.08);

    RETURN ROUND(v_base_price * v_breed_mult * v_pure_mult, 2);
END;
$$ LANGUAGE plpgsql STABLE;

-- Get 24h volume for a class
CREATE OR REPLACE FUNCTION get_24h_volume(p_class VARCHAR DEFAULT NULL)
RETURNS TABLE (
    class VARCHAR,
    sales_count BIGINT,
    volume_usd NUMERIC,
    avg_price NUMERIC
) AS $$
    SELECT
        s.class,
        COUNT(*) as sales_count,
        SUM(s.price_usd) as volume_usd,
        ROUND(AVG(s.price_usd), 2) as avg_price
    FROM axie_sales s
    WHERE s.block_timestamp > NOW() - INTERVAL '24 hours'
      AND (p_class IS NULL OR s.class = p_class)
    GROUP BY s.class
    ORDER BY volume_usd DESC;
$$ LANGUAGE SQL STABLE;

-- Calculate virgin premium
CREATE OR REPLACE FUNCTION get_virgin_premium()
RETURNS TABLE (
    class VARCHAR,
    virgin_floor NUMERIC,
    breed1_floor NUMERIC,
    premium_pct NUMERIC
) AS $$
    SELECT
        c0.class,
        c0.floor_price_usd as virgin_floor,
        c1.floor_price_usd as breed1_floor,
        ROUND((c0.floor_price_usd / NULLIF(c1.floor_price_usd, 0) - 1) * 100, 1) as premium_pct
    FROM (
        SELECT class, floor_price_usd
        FROM breed_count_metrics
        WHERE breed_count = 0
          AND snapshot_at = (SELECT MAX(snapshot_at) FROM breed_count_metrics WHERE breed_count = 0)
    ) c0
    LEFT JOIN (
        SELECT class, floor_price_usd
        FROM breed_count_metrics
        WHERE breed_count = 1
          AND snapshot_at = (SELECT MAX(snapshot_at) FROM breed_count_metrics WHERE breed_count = 1)
    ) c1 ON c0.class = c1.class
    ORDER BY premium_pct DESC NULLS LAST;
$$ LANGUAGE SQL STABLE;

-- ============================================
-- REFRESH PROCEDURES
-- ============================================

-- Procedure to refresh all materialized views
CREATE OR REPLACE PROCEDURE refresh_all_views()
LANGUAGE plpgsql AS $$
BEGIN
    REFRESH MATERIALIZED VIEW CONCURRENTLY mv_floor_history;
    REFRESH MATERIALIZED VIEW CONCURRENTLY mv_daily_volume;
    REFRESH MATERIALIZED VIEW CONCURRENTLY mv_undervalued;
    REFRESH MATERIALIZED VIEW CONCURRENTLY mv_hot_parts;
    REFRESH MATERIALIZED VIEW CONCURRENTLY mv_large_sales;
END;
$$;

-- ============================================
-- USEFUL QUERIES (as views)
-- ============================================

-- Current market summary
CREATE OR REPLACE VIEW v_market_summary AS
SELECT
    ms.snapshot_at,
    ms.total_listed,
    ms.floor_price_usd,
    ms.total_sales as sales_1h,
    ms.total_volume_usd as volume_1h,
    ms.eth_usd,
    ms.ron_usd
FROM market_snapshots ms
ORDER BY ms.snapshot_at DESC
LIMIT 1;

-- Class comparison
CREATE OR REPLACE VIEW v_class_comparison AS
SELECT
    class,
    total_listed,
    floor_price_usd,
    sales_count as sales_1h,
    volume_usd as volume_1h,
    floor_change_pct
FROM class_metrics
WHERE snapshot_at = (SELECT MAX(snapshot_at) FROM class_metrics)
ORDER BY floor_price_usd ASC;

-- Breed count comparison
CREATE OR REPLACE VIEW v_breed_comparison AS
SELECT
    breed_count,
    total_listed,
    floor_price_usd,
    avg_price_usd,
    virgin_premium_pct
FROM breed_count_metrics
WHERE snapshot_at = (SELECT MAX(snapshot_at) FROM breed_count_metrics)
ORDER BY breed_count ASC;

SELECT 'Views and functions created successfully' as status;
