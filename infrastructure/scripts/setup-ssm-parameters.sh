#!/bin/bash
set -euo pipefail

# AxiePro SSM Parameter Setup Script
# Creates and verifies all required SSM parameters for a given environment

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
MANIFEST_FILE="$SCRIPT_DIR/../config/ssm-parameters.json"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Default values
ENVIRONMENT="${1:-dev}"
REGION="${2:-us-west-2}"
DRY_RUN="${3:-false}"

echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}AxiePro SSM Parameter Setup${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""
echo "Environment: $ENVIRONMENT"
echo "Region: $REGION"
echo "Dry Run: $DRY_RUN"
echo ""

# Check if jq is installed
if ! command -v jq &> /dev/null; then
    echo -e "${RED}Error: jq is not installed. Install with: brew install jq${NC}"
    exit 1
fi

# Check if AWS CLI is installed
if ! command -v aws &> /dev/null; then
    echo -e "${RED}Error: AWS CLI is not installed.${NC}"
    exit 1
fi

# Check AWS credentials
if ! aws sts get-caller-identity &> /dev/null; then
    echo -e "${RED}Error: AWS credentials not configured.${NC}"
    exit 1
fi

# Function to generate random secret
generate_secret() {
    local length=$1
    openssl rand -base64 $length | tr -d "=+/" | cut -c1-$length
}

# Function to get CDK output value
get_cdk_output() {
    local stack_name=$1
    local output_key=$2

    aws cloudformation describe-stacks \
        --stack-name "$stack_name" \
        --region "$REGION" \
        --query "Stacks[0].Outputs[?OutputKey=='$output_key'].OutputValue" \
        --output text 2>/dev/null || echo ""
}

# Function to check if parameter exists
parameter_exists() {
    local param_name=$1
    aws ssm get-parameter \
        --name "$param_name" \
        --region "$REGION" \
        &> /dev/null
    return $?
}

# Function to create/update parameter
create_parameter() {
    local param_name=$1
    local param_value=$2
    local param_type=$3
    local overwrite=$4

    if [ "$DRY_RUN" = "true" ]; then
        echo -e "${YELLOW}[DRY RUN]${NC} Would create: $param_name"
        return 0
    fi

    if [ "$overwrite" = "true" ]; then
        aws ssm put-parameter \
            --name "$param_name" \
            --value "$param_value" \
            --type "$param_type" \
            --region "$REGION" \
            --overwrite \
            &> /dev/null
    else
        aws ssm put-parameter \
            --name "$param_name" \
            --value "$param_value" \
            --type "$param_type" \
            --region "$REGION" \
            &> /dev/null
    fi

    return $?
}

# Counters
TOTAL=0
CREATED=0
EXISTS=0
MANUAL=0
MISSING=0

# Read manifest and process parameters
echo -e "${BLUE}Processing parameters from manifest...${NC}"
echo ""

# Process each parameter category
for category in $(jq -r '.parameters | keys[]' "$MANIFEST_FILE"); do
    echo -e "${GREEN}Category: $category${NC}"

    # Get parameters in category
    params=$(jq -c ".parameters.$category.parameters[]" "$MANIFEST_FILE")

    while IFS= read -r param; do
        TOTAL=$((TOTAL + 1))

        # Extract parameter details
        param_name=$(echo "$param" | jq -r '.name' | sed "s/{env}/$ENVIRONMENT/g")
        param_desc=$(echo "$param" | jq -r '.description')
        param_type=$(echo "$param" | jq -r '.type')
        param_required=$(echo "$param" | jq -r '.required')
        param_default=$(echo "$param" | jq -r '.default // empty')
        param_manual=$(echo "$param" | jq -r '.manual // false')
        param_auto_gen=$(echo "$param" | jq -r '.auto_generate // false')
        param_source=$(echo "$param" | jq -r '.source // empty')
        param_source_key=$(echo "$param" | jq -r '.source_key // empty')

        # Check if parameter already exists
        if parameter_exists "$param_name"; then
            echo -e "  ${GREEN}✓${NC} $param_name (exists)"
            EXISTS=$((EXISTS + 1))
            continue
        fi

        # Determine parameter value
        param_value=""

        # Auto-generate secrets
        if [ "$param_auto_gen" = "true" ]; then
            param_length=$(echo "$param" | jq -r '.length // 32')
            param_value=$(generate_secret "$param_length")
            echo -e "  ${GREEN}+${NC} $param_name (auto-generated)"

        # Get from CDK output
        elif [ -n "$param_source" ] && [ "$param_source" = "cdk_output" ]; then
            stack_name=$(echo "$param_source_key" | cut -d'.' -f1)
            output_key=$(echo "$param_source_key" | cut -d'.' -f2)
            param_value=$(get_cdk_output "axiepro-$stack_name-$ENVIRONMENT" "$output_key")

            if [ -z "$param_value" ]; then
                echo -e "  ${YELLOW}⚠${NC} $param_name (CDK output not found: $param_source_key)"
                if [ "$param_required" = "true" ]; then
                    MISSING=$((MISSING + 1))
                fi
                continue
            fi
            echo -e "  ${GREEN}+${NC} $param_name (from CDK)"

        # Use default value
        elif [ -n "$param_default" ]; then
            param_value="$param_default"
            echo -e "  ${GREEN}+${NC} $param_name (default)"

        # Requires manual input
        elif [ "$param_manual" = "true" ]; then
            echo -e "  ${YELLOW}⊙${NC} $param_name (requires manual configuration)"
            echo -e "      Description: $param_desc"
            MANUAL=$((MANUAL + 1))

            # Create placeholder for required parameters
            if [ "$param_required" = "true" ]; then
                param_value="PLACEHOLDER_CHANGE_ME"
            else
                continue
            fi

        # Required but no value
        elif [ "$param_required" = "true" ]; then
            echo -e "  ${RED}✗${NC} $param_name (required but no value)"
            MISSING=$((MISSING + 1))
            continue

        # Optional, skip
        else
            echo -e "  ${BLUE}○${NC} $param_name (optional, skipped)"
            continue
        fi

        # Create parameter
        if [ -n "$param_value" ]; then
            if create_parameter "$param_name" "$param_value" "$param_type" "false"; then
                CREATED=$((CREATED + 1))
            else
                echo -e "  ${RED}✗${NC} Failed to create $param_name"
                MISSING=$((MISSING + 1))
            fi
        fi

    done <<< "$params"

    echo ""
done

# Summary
echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}Summary${NC}"
echo -e "${BLUE}========================================${NC}"
echo "Total parameters: $TOTAL"
echo -e "${GREEN}Existing: $EXISTS${NC}"
echo -e "${GREEN}Created: $CREATED${NC}"
echo -e "${YELLOW}Requires manual setup: $MANUAL${NC}"
echo -e "${RED}Missing (required): $MISSING${NC}"
echo ""

