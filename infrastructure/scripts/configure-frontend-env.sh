#!/bin/bash
set -euo pipefail

# AxiePro Frontend Environment Configuration Script
# Generates .env.production from template using CDK outputs

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
FRONTEND_DIR="$SCRIPT_DIR/../../frontend"

# Colors
GREEN='\033[0;32m'
BLUE='\033[0;34m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m'

# Arguments
ENVIRONMENT="${1:-production}"
REGION="${2:-us-west-2}"

echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}Frontend Environment Configuration${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""
echo "Environment: $ENVIRONMENT"
echo "Region: $REGION"
echo ""

# Get CDK stack outputs
echo -e "${BLUE}Fetching CDK outputs...${NC}"

# Get App Runner URL from ComputeStack
APP_RUNNER_URL=$(aws cloudformation describe-stacks \
    --stack-name "axiepro-ComputeStack-$ENVIRONMENT" \
    --region "$REGION" \
    --query "Stacks[0].Outputs[?OutputKey=='FastAPIServiceUrl'].OutputValue" \
    --output text 2>/dev/null || echo "")

if [ -z "$APP_RUNNER_URL" ]; then
    echo -e "${RED}Error: Could not fetch App Runner URL from CDK stack.${NC}"
    echo "Make sure CDK stack is deployed:"
    echo "  cd infrastructure && npx cdk deploy ComputeStack -c environment=$ENVIRONMENT"
    exit 1
fi

echo -e "${GREEN}✓${NC} App Runner URL: $APP_RUNNER_URL"

# Template and output paths
TEMPLATE_FILE="$FRONTEND_DIR/.env.${ENVIRONMENT}.template"
OUTPUT_FILE="$FRONTEND_DIR/.env.${ENVIRONMENT}"

if [ ! -f "$TEMPLATE_FILE" ]; then
    echo -e "${RED}Error: Template file not found: $TEMPLATE_FILE${NC}"
    exit 1
fi

echo -e "${BLUE}Generating environment file...${NC}"

# Read template and replace placeholders
cp "$TEMPLATE_FILE" "$OUTPUT_FILE"

# Replace placeholders
sed -i.bak "s|{{APP_RUNNER_URL}}|$APP_RUNNER_URL|g" "$OUTPUT_FILE"
sed -i.bak "s|{{GOOGLE_ANALYTICS_ID}}|${GOOGLE_ANALYTICS_ID:-}|g" "$OUTPUT_FILE"
sed -i.bak "s|{{SENTRY_DSN}}|${SENTRY_DSN:-}|g" "$OUTPUT_FILE"
sed -i.bak "s|{{BUILD_ID}}|$(git rev-parse --short HEAD 2>/dev/null || echo 'unknown')|g" "$OUTPUT_FILE"
sed -i.bak "s|{{DEPLOY_TIME}}|$(date -u +%Y-%m-%dT%H:%M:%SZ)|g" "$OUTPUT_FILE"

# Remove backup file
rm -f "${OUTPUT_FILE}.bak"

echo -e "${GREEN}✓${NC} Environment file created: $OUTPUT_FILE"
echo ""

# Display generated file
echo -e "${BLUE}Generated configuration:${NC}"
echo "---"
cat "$OUTPUT_FILE"
echo "---"
echo ""

# Verify required variables
echo -e "${BLUE}Verifying configuration...${NC}"

if grep -q "{{" "$OUTPUT_FILE"; then
    echo -e "${YELLOW}Warning: Some placeholders were not replaced:${NC}"
    grep "{{" "$OUTPUT_FILE" || true
    echo ""
fi

# Check if NEXT_PUBLIC_API_URL is set
if grep -q "NEXT_PUBLIC_API_URL=http" "$OUTPUT_FILE"; then
    echo -e "${GREEN}✓${NC} API URL configured"
else
    echo -e "${RED}✗${NC} API URL not configured"
    exit 1
fi

echo ""
echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}Configuration complete!${NC}"
echo -e "${GREEN}========================================${NC}"
echo ""
echo "Next steps:"
echo "1. Review the generated file: $OUTPUT_FILE"
echo "2. Update any optional variables (GA_ID, SENTRY_DSN)"
echo "3. Deploy frontend with this configuration"
echo ""
echo "For Vercel deployment:"
echo "  vercel env add NEXT_PUBLIC_API_URL $ENVIRONMENT"
echo "  (paste the value: $APP_RUNNER_URL)"
echo ""
