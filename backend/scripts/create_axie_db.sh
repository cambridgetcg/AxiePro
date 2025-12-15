#!/bin/bash
# =====================================================
# Create Axie Explorer Database
# =====================================================
set -e

AURORA_HOST="op-price-data.cluster-cn4c2su0o42n.us-east-1.rds.amazonaws.com"
AURORA_USER="yucheung"
DB_NAME="cardforum"
APP_USER="axie_admin"

# Prompt for passwords
echo "=== Axie Explorer Database Setup ==="
echo ""
read -sp "Enter Aurora master password for '$AURORA_USER': " MASTER_PW
echo ""
read -sp "Enter new password for '$APP_USER' (app user): " APP_PW
echo ""
echo ""

export PGPASSWORD="$MASTER_PW"

echo "1. Testing connection..."
psql -h "$AURORA_HOST" -U "$AURORA_USER" -d postgres -c "SELECT version();" || {
    echo "Error: Cannot connect to Aurora. Check password and network."
    exit 1
}

echo ""
echo "2. Creating database '$DB_NAME'..."
psql -h "$AURORA_HOST" -U "$AURORA_USER" -d postgres -c "CREATE DATABASE $DB_NAME;" 2>/dev/null || echo "   Database may already exist, continuing..."

echo ""
echo "3. Creating application user '$APP_USER'..."
psql -h "$AURORA_HOST" -U "$AURORA_USER" -d postgres <<EOF
DO \$\$
BEGIN
    IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname = '$APP_USER') THEN
        CREATE USER $APP_USER WITH PASSWORD '$APP_PW';
    ELSE
        ALTER USER $APP_USER WITH PASSWORD '$APP_PW';
    END IF;
END
\$\$;
EOF

echo ""
echo "4. Granting privileges..."
psql -h "$AURORA_HOST" -U "$AURORA_USER" -d "$DB_NAME" <<EOF
GRANT ALL PRIVILEGES ON DATABASE $DB_NAME TO $APP_USER;
GRANT ALL ON SCHEMA public TO $APP_USER;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON TABLES TO $APP_USER;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON SEQUENCES TO $APP_USER;
EOF

echo ""
echo "5. Enabling extensions..."
psql -h "$AURORA_HOST" -U "$AURORA_USER" -d "$DB_NAME" <<EOF
CREATE EXTENSION IF NOT EXISTS pg_trgm;
CREATE EXTENSION IF NOT EXISTS pg_stat_statements;
EOF

echo ""
echo "=== Setup Complete ==="
echo ""
echo "Database URL for .env:"
echo "DATABASE_URL=postgresql://$APP_USER:YOUR_PASSWORD@$AURORA_HOST:5432/$DB_NAME"
echo ""
echo "Next: Run Alembic migrations"
echo "  cd /Users/alex/Ronin_API/backend"
echo "  source venv/bin/activate"
echo "  export DATABASE_URL='postgresql://$APP_USER:YOUR_PASSWORD@$AURORA_HOST:5432/$DB_NAME'"
echo "  alembic upgrade head"

unset PGPASSWORD
