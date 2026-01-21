#!/bin/bash
# AxiePro Infrastructure Destroy Script
# Usage: ./scripts/destroy.sh [environment]
# WARNING: This will destroy all resources!

set -e

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

ENVIRONMENT=${1:-development}

# Validate environment
if [[ ! "$ENVIRONMENT" =~ ^(development|staging|production)$ ]]; then
    echo -e "${RED}Error: Invalid environment '$ENVIRONMENT'${NC}"
    exit 1
fi

# Extra confirmation for production
if [ "$ENVIRONMENT" == "production" ]; then
    echo -e "${RED}============================================${NC}"
    echo -e "${RED}   ⚠️  PRODUCTION ENVIRONMENT DESTRUCTION${NC}"
    echo -e "${RED}============================================${NC}"
    echo ""
    echo -e "${RED}This will PERMANENTLY DELETE all production resources!${NC}"
    echo ""
    read -p "Type 'DESTROY PRODUCTION' to confirm: " CONFIRM
    if [ "$CONFIRM" != "DESTROY PRODUCTION" ]; then
        echo "Destruction cancelled."
        exit 0
    fi
fi

cd "$(dirname "$0")/.."

echo -e "${YELLOW}Destroying AxiePro infrastructure for $ENVIRONMENT...${NC}"
echo ""

# Destroy in reverse order of dependencies
npx cdk destroy --all -c environment=$ENVIRONMENT --force

echo ""
echo -e "${GREEN}Infrastructure destroyed successfully.${NC}"
