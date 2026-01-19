-- AxiePro Database Schema - Valuation Tables
-- Run after 05_sync_state_enhancement.sql
-- Supports hedonic pricing, ML valuation, and deal detection

SET search_path TO axie, public;

-- ============================================
-- 1. TRAIT STATISTICS (Pre-computed price stats)
-- ============================================
CREATE TABLE IF NOT EXISTS trait_statistics (
    id              BIGSERIAL PRIMARY KEY,
    trait_key       VARCHAR(100) NOT NULL,      -- e.g., "class:beast", "part:eyes-kotaro"
    trait_type      VARCHAR(20) NOT NULL,       -- "class", "part", "breed_count", "purity"
    class           VARCHAR(20),                -- Filter by class if applicable

    -- Price statistics
    avg_price_eth   DECIMAL(18, 8),
    median_price_eth DECIMAL(18, 8),
    std_dev_eth     DECIMAL(18, 8),
    min_price_eth   DECIMAL(18, 8),
    max_price_eth   DECIMAL(18, 8),

    -- Sample info
    sample_count    INTEGER NOT NULL DEFAULT 0,
    time_window_hours INTEGER NOT NULL DEFAULT 168,  -- Default 7 days

    -- Timestamps
    computed_at     TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    UNIQUE(trait_key, class, time_window_hours)
);

CREATE INDEX IF NOT EXISTS idx_trait_stats_key ON trait_statistics(trait_key);
CREATE INDEX IF NOT EXISTS idx_trait_stats_class ON trait_statistics(class);
CREATE INDEX IF NOT EXISTS idx_trait_stats_type ON trait_statistics(trait_type);
CREATE INDEX IF NOT EXISTS idx_trait_stats_computed ON trait_statistics(computed_at DESC);

-- ============================================
-- 2. HEDONIC COEFFICIENTS (Trained model params)
-- ============================================
CREATE TABLE IF NOT EXISTS hedonic_coefficients (
    id              BIGSERIAL PRIMARY KEY,
    model_version   VARCHAR(50) NOT NULL,

    -- Feature coefficients stored as JSONB
    -- Keys: "intercept", "class:beast", "part:eyes-kotaro", "breed_count", etc.
    coefficients    JSONB NOT NULL,

    -- Model metadata
    r_squared       DECIMAL(8, 6),
    adj_r_squared   DECIMAL(8, 6),
    rmse            DECIMAL(18, 8),
    sample_size     INTEGER,
    feature_count   INTEGER,

    -- Training window
    train_start     TIMESTAMPTZ,
    train_end       TIMESTAMPTZ,

    -- Status
    is_active       BOOLEAN DEFAULT FALSE,
    trained_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    UNIQUE(model_version)
);

CREATE INDEX IF NOT EXISTS idx_hedonic_active ON hedonic_coefficients(is_active) WHERE is_active = TRUE;
CREATE INDEX IF NOT EXISTS idx_hedonic_trained ON hedonic_coefficients(trained_at DESC);

-- ============================================
-- 3. AXIE VALUATIONS (Pre-computed FMV)
-- ============================================
CREATE TABLE IF NOT EXISTS axie_valuations (
    axie_id         BIGINT PRIMARY KEY,

    -- Hedonic model valuation
    hedonic_value_eth DECIMAL(18, 8),
    hedonic_version VARCHAR(50),

    -- ML model valuation
    ml_value_eth    DECIMAL(18, 8),
    ml_version      VARCHAR(50),

    -- Ensemble / final value
    ensemble_value_eth DECIMAL(18, 8),

    -- Confidence intervals (95%)
    confidence_lower_eth DECIMAL(18, 8),
    confidence_upper_eth DECIMAL(18, 8),
    confidence_score DECIMAL(5, 4),       -- 0-1 confidence in valuation

    -- Market context
    current_floor_eth DECIMAL(18, 8),
    class_avg_eth   DECIMAL(18, 8),

    -- Trend indicators
    trend_score     DECIMAL(5, 2),        -- -100 to +100
    momentum_7d     DECIMAL(8, 4),        -- 7-day price momentum %

    -- Timestamps
    computed_at     TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    expires_at      TIMESTAMPTZ NOT NULL DEFAULT NOW() + INTERVAL '15 minutes'
);

CREATE INDEX IF NOT EXISTS idx_valuations_value ON axie_valuations(ensemble_value_eth);
CREATE INDEX IF NOT EXISTS idx_valuations_confidence ON axie_valuations(confidence_score DESC);
CREATE INDEX IF NOT EXISTS idx_valuations_expires ON axie_valuations(expires_at);
CREATE INDEX IF NOT EXISTS idx_valuations_computed ON axie_valuations(computed_at DESC);

