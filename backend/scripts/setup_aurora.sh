#!/bin/bash
# =====================================================
# Aurora Database Setup Script
# =====================================================
set -e

CLUSTER_ID="op-price-data"
INSTANCE_ID="op-price-data-instance-1"
REGION="us-east-1"

echo "=== Axie Explorer Aurora Setup ==="
echo ""

# Check if psql is installed
if ! command -v psql &> /dev/null; then
    echo "Error: psql not found. Install PostgreSQL client:"
    echo "  brew install postgresql@16"
    exit 1
fi

# Option 1: Make instance temporarily publicly accessible
echo "Option 1: Enable public access temporarily (recommended for initial setup)"
echo "--------------------------------------------------------------------------"
echo ""
echo "Run these commands to enable public access:"
echo ""
echo "# 1. Modify instance to be publicly accessible"
echo "aws rds modify-db-instance \\"
echo "    --db-instance-identifier $INSTANCE_ID \\"
echo "    --publicly-accessible \\"
echo "    --apply-immediately"
echo ""
echo "# 2. Wait for modification (takes ~5 min)"
echo "aws rds wait db-instance-available --db-instance-identifier $INSTANCE_ID"
echo ""
echo "# 3. Add your IP to security group"
echo "MY_IP=\$(curl -s ifconfig.me)"
echo "aws ec2 authorize-security-group-ingress \\"
echo "    --group-id sg-0950dcd2b1d814059 \\"
echo "    --protocol tcp \\"
echo "    --port 5432 \\"
echo "    --cidr \$MY_IP/32"
echo ""
echo "# 4. Connect and run setup"
echo "psql -h op-price-data.cluster-cn4c2su0o42n.us-east-1.rds.amazonaws.com -U yucheung -d postgres -f scripts/setup_database.sql"
echo ""

# Option 2: Use AWS CloudShell
echo "Option 2: Use AWS CloudShell (no public access needed)"
echo "------------------------------------------------------"
echo ""
echo "1. Go to AWS Console > CloudShell"
echo "2. Install psql: sudo yum install postgresql15 -y"
echo "3. Connect: psql -h op-price-data.cluster-cn4c2su0o42n.us-east-1.rds.amazonaws.com -U yucheung -d postgres"
echo "4. Run the SQL commands from setup_database.sql"
echo ""

# Check current public accessibility
echo "Current instance status:"
aws rds describe-db-instances \
    --db-instance-identifier $INSTANCE_ID \
    --query "DBInstances[0].{Status:DBInstanceStatus,PubliclyAccessible:PubliclyAccessible}" \
    --output table
