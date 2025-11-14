# Docker Secrets for Production Deployment

This guide explains how to set up and manage Docker secrets for secure production
deployments of FitFolio.

## Overview

Docker secrets provide a secure way to store sensitive configuration data such as
passwords, API keys, and tokens. Secrets are:

- Encrypted at rest and in transit
- Only accessible to services that explicitly require them
- Mounted as in-memory files (`/run/secrets/`) inside containers
- Never stored in images or environment variables

## Prerequisites

- Docker Swarm mode enabled (required for Docker secrets)
- Production environment (secrets are external to compose file)

## Setting Up Docker Swarm

If not already done, initialize Docker Swarm:

```bash
docker swarm init
```

## Creating Secrets

### Required Secrets

FitFolio requires the following secrets for production:

1. **postgres_password** - PostgreSQL database password
2. **smtp_username** - SMTP username for email service (optional)
3. **smtp_password** - SMTP password for email service (optional)

### Create Secrets from Command Line

#### Option 1: From String (Interactive)

```bash
# PostgreSQL password
echo "$(openssl rand -base64 32)" | docker secret create postgres_password -

# SMTP username (if using authenticated SMTP)
echo "your-smtp-username" | docker secret create smtp_username -

# SMTP password (if using authenticated SMTP)
echo "your-smtp-password" | docker secret create smtp_password -
```

#### Option 2: From File

Create secret files locally (ensure they're in `.gitignore`):

```bash
# Create secrets directory (local only)
mkdir -p .secrets
chmod 700 .secrets

# Generate and save secrets
openssl rand -base64 32 > .secrets/postgres_password
echo "your-smtp-username" > .secrets/smtp_username
echo "your-smtp-password" > .secrets/smtp_password

# Create Docker secrets from files
docker secret create postgres_password .secrets/postgres_password
docker secret create smtp_username .secrets/smtp_username
docker secret create smtp_password .secrets/smtp_password

# Securely delete local files
shred -u .secrets/*
rmdir .secrets
```

## Verifying Secrets

List all secrets:

```bash
docker secret ls
```

Expected output:

```
ID                          NAME                DRIVER    CREATED          UPDATED
abc123def456...             postgres_password             2 minutes ago    2 minutes ago
def456ghi789...             smtp_username                 2 minutes ago    2 minutes ago
ghi789jkl012...             smtp_password                 2 minutes ago    2 minutes ago
```

## Using Secrets in Production

### Deploy with Secrets

```bash
# Deploy the stack with secrets
docker stack deploy -c compose.prod.yml fitfolio

# Or with docker compose (v2.17+)
docker compose -f compose.prod.yml up -d
```

### Verify Secret Mounting

Check that secrets are mounted inside containers:

```bash
# List secrets in backend container
docker exec fitfolio-backend-prod ls -la /run/secrets

# Expected output:
# -r--r--r-- 1 root root  44 Nov 14 20:00 postgres_password
# -r--r--r-- 1 root root  20 Nov 14 20:00 smtp_username
# -r--r--r-- 1 root root  20 Nov 14 20:00 smtp_password
```

## Rotating Secrets

To update a secret (e.g., after a security incident):

```bash
# 1. Create new secret with different name
echo "new-secure-password" | docker secret create postgres_password_v2 -

# 2. Update compose.prod.yml to use new secret name
# Edit: postgres_password -> postgres_password_v2

# 3. Redeploy stack
docker stack deploy -c compose.prod.yml fitfolio

# 4. Remove old secret after verification
docker secret rm postgres_password
```

## Environment Variables vs Secrets

### When to Use Secrets

✅ Passwords, API keys, tokens ✅ Private keys, certificates ✅ Any sensitive data that
shouldn't be in version control

### When to Use Environment Variables

✅ Non-sensitive configuration (hostnames, ports) ✅ Feature flags ✅ Log levels ✅ CORS
origins

## How FitFolio Uses Secrets

### Backend Application

The backend reads secrets via the `app.core.secrets` module:

```python
from app.core.secrets import read_secret, get_database_url, get_smtp_username, get_smtp_password

# Automatic detection of Docker secrets vs environment variables
database_url = get_database_url()      # Reads postgres_password from /run/secrets
smtp_username = get_smtp_username()    # Reads smtp_username from /run/secrets (optional)
smtp_password = get_smtp_password()    # Reads smtp_password from /run/secrets (optional)
```

### Database Service

PostgreSQL uses the `POSTGRES_PASSWORD_FILE` variable to read from secrets:

```yaml
environment:
  POSTGRES_PASSWORD_FILE: /run/secrets/postgres_password
secrets:
  - postgres_password
```

## Troubleshooting

### Error: secret not found

**Problem**: `docker stack deploy` fails with "secret postgres_password not found"

**Solution**: Create the secret before deploying:

```bash
docker secret create postgres_password -
<paste password and press Ctrl+D>
```

### Permission Denied Reading Secrets

**Problem**: Backend cannot read `/run/secrets/postgres_password`

**Solution**: Secrets are only accessible to containers that declare them. Ensure
`compose.prod.yml` includes:

```yaml
services:
  backend:
    secrets:
      - postgres_password
```

### Development vs Production

**Problem**: Secrets don't work in development

**Solution**: Docker secrets require Swarm mode. For development, use `compose.dev.yml`
which uses environment variables from `.env` file.

## Security Best Practices

1. **Never commit secrets to version control**
   - Add `.secrets/` to `.gitignore`
   - Use `docker secret create` directly on production servers

2. **Use strong random values**

   ```bash
   openssl rand -base64 64  # Generates 64-byte random string
   ```

3. **Rotate secrets periodically**
   - Change passwords every 90 days
   - Use secret versioning (postgres_password_v2, etc.)

4. **Limit secret access**
   - Only grant secrets to services that need them
   - Use principle of least privilege

5. **Monitor secret access**
   ```bash
   docker service logs fitfolio_backend | grep "secret"
   ```

## Migration from Environment Variables

If migrating from `.env` file to secrets:

1. **Create secrets from existing values**:

   ```bash
   grep POSTGRES_PASSWORD .env | cut -d= -f2 | docker secret create postgres_password -
   grep SMTP_USERNAME .env | cut -d= -f2 | docker secret create smtp_username -
   grep SMTP_PASSWORD .env | cut -d= -f2 | docker secret create smtp_password -
   ```

2. **Update compose file** to use secrets (already done in `compose.prod.yml`)

3. **Test deployment**:

   ```bash
   docker stack deploy -c compose.prod.yml fitfolio-test
   ```

4. **Verify application starts**:

   ```bash
   docker service ps fitfolio-test_backend
   docker service logs fitfolio-test_backend
   ```

5. **Deploy to production** when verified

## Related Documentation

- [Production Deployment Guide](./PRODUCTION.md)
- [Environment Variables Reference](./ENVIRONMENT.md)
- [Security Best Practices](../security/BEST_PRACTICES.md)

## References

- [Docker Secrets Documentation](https://docs.docker.com/engine/swarm/secrets/)
- [Compose Secrets Specification](https://docs.docker.com/compose/compose-file/09-secrets/)
