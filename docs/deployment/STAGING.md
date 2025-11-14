# Staging Environment

This guide covers staging deployment, secrets, and promotion workflow.

## Domain and Routing

- Domain: `staging.fitfolio.rutabagel.com`
- Reverse proxy: Traefik on the external `traefik-public` network
- TLS: ACME (Let's Encrypt) via Traefik

## Secrets (create in staging)

```bash
echo "staging-db-password" | docker secret create postgres_password_staging -
echo "staging-smtp-username" | docker secret create smtp_username_staging -
echo "staging-smtp-password" | docker secret create smtp_password_staging -
```

## Deploy

Use immutable tags:

```bash
export GHCR_OWNER=rutabageldev
export GHCR_REPO=fitfolio
export IMAGE_TAG=sha-<commit>   # e.g., sha-$(git rev-parse --short=12 HEAD)

docker compose -f compose.staging.yml pull
docker compose -f compose.staging.yml up -d
```

Run DB migrations:

```bash
make migrate-staging
```

Smoke test:

```bash
make smoke-staging
```

## Promotion to Production

Promote the same `IMAGE_TAG` to production once staging is green:

```bash
export IMAGE_TAG=sha-<commit>
docker compose -f compose.prod.yml pull
docker compose -f compose.prod.yml up -d
```

## Mail in Staging

- Mailpit is included for staging. It is not exposed publicly (no host ports).
- For near-prod testing, use provider sandbox credentials (e.g., SendGrid/SES) with
  safelists.

## Rollback

Redeploy a previously known-good `IMAGE_TAG` and re-run smoke tests.