-- ============================================
-- 4. DETECTED DEALS (Arbitrage opportunities)
-- ============================================
CREATE TABLE IF NOT EXISTS detected_deals (
    id              BIGSERIAL PRIMARY KEY,
    axie_id         BIGINT NOT NULL,

    -- Listing info at detection
    listing_price_eth DECIMAL(18, 8) NOT NULL,
    listing_price_usd DECIMAL(12, 2),
    seller          VARCHAR(66),

    -- Valuation comparison
    fair_value_eth  DECIMAL(18, 8) NOT NULL,
    discount_eth    DECIMAL(18, 8),
    discount_percent DECIMAL(8, 4) NOT NULL,

    -- Z-score based detection
    z_score         DECIMAL(8, 4),
    std_dev_eth     DECIMAL(18, 8),

    -- Deal scoring
    deal_score      SMALLINT NOT NULL,    -- 0-100
    deal_type       VARCHAR(20) NOT NULL, -- "deal", "snipe", "whale_dump"

    -- Axie attributes at detection
    class           VARCHAR(20),
    breed_count     SMALLINT,
    purity_score    SMALLINT,
    parts_json      JSONB,

    -- Part-level analysis
    part_analysis   JSONB,

    -- Status tracking
    status          VARCHAR(20) DEFAULT 'active', -- "active", "sold", "delisted", "expired"
    detected_at     TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    sold_at         TIMESTAMPTZ,
    notification_sent BOOLEAN DEFAULT FALSE,

    -- Execution tracking
    purchased_by    VARCHAR(66),
    profit_eth      DECIMAL(18, 8),
    profit_usd      DECIMAL(12, 2)
);

CREATE INDEX IF NOT EXISTS idx_deals_axie ON detected_deals(axie_id);
CREATE INDEX IF NOT EXISTS idx_deals_score ON detected_deals(deal_score DESC);
CREATE INDEX IF NOT EXISTS idx_deals_status ON detected_deals(status, detected_at DESC);
CREATE INDEX IF NOT EXISTS idx_deals_type ON detected_deals(deal_type, detected_at DESC);
CREATE INDEX IF NOT EXISTS idx_deals_detected ON detected_deals(detected_at DESC);
CREATE INDEX IF NOT EXISTS idx_deals_class ON detected_deals(class, deal_score DESC);
CREATE UNIQUE INDEX IF NOT EXISTS idx_deals_unique ON detected_deals(axie_id, detected_at);

-- ============================================
-- 5. PRICE SNAPSHOTS (Trait-level time series)
-- ============================================
CREATE TABLE IF NOT EXISTS price_snapshots (
    id              BIGSERIAL,
    time            TIMESTAMPTZ NOT NULL,

    trait_key       VARCHAR(100) NOT NULL,
    class           VARCHAR(20),

    -- Price metrics
    floor_eth       DECIMAL(18, 8),
    avg_eth         DECIMAL(18, 8),
    median_eth      DECIMAL(18, 8),

    -- Volume metrics
    listings_count  INTEGER,
    sales_count     INTEGER,
    volume_eth      DECIMAL(18, 8),

    PRIMARY KEY (id, time)
) PARTITION BY RANGE (time);

-- Create partitions for 2024-2025
CREATE TABLE IF NOT EXISTS price_snapshots_2024_h1 PARTITION OF price_snapshots
    FOR VALUES FROM ('2024-01-01') TO ('2024-07-01');
CREATE TABLE IF NOT EXISTS price_snapshots_2024_h2 PARTITION OF price_snapshots
    FOR VALUES FROM ('2024-07-01') TO ('2025-01-01');
CREATE TABLE IF NOT EXISTS price_snapshots_2025_h1 PARTITION OF price_snapshots
    FOR VALUES FROM ('2025-01-01') TO ('2025-07-01');
CREATE TABLE IF NOT EXISTS price_snapshots_2025_h2 PARTITION OF price_snapshots
    FOR VALUES FROM ('2025-07-01') TO ('2026-01-01');

CREATE INDEX IF NOT EXISTS idx_snapshots_trait_time ON price_snapshots(trait_key, time DESC);
CREATE INDEX IF NOT EXISTS idx_snapshots_class_time ON price_snapshots(class, time DESC);

-- ============================================
-- 6. MODEL PREDICTIONS LOG (Audit trail)
-- ============================================
CREATE TABLE IF NOT EXISTS prediction_log (
    id              BIGSERIAL PRIMARY KEY,
    axie_id         BIGINT NOT NULL,

    -- Prediction details
    model_type      VARCHAR(20) NOT NULL,     -- "hedonic", "xgboost", "lightgbm", "ensemble"
    model_version   VARCHAR(50),
    predicted_value_eth DECIMAL(18, 8) NOT NULL,
    confidence_score DECIMAL(5, 4),

    -- Features used (for debugging)
    features_json   JSONB,

    -- Actual outcome (if sold)
    actual_price_eth DECIMAL(18, 8),
    prediction_error DECIMAL(8, 4),           -- Percentage error

    predicted_at    TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    outcome_recorded_at TIMESTAMPTZ
);

CREATE INDEX IF NOT EXISTS idx_pred_log_axie ON prediction_log(axie_id, predicted_at DESC);
CREATE INDEX IF NOT EXISTS idx_pred_log_model ON prediction_log(model_type, predicted_at DESC);
CREATE INDEX IF NOT EXISTS idx_pred_log_time ON prediction_log(predicted_at DESC);

