-- =====================================================
-- Axie Explorer Database Setup Script
-- Run this against your Aurora PostgreSQL cluster
-- =====================================================

-- 1. Create the database
CREATE DATABASE cardforum
    WITH
    OWNER = yucheung
    ENCODING = 'UTF8'
    LC_COLLATE = 'en_US.UTF-8'
    LC_CTYPE = 'en_US.UTF-8'
    TEMPLATE = template0;

-- 2. Connect to the new database
\c cardforum

-- 3. Create a dedicated user for the application
CREATE USER axie_admin WITH PASSWORD 'CHANGE_THIS_PASSWORD';

-- Grant privileges
GRANT ALL PRIVILEGES ON DATABASE cardforum TO axie_admin;
GRANT ALL ON SCHEMA public TO axie_admin;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON TABLES TO axie_admin;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON SEQUENCES TO axie_admin;

-- 4. Enable useful extensions
CREATE EXTENSION IF NOT EXISTS pg_trgm;           -- For text search
CREATE EXTENSION IF NOT EXISTS pg_stat_statements; -- For query analysis

-- 5. Verify setup
\dt
\du

-- Done! Now run Alembic migrations:
-- DATABASE_URL="postgresql://axie_admin:PASSWORD@op-price-data.cluster-cn4c2su0o42n.us-east-1.rds.amazonaws.com:5432/cardforum" alembic upgrade head
