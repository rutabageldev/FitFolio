#!/bin/bash
# Setup development Docker secrets
# This script creates the necessary secret files for local development

set -e

SECRETS_DIR=".secrets"
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo "Setting up development Docker secrets..."
echo ""

# Create secrets directory if it doesn't exist
mkdir -p "$SECRETS_DIR"
chmod 700 "$SECRETS_DIR"

# Function to create or update a secret
setup_secret() {
    local secret_name=$1
    local env_var=$2
    local default_value=$3
    local secret_file="$SECRETS_DIR/$secret_name"

    if [ -f "$secret_file" ]; then
        echo -e "${YELLOW}Secret '$secret_name' already exists. Skipping.${NC}"
        return
    fi

    # Try to read from .env file first
    if [ -f ".env" ] && grep -q "^${env_var}=" ".env"; then
        value=$(grep "^${env_var}=" ".env" | cut -d= -f2- | tr -d '"' | tr -d "'")
        if [ -n "$value" ]; then
            echo "$value" > "$secret_file"
            chmod 600 "$secret_file"
            echo -e "${GREEN}✓ Created '$secret_name' from .env${NC}"
            return
        fi
    fi

    # Fall back to default value if provided
    if [ -n "$default_value" ]; then
        echo "$default_value" > "$secret_file"
        chmod 600 "$secret_file"
        echo -e "${GREEN}✓ Created '$secret_name' with default value${NC}"
        return
    fi

    # Generate random value
    random_value=$(openssl rand -base64 32)
    echo "$random_value" > "$secret_file"
    chmod 600 "$secret_file"
    echo -e "${GREEN}✓ Generated random value for '$secret_name'${NC}"
}

# Setup each secret
echo "Setting up secrets..."
echo ""

# PostgreSQL password
setup_secret "postgres_password" "POSTGRES_PASSWORD" "supersecret"

# SMTP username (optional, can be empty for Mailpit)
setup_secret "smtp_username" "SMTP_USERNAME" ""

# SMTP password (optional, can be empty for Mailpit)
setup_secret "smtp_password" "SMTP_PASSWORD" ""

echo ""
echo -e "${GREEN}Development secrets setup complete!${NC}"
echo ""
echo "Created files:"
ls -lh "$SECRETS_DIR/"
echo ""
echo "⚠️  These files contain sensitive data and are excluded from git."
echo "⚠️  Make sure to run 'docker compose -f compose.dev.yml up' to use them."
echo ""
