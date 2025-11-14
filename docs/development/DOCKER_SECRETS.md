# Docker Secrets in Development

This guide explains how to use Docker secrets in the development environment for
dev/prod parity.

## Why Use Docker Secrets in Development?

Using Docker secrets in development ensures:

1. **Dev/Prod Parity**: Development environment mirrors production secret handling
2. **Early Testing**: Validates secret injection mechanism before deployment
3. **Security Practice**: Developers work with secure patterns from the start
4. **Easier Debugging**: Issues with secret reading are caught locally

## Quick Start

### 1. Setup Secrets

Run the setup script to create secret files:

```bash
make setup-dev-secrets
```

This will:

- Create `.secrets/` directory
- Generate secret files from your `.env` file or random values
- Set proper file permissions (600)

### 2. Start Development Stack

```bash
make up
```

Docker Compose will automatically mount the secret files into `/run/secrets/` in your
containers.

## Manual Setup

If you prefer to create secrets manually:

```bash
# Create secrets directory
mkdir -p .secrets
chmod 700 .secrets

# Create secret files
echo "supersecret" > .secrets/postgres_password
echo "" > .secrets/smtp_username
echo "" > .secrets/smtp_password

# Set permissions
chmod 600 .secrets/*
```

## How It Works

### File-Based Secrets vs Swarm Secrets

**Production (Swarm mode)**:

- Secrets stored in encrypted Swarm raft log
- Managed with `docker secret create`
- Automatically mounted to `/run/secrets/` as tmpfs

**Development (Compose mode)**:

- Secrets stored in `.secrets/` directory (gitignored)
- Defined in `compose.dev.yml` with `file:` reference
- Mounted to `/run/secrets/` just like production

### Secret Mounting

When you start the dev stack, Docker Compose:

1. Reads secret files from `.secrets/`
2. Mounts them into containers at `/run/secrets/`
3. Application reads from `/run/secrets/` (same path as production)

```yaml
# compose.dev.yml
services:
  backend:
    secrets:
      - postgres_password
      - smtp_username
      - smtp_password

secrets:
  postgres_password:
    file: ./.secrets/postgres_password
  smtp_username:
    file: ./.secrets/smtp_username
  smtp_password:
    file: ./.secrets/smtp_password
```

### Application Integration

The backend automatically detects and reads secrets when `USE_DOCKER_SECRETS=true`:

```python
# app/core/secrets.py
def read_secret(secret_name: str, default: str | None = None) -> str:
    """Read from /run/secrets/ or fallback to environment variables."""
    use_docker_secrets = os.getenv("USE_DOCKER_SECRETS", "").lower() in ("true", "1", "yes")

    if use_docker_secrets:
        secret_path = Path("/run/secrets") / secret_name
        if secret_path.exists():
            return secret_path.read_text().strip()

    # Fallback to environment variable
    return os.getenv(secret_name.upper())
```

## Verifying Secrets

### Check Secret Files Are Mounted

```bash
# List secrets in backend container
docker exec fitfolio-backend ls -la /run/secrets

# Expected output:
# -rw-r--r-- 1 root root  11 Nov 14 20:00 postgres_password
# -rw-r--r-- 1 root root   0 Nov 14 20:00 smtp_username
# -rw-r--r-- 1 root root   0 Nov 14 20:00 smtp_password
```

### Test Secret Reading

```bash
# Read a secret from inside container
docker exec fitfolio-backend cat /run/secrets/postgres_password
```

### Check Application Logs

```bash
make be-logs
```

Look for any errors related to secret reading during startup.

## Updating Secrets

To change a secret value:

```bash
# 1. Stop the stack
make down

# 2. Update the secret file
echo "new-password" > .secrets/postgres_password

# 3. Restart the stack
make up
```

## Migrating from Environment Variables

If you're migrating from `.env` to secrets:

1. **Run setup script** (automatically migrates from `.env`):

   ```bash
   make setup-dev-secrets
   ```

