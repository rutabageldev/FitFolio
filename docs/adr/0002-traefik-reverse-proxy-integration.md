# ADR-0002: Traefik Reverse Proxy Integration

**Status:** Accepted **Date:** 2025-10-31 **Deciders:** Development Team **Tags:**
deployment, infrastructure, traefik, security, ssl

## Context

FitFolio needed a reverse proxy solution for production deployment with the following
requirements:

- HTTPS/TLS termination with automatic certificate management
- Routing for both frontend and backend services
- Zero-downtime deployments
- Security headers
- HTTP to HTTPS redirects

The utility node VPS already runs Traefik for other services (UniFi, Vaultwarden).

**Alternatives Considered:**

1. **Nginx reverse proxy** - Traditional, widely used
2. **Caddy** - Modern, automatic HTTPS, simpler config
3. **Use existing Traefik** - Already running on VPS
4. **HAProxy** - High performance but more complex

**Constraints:**

- Traefik already installed and proven reliable
- Multiple services need to coexist on same VPS
- Let's Encrypt certificates already configured
- Want consistent configuration between dev and prod

## Decision

Use the existing Traefik instance for both development and production environments,
configured via Docker Compose labels.

**Architecture:**

- Traefik handles: reverse proxy, TLS termination, Let's Encrypt, routing
- Frontend container: Vite dev server (dev) or Nginx (prod) for static files
- Backend container: Uvicorn ASGI server
- Services declare routing via Docker labels (declarative config)

**Routing Rules:**

- Backend: `Host(fitfolio.*.rutabagel.com) && PathPrefix(/api)` (priority 10)
- Frontend: `Host(fitfolio.*.rutabagel.com)` (priority 1)
- Healthcheck: Available via backend at `/healthz`

**Networks:**

- `traefik-public`: External network for Traefik routing
- `default`: Internal network for service-to-service communication

## Rationale

**Why Traefik over Nginx:**

- Already running and proven on target VPS
- Automatic Let's Encrypt certificate management (no manual renewal)
- Declarative configuration via labels (infrastructure as code)
- Zero-downtime deployments (Traefik automatically updates routing)
- No additional infrastructure needed

**Why Docker labels over config files:**

- Configuration lives with the service (compose file)
- No separate Traefik config to maintain
- Changes deploy atomically with service updates
- Easy to test routing in development

**Why keep Nginx in frontend container:**

- Serves static files efficiently in production
- Handles SPA routing (fallback to index.html)
- Asset caching and compression
- Separation of concerns (Traefik routes, Nginx serves)

**Trade-offs:**

- Tied to Traefik ecosystem (but already committed)
- Learning curve for Traefik labels (mitigated by testing in dev)
- Less control than Nginx config (sufficient for our needs)

## Consequences

### Positive

- Zero-downtime deployments (Traefik auto-updates routes)
- Automatic SSL certificate renewal
- Consistent routing config between dev and prod
- Test exact production routing in development
- Infrastructure already proven reliable
- No additional services to maintain

### Negative

- Requires Traefik running in development
- More complex local setup (but containerized)
- Label syntax can be verbose

### Neutral

- Must use external `traefik-public` network
- Backend and frontend use different networks

## Implementation

**Development Configuration (`compose.dev.yml`):**

```yaml
backend:
  labels:
    - 'traefik.enable=true'
    - 'traefik.http.routers.fitfolio-backend.rule=Host(`fitfolio.dev.rutabagel.com`) &&
      PathPrefix(`/api`)'
    - 'traefik.http.routers.fitfolio-backend.entrypoints=websecure'
    - 'traefik.http.routers.fitfolio-backend.tls=true'
    - 'traefik.http.routers.fitfolio-backend.priority=10'
    - 'traefik.http.services.fitfolio-backend.loadbalancer.server.port=8000'
  networks:
    - traefik-public
    - default
```

**Production Configuration (`compose.prod.yml`):**

- Same label structure with production domain: `fitfolio.rutabagel.com`
- Backend container name: `fitfolio-backend-prod`
- Frontend uses nginx (port 80) instead of Vite dev server

**Vite Configuration (`frontend/vite.config.js`):**

```javascript
const allowedHosts = ['localhost', '.localhost'];
if (env.VITE_ALLOWED_HOST) {
  allowedHosts.push(env.VITE_ALLOWED_HOST);
}
server: {
  allowedHosts;
}
```

**Related Commits:**

- Traefik integration: `b688b8c`

**Files Modified:**

- `compose.dev.yml` - Added Traefik labels and networks
- `compose.prod.yml` - Complete overhaul with Traefik configuration
- `frontend/vite.config.js` - Dynamic allowed hosts
- `backend/app/main.py` - CORS configuration, API root endpoint

## References

- Related ADR: ADR-0001 (API Versioning) - `/api/v1` routing
- Traefik Documentation: https://doc.traefik.io/traefik/
- Analysis Document: `docs/REVERSE_PROXY_ANALYSIS.md`
- Let's Encrypt Integration: https://doc.traefik.io/traefik/https/acme/
