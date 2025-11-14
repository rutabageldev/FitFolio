#!/bin/bash
# Check if development Docker secrets are properly configured
# This script validates that required secret files exist when USE_DOCKER_SECRETS=true

set -e

SECRETS_DIR=".secrets"
RED='\033[0;31m'
YELLOW='\033[1;33m'
GREEN='\033[0;32m'
NC='\033[0m' # No Color

# Check if we're using Docker secrets
USE_DOCKER_SECRETS=$(grep -E "^USE_DOCKER_SECRETS=" compose.dev.yml 2>/dev/null | grep -o '"true"' || echo "false")

if [ "$USE_DOCKER_SECRETS" != '"true"' ]; then
    # Not using Docker secrets in dev, skip check
    exit 0
fi

# Required secrets for development
REQUIRED_SECRETS=(
    "postgres_password"
    "smtp_username"
    "smtp_password"
)

missing_secrets=()

# Check each required secret
for secret in "${REQUIRED_SECRETS[@]}"; do
    secret_file="$SECRETS_DIR/$secret"
    if [ ! -f "$secret_file" ]; then
        missing_secrets+=("$secret")
    fi
done

# Report results
if [ ${#missing_secrets[@]} -eq 0 ]; then
    echo -e "${GREEN}✓ All required dev secrets are present${NC}"
    exit 0
else
    echo -e "${RED}✗ Missing required dev secrets:${NC}"
    for secret in "${missing_secrets[@]}"; do
        echo -e "  ${YELLOW}- $secret${NC}"
    done
    echo ""
    echo -e "${YELLOW}Run 'make setup-dev-secrets' to generate them automatically.${NC}"
    exit 1
fi