2. **Verify secrets are created**:

   ```bash
   ls -la .secrets/
   ```

3. **Start stack and test**:

   ```bash
   make up
   make be-health
   ```

4. **Optional: Remove sensitive values from `.env`** (keep structure for reference)

## Troubleshooting

### Error: "Secret not found"

**Problem**: Application can't find secret file

**Solution**:

1. Verify secrets exist locally:
   ```bash
   ls -la .secrets/
   ```
2. Run setup script:
   ```bash
   make setup-dev-secrets
   ```
3. Restart containers:
   ```bash
   make down && make up
   ```

### Error: "Permission denied" reading secret

**Problem**: Secret file has wrong permissions

**Solution**:

```bash
chmod 600 .secrets/*
```

### Secrets Not Updating

**Problem**: Changed secret file but application still uses old value

**Solution**:

```bash
# Docker Compose caches secret mounts, need to recreate containers
make down
make up
```

### Backend Health Check Fails

**Problem**: Backend can't connect to database after enabling secrets

**Solution**:

1. Check database password secret matches:
   ```bash
   docker exec fitfolio-db cat /run/secrets/postgres_password
   docker exec fitfolio-backend cat /run/secrets/postgres_password
   ```
2. Verify `USE_DOCKER_SECRETS=true` is set in `compose.dev.yml`

## Security Notes

### Git Exclusion

The `.secrets/` directory is automatically excluded from git via `.gitignore`:

```gitignore
# Docker secrets (development)
.secrets/*
!.secrets/.gitkeep
```

**⚠️ Never commit secret files to git!**

### File Permissions

Secret files should have restricted permissions:

```bash
# Directory: owner read/write/execute only
chmod 700 .secrets/

# Files: owner read/write only
chmod 600 .secrets/*
```

### Secret Rotation

For development, you can easily rotate secrets:

```bash
# Generate new database password
openssl rand -base64 32 > .secrets/postgres_password

# Restart to apply
make down && make up
```

### Local-Only Secrets

Development secrets should be:

- ✅ Strong enough to simulate production (e.g., long random values)
- ✅ Different from production secrets (never copy prod secrets to dev)
- ✅ Shared within the team securely (not via git)

## Comparison: Dev vs Prod

| Aspect           | Development                    | Production                    |
| ---------------- | ------------------------------ | ----------------------------- |
| Storage          | `.secrets/` files (gitignored) | Docker Swarm encrypted raft   |
| Creation         | `make setup-dev-secrets`       | `docker secret create`        |
| Management       | Edit files locally             | `docker secret` commands      |
| Distribution     | Team-specific (secure channel) | CI/CD or manual on server     |
| Mount Location   | `/run/secrets/`                | `/run/secrets/`               |
| Application Code | Same (`app/core/secrets.py`)   | Same (`app/core/secrets.py`)  |
| Rotation         | Replace file, restart          | Create new version, redeploy  |
| Security         | File permissions (600)         | Encrypted at rest and transit |

## Best Practices

1. **Use setup script** for consistency:

   ```bash
   make setup-dev-secrets
   ```

2. **Keep secrets out of git** - always verify `.gitignore` includes `.secrets/*`

3. **Use strong random values** even in development:

   ```bash
   openssl rand -base64 32  # For database password
   ```

4. **Document team secret sharing** - use secure channels (1Password, LastPass,
   encrypted files)

5. **Test secret injection early** - don't wait until production to validate

6. **Sync dev and prod secret names** - ensure consistency in `compose.dev.yml` and
   `compose.prod.yml`

## Related Documentation

- [Production Docker Secrets Guide](../deployment/DOCKER_SECRETS.md)
- [Environment Variables Reference](../deployment/ENVIRONMENT.md)
- [Development Setup](./SETUP.md)

## References

- [Docker Compose Secrets](https://docs.docker.com/compose/use-secrets/)
- [Docker Swarm Secrets](https://docs.docker.com/engine/swarm/secrets/)