# Manual setup instructions
if [ $MANUAL -gt 0 ]; then
    echo -e "${YELLOW}========================================${NC}"
    echo -e "${YELLOW}Manual Setup Required${NC}"
    echo -e "${YELLOW}========================================${NC}"
    echo ""
    echo "The following parameters require manual configuration:"
    echo ""

    for category in $(jq -r '.parameters | keys[]' "$MANIFEST_FILE"); do
        params=$(jq -c ".parameters.$category.parameters[] | select(.manual == true)" "$MANIFEST_FILE")

        if [ -n "$params" ]; then
            while IFS= read -r param; do
                param_name=$(echo "$param" | jq -r '.name' | sed "s/{env}/$ENVIRONMENT/g")
                param_desc=$(echo "$param" | jq -r '.description')
                param_instructions=$(echo "$param" | jq -r '.instructions // "No instructions provided"')

                echo "Parameter: $param_name"
                echo "  Description: $param_desc"
                echo "  Instructions: $param_instructions"
                echo ""
                echo "  To set:"
                echo "  aws ssm put-parameter \\"
                echo "    --name \"$param_name\" \\"
                echo "    --value \"YOUR_VALUE_HERE\" \\"
                echo "    --type \"SecureString\" \\"
                echo "    --region \"$REGION\""
                echo ""
            done <<< "$params"
        fi
    done
fi

# Export to .env format for local development
if [ "$DRY_RUN" = "false" ] && [ $CREATED -gt 0 ]; then
    ENV_FILE="$SCRIPT_DIR/../../backend/.env.${ENVIRONMENT}"
    echo -e "${BLUE}Exporting parameters to $ENV_FILE${NC}"

    echo "# Auto-generated from SSM Parameter Store" > "$ENV_FILE"
    echo "# Environment: $ENVIRONMENT" >> "$ENV_FILE"
    echo "# Generated: $(date)" >> "$ENV_FILE"
    echo "" >> "$ENV_FILE"

    # Export database parameters
    echo "DATABASE_HOST=$(aws ssm get-parameter --name "/axiepro/$ENVIRONMENT/database/host" --region "$REGION" --query "Parameter.Value" --output text 2>/dev/null || echo "")" >> "$ENV_FILE"
    echo "DATABASE_PORT=$(aws ssm get-parameter --name "/axiepro/$ENVIRONMENT/database/port" --region "$REGION" --query "Parameter.Value" --output text 2>/dev/null || echo "5432")" >> "$ENV_FILE"
    echo "DATABASE_NAME=$(aws ssm get-parameter --name "/axiepro/$ENVIRONMENT/database/name" --region "$REGION" --query "Parameter.Value" --output text 2>/dev/null || echo "axiepro")" >> "$ENV_FILE"

    echo -e "${GREEN}Environment file created: $ENV_FILE${NC}"
fi

# Exit with appropriate code
if [ $MISSING -gt 0 ]; then
    echo -e "${RED}Setup incomplete. Please configure missing parameters.${NC}"
    exit 1
elif [ $MANUAL -gt 0 ]; then
    echo -e "${YELLOW}Setup requires manual configuration. See instructions above.${NC}"
    exit 2
else
    echo -e "${GREEN}✓ All parameters configured successfully!${NC}"
    exit 0
fi