-- ============================================
-- 7. ALERT SUBSCRIPTIONS (User preferences)
-- ============================================
CREATE TABLE IF NOT EXISTS alert_subscriptions (
    id              BIGSERIAL PRIMARY KEY,
    user_id         VARCHAR(100) NOT NULL,

    -- Filter criteria
    classes         VARCHAR(20)[],            -- Array of classes to watch
    min_deal_score  SMALLINT DEFAULT 50,
    max_price_eth   DECIMAL(18, 8),
    min_discount_pct DECIMAL(8, 4),

    -- Notification channels
    websocket_enabled BOOLEAN DEFAULT TRUE,
    sns_enabled     BOOLEAN DEFAULT FALSE,
    sns_topic_arn   TEXT,

    -- Rate limiting
    max_alerts_per_hour INTEGER DEFAULT 10,
    last_alert_at   TIMESTAMPTZ,
    alerts_this_hour INTEGER DEFAULT 0,

    -- Status
    is_active       BOOLEAN DEFAULT TRUE,
    created_at      TIMESTAMPTZ DEFAULT NOW(),
    updated_at      TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_alert_subs_user ON alert_subscriptions(user_id);
CREATE INDEX IF NOT EXISTS idx_alert_subs_active ON alert_subscriptions(is_active) WHERE is_active = TRUE;

-- ============================================
-- HELPER FUNCTIONS
-- ============================================

-- Function to get active hedonic coefficients
CREATE OR REPLACE FUNCTION get_active_hedonic_coefficients()
RETURNS JSONB AS $$
DECLARE
    result JSONB;
BEGIN
    SELECT coefficients INTO result
    FROM axie.hedonic_coefficients
    WHERE is_active = TRUE
    ORDER BY trained_at DESC
    LIMIT 1;

    RETURN result;
END;
$$ LANGUAGE plpgsql STABLE;

-- Function to get trait statistics for valuation
CREATE OR REPLACE FUNCTION get_trait_stats(p_trait_key VARCHAR, p_class VARCHAR DEFAULT NULL)
RETURNS TABLE (
    avg_price DECIMAL,
    median_price DECIMAL,
    std_dev DECIMAL,
    sample_count INTEGER
) AS $$
BEGIN
    RETURN QUERY
    SELECT
        ts.avg_price_eth,
        ts.median_price_eth,
        ts.std_dev_eth,
        ts.sample_count
    FROM axie.trait_statistics ts
    WHERE ts.trait_key = p_trait_key
      AND (p_class IS NULL OR ts.class = p_class)
      AND ts.computed_at > NOW() - INTERVAL '24 hours'
    ORDER BY ts.computed_at DESC
    LIMIT 1;
END;
$$ LANGUAGE plpgsql STABLE;

-- Function to expire old valuations
CREATE OR REPLACE FUNCTION expire_old_valuations()
RETURNS INTEGER AS $$
DECLARE
    deleted_count INTEGER;
BEGIN
    DELETE FROM axie.axie_valuations
    WHERE expires_at < NOW();

    GET DIAGNOSTICS deleted_count = ROW_COUNT;
    RETURN deleted_count;
END;
$$ LANGUAGE plpgsql;

-- Function to update deal status when sold
CREATE OR REPLACE FUNCTION update_deal_on_sale()
RETURNS TRIGGER AS $$
BEGIN
    UPDATE axie.detected_deals
    SET
        status = 'sold',
        sold_at = NEW.block_timestamp,
        profit_eth = NEW.price_token - listing_price_eth,
        profit_usd = NEW.price_usd - (listing_price_eth * NEW.eth_usd_rate)
    WHERE axie_id = NEW.axie_id
      AND status = 'active'
      AND detected_at > NOW() - INTERVAL '24 hours';

    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Trigger to update deals when axie is sold
DROP TRIGGER IF EXISTS trg_update_deal_on_sale ON axie_sales;
CREATE TRIGGER trg_update_deal_on_sale
    AFTER INSERT ON axie_sales
    FOR EACH ROW
    EXECUTE FUNCTION update_deal_on_sale();

-- ============================================
-- COMMENTS
-- ============================================
COMMENT ON TABLE trait_statistics IS 'Pre-computed price statistics per trait for fast valuation';
COMMENT ON TABLE hedonic_coefficients IS 'Trained hedonic pricing model coefficients';
COMMENT ON TABLE axie_valuations IS 'Pre-computed fair market valuations with confidence intervals';
COMMENT ON TABLE detected_deals IS 'Detected arbitrage opportunities with tracking';
COMMENT ON TABLE price_snapshots IS 'Time series of trait prices for trend analysis';
COMMENT ON TABLE prediction_log IS 'Audit log of model predictions vs actual outcomes';
COMMENT ON TABLE alert_subscriptions IS 'User preferences for deal notifications';

SELECT 'Valuation tables created successfully' as status;
