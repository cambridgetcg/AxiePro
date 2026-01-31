-- AxiePro Database Schema - Drop Sales FK Constraint
-- Run to unblock sales ingestion
--
-- PURPOSE: Remove the foreign key constraint that requires axie metadata
-- to exist before sales can be inserted. Sales can be inserted independently
-- and linked to metadata later.

SET search_path TO axie, public;

-- Drop the FK constraint on axie_sales table
ALTER TABLE axie_sales DROP CONSTRAINT IF EXISTS axie_sales_axie_id_fkey;

-- Add a comment explaining why
COMMENT ON TABLE axie_sales IS 'Axie sales data. FK to axies removed to allow independent ingestion. Metadata linked via axie_id when available.';

SELECT 'Sales FK constraint dropped successfully' as status;
