"""restore sales FK with deferrable constraint

Revision ID: 20260131_restore_fk
Revises: (check latest migration)
Create Date: 2026-01-31

Restores the foreign key constraint between axie_sales and axies tables
with DEFERRABLE INITIALLY DEFERRED to allow delayed metadata ingestion.

This allows:
1. Sales to be ingested immediately from blockchain
2. Metadata to be fetched separately (may arrive later)
3. FK constraint verified at transaction commit time

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '20260131_restore_fk'
down_revision = None  # Update this to the latest migration hash
branch_labels = None
depends_on = None


def upgrade() -> None:
    """
    Restore FK constraint with DEFERRABLE option.

    Uses DEFERRABLE INITIALLY DEFERRED to allow:
    - Sales ingestion before metadata exists
    - Validation at commit time (not insert time)
    - Graceful handling of temporal mismatches
    """
    # Check if FK already exists (idempotent)
    conn = op.get_bind()

    # Query to check if constraint exists
    check_fk = sa.text("""
        SELECT 1
        FROM information_schema.table_constraints
        WHERE constraint_name = 'axie_sales_axie_id_fkey'
          AND table_schema = 'axie'
          AND table_name = 'axie_sales'
    """)

    result = conn.execute(check_fk).fetchone()

    if result:
        print("FK constraint already exists, skipping creation")
        return

    # Create DEFERRABLE FK constraint
    op.execute("""
        ALTER TABLE axie.axie_sales
        ADD CONSTRAINT axie_sales_axie_id_fkey
        FOREIGN KEY (axie_id)
        REFERENCES axie.axies (axie_id)
        ON DELETE SET NULL
        DEFERRABLE INITIALLY DEFERRED
    """)

    print("✓ Created DEFERRABLE FK constraint: axie_sales → axies")

    # Add comment explaining the constraint
    op.execute("""
        COMMENT ON CONSTRAINT axie_sales_axie_id_fkey ON axie.axie_sales IS
        'Foreign key to axies table with DEFERRABLE constraint to allow delayed metadata ingestion.
        Sales can be inserted before metadata exists within same transaction.'
    """)


def downgrade() -> None:
    """
    Remove FK constraint.

    Note: This is the same as the original 08_drop_sales_fk.sql script.
    """
    # Check if FK exists before dropping (idempotent)
    conn = op.get_bind()

    check_fk = sa.text("""
        SELECT 1
        FROM information_schema.table_constraints
        WHERE constraint_name = 'axie_sales_axie_id_fkey'
          AND table_schema = 'axie'
          AND table_name = 'axie_sales'
    """)

    result = conn.execute(check_fk).fetchone()

    if not result:
        print("FK constraint does not exist, skipping drop")
        return

    # Drop FK constraint
    op.execute("""
        ALTER TABLE axie.axie_sales
        DROP CONSTRAINT IF EXISTS axie_sales_axie_id_fkey
    """)

    print("✓ Dropped FK constraint: axie_sales → axies")
