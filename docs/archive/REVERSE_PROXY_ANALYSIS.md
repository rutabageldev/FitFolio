# Reverse Proxy Analysis: Traefik vs Nginx

**Date:** 2025-10-29 **Context:** Production deployment for FitFolio with existing
Traefik infrastructure (UniFi, Vaultwarden) **Decision:** Choose reverse proxy for
multi-service production environment

---

## Executive Summary

**Recommendation: Traefik** ✅

**Rationale:**

1. Already running Traefik for UniFi and Vaultwarden
2. Automatic TLS with Let's Encrypt (zero-touch renewal)
3. Dynamic service discovery from Docker labels
4. Native multi-service routing on same host
5. Lower operational overhead (no config reload on changes)

**Key Insight:** You're already paying the learning curve cost with your existing
Traefik setup. Leveraging it for FitFolio is the path of least resistance.

---

## Current State Analysis

### Your Existing Infrastructure

**Utility Node (Current Production):**

- ✅ Traefik (reverse proxy)
- ✅ UniFi Controller
- ✅ Vaultwarden
- 🔄 FitFolio (to be added)

**FitFolio Current Setup:**

- Frontend: Nginx in container (serving static files)
- Backend: Gunicorn + Uvicorn (FastAPI)
- No reverse proxy yet

### The Question

Should we:

1. **Option A:** Add FitFolio to existing Traefik (harmonize)
2. **Option B:** Run separate Nginx reverse proxy for FitFolio (diverge)

---

## Detailed Comparison

### 1. Traefik (Modern, Dynamic, Container-Native)

#### Strengths ✅

**1. You Already Have It**

- Running for UniFi + Vaultwarden
- Configuration knowledge already in place
- Zero new learning curve
- Operational muscle memory established

**2. Automatic TLS with Let's Encrypt**

```yaml
# Just add this label - TLS is automatic
labels:
  - 'traefik.http.routers.fitfolio.tls.certresolver=letsencrypt'
```

- Zero-touch certificate issuance
- Automatic renewal (no cron jobs)
- Wildcard support (\*.rutabagel.com)
- HTTP → HTTPS redirect built-in

**3. Dynamic Service Discovery**

```yaml
# Add labels to your compose file - Traefik auto-discovers
services:
  backend:
    labels:
      - 'traefik.enable=true'
      - 'traefik.http.routers.backend.rule=Host(`rutabagel.com`) && PathPrefix(`/api`)'
      - 'traefik.http.services.backend.loadbalancer.server.port=8000'
```

- No config reload needed
- Services appear/disappear automatically
- Zero-downtime deployments

**4. Multi-Service Routing (Your Use Case)**

```
                    ┌─────────────────┐
                    │   Traefik :80   │
                    │   Traefik :443  │
                    └────────┬────────┘
                             │
           ┌─────────────────┼─────────────────┐
           │                 │                 │
    unifi.rutabagel.com  vault.rutabagel.com  rutabagel.com
           │                 │                 │
      ┌────▼────┐      ┌────▼────┐      ┌────▼────┐
      │  UniFi  │      │Vaultwarden│    │FitFolio │
      └─────────┘      └─────────┘      └─────────┘
```

**Single Traefik handles all services** - Perfect for your utility node.

**5. Built-in Features**

- Rate limiting (per service)
- Circuit breakers
- Retry logic
- Middleware chains (auth, headers, redirects)
- Metrics (Prometheus)
- Dashboard (web UI)
- WebSocket support

**6. Docker-Native**

- Reads service labels directly
- No file-based config (unless you want it)
- Scales horizontally (if needed later)

#### Weaknesses ⚠️

**1. Complexity for Simple Cases**

- Overkill if you only need static files
- More moving parts than Nginx

**2. Resource Usage**

- ~50-100MB RAM baseline
- Heavier than Nginx (~10MB)
- Negligible on modern hardware

**3. Debugging Can Be Tricky**

- Label-based config less visible than files
- Need to check logs + dashboard
- More abstraction layers

**4. Learning Curve (Mitigated)**

- Steep initial learning curve
- **But you've already climbed it!**

---

### 2. Nginx (Traditional, Battle-Tested, Simple)

#### Strengths ✅

**1. Already in Your Stack**

- Frontend container uses Nginx for static files
- Could extend it to reverse proxy role
- Familiar nginx.conf syntax

**2. Performance**

- Extremely fast (event-driven)
- Low memory footprint (~10MB)
- Handles 10K+ concurrent connections

**3. Simplicity**

- Config files are explicit and readable
- Easy to understand request flow
- Mature, stable, well-documented

**4. Static Content Champion**

- Best-in-class static file serving
- Efficient gzip/brotli compression
- Caching headers

**5. Battle-Tested**

- 20+ years of production use
- Every edge case handled
- Massive community knowledge

#### Weaknesses ⚠️

**1. Manual TLS Management**

```bash
# You'd need to set up certbot separately
certbot certonly --webroot -w /var/www/html -d rutabagel.com
# Cron job for renewal
0 0 * * * certbot renew --quiet
```

- Separate certbot setup
- Renewal automation via cron
- Manual intervention if renewal fails
- More moving parts

**2. Static Configuration**

```nginx
# Every change requires editing config + reload
upstream backend {
    server fitfolio-backend:8000;
}

server {
    listen 443 ssl;
    server_name rutabagel.com;

    ssl_certificate /etc/letsencrypt/live/rutabagel.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/rutabagel.com/privkey.pem;

    location /api/ {
        proxy_pass http://backend/;
    }
}
```

- Add new service = edit config + reload
- No automatic service discovery
- Requires careful reload orchestration

**3. Multi-Service Complexity**

```nginx
# You'd need separate server blocks or complex routing
server {
    server_name unifi.rutabagel.com;
    location / { proxy_pass http://unifi:8443; }
}
server {
    server_name vault.rutabagel.com;
    location / { proxy_pass http://vaultwarden:80; }
}
server {
    server_name rutabagel.com;
    location /api/ { proxy_pass http://fitfolio-backend:8000/; }
    location / { proxy_pass http://fitfolio-frontend:80/; }
}
```

**Problem:** This creates a second reverse proxy alongside Traefik:

```
┌─────────────────┐         ┌─────────────────┐
│   Traefik :80   │         │   Nginx :8080   │
│   Traefik :443  │         │   Nginx :8443   │
└────────┬────────┘         └────────┬────────┘
         │                           │
    ┌────┼────┐                      │
    │         │                      │
  UniFi  Vaultwarden              FitFolio
```

**Two reverse proxies = operational overhead + complexity.**

**4. No Built-in Service Discovery**

- Must manually track backend IPs/ports
- Docker Compose service names help, but still manual
- Adding/removing services requires config changes

---

## Decision Matrix

| Criteria                   | Traefik                      | Nginx                            | Winner      |
| -------------------------- | ---------------------------- | -------------------------------- | ----------- |
| **Already in Your Stack**  | ✅ Yes (UniFi/Vault)         | ⚠️ Frontend only                 | **Traefik** |
| **TLS Automation**         | ✅ Automatic (Let's Encrypt) | ⚠️ Manual (certbot)              | **Traefik** |
| **Multi-Service Routing**  | ✅ Native, label-based       | ⚠️ Manual config per service     | **Traefik** |
| **Service Discovery**      | ✅ Automatic (Docker labels) | ❌ None (manual config)          | **Traefik** |
| **Zero-Downtime Deploys**  | ✅ Automatic                 | ⚠️ Requires careful reload       | **Traefik** |
| **Operational Simplicity** | ✅ One proxy for all         | ⚠️ Two proxies (Traefik + Nginx) | **Traefik** |
| **Performance**            | ⚠️ Good (50-100MB RAM)       | ✅ Excellent (10MB RAM)          | **Nginx**   |
| **Config Visibility**      | ⚠️ Labels (less visible)     | ✅ Files (explicit)              | **Nginx**   |
| **Learning Curve**         | ✅ Already paid              | ✅ Familiar                      | **Tie**     |
| **Static File Serving**    | ⚠️ Can do it                 | ✅ Best-in-class                 | **Nginx**   |

**Score: Traefik 8, Nginx 3**

---

## Architectural Recommendations

### Recommended: Traefik as Reverse Proxy

**Architecture:**

```
                    Internet
                       │
                       ▼
                 ┌───────────┐
                 │ Traefik   │ :80, :443
                 │ (existing)│ Let's Encrypt
                 └─────┬─────┘
                       │
       ┌───────────────┼───────────────┐
       │               │               │
    UniFi          Vaultwarden      FitFolio
  :8443 (existing)  :80 (existing)     │
                                       │
                        ┌──────────────┼──────────────┐
                        │              │              │
                  Frontend :80    Backend :8000   PostgreSQL
                  (Nginx serves    (Gunicorn)        Redis
                   static files)
```

**Key Insight:** Nginx stays in the FitFolio frontend container for static file serving
(its strength), while Traefik handles all reverse proxy duties (its strength).

**Role Separation:**

- **Traefik:** TLS termination, routing, external access
- **Nginx:** Static file serving inside frontend container

**Benefits:**

1. ✅ Single reverse proxy (Traefik) for all services
2. ✅ Nginx still used for its strength (static files)
3. ✅ No config duplication or maintenance burden
4. ✅ Automatic TLS for all services
5. ✅ Easy to add future services

---

## Implementation Plan

### Phase 3: Add FitFolio to Traefik

#### 1. Update compose.prod.yml

```yaml
services:
  backend:
    image: fitfolio-backend:prod
    container_name: fitfolio-backend-prod
    networks:
      - fitfolio
      - traefik-net # Connect to Traefik network
    labels:
      - 'traefik.enable=true'
      - 'traefik.docker.network=traefik-net'

      # Backend API routing
      - 'traefik.http.routers.fitfolio-backend.rule=Host(`rutabagel.com`) &&
        PathPrefix(`/api`)'
      - 'traefik.http.routers.fitfolio-backend.entrypoints=websecure'
      - 'traefik.http.routers.fitfolio-backend.tls.certresolver=letsencrypt'
      - 'traefik.http.services.fitfolio-backend.loadbalancer.server.port=8000'

      # Strip /api prefix (optional, depends on backend routes)
      - 'traefik.http.middlewares.fitfolio-strip.stripprefix.prefixes=/api'
      - 'traefik.http.routers.fitfolio-backend.middlewares=fitfolio-strip'

  frontend:
    image: fitfolio-frontend:prod
    container_name: fitfolio-frontend-prod
    networks:
      - traefik-net
    labels:
      - 'traefik.enable=true'
      - 'traefik.docker.network=traefik-net'

      # Frontend routing (all other requests)
      - 'traefik.http.routers.fitfolio-frontend.rule=Host(`rutabagel.com`)'
      - 'traefik.http.routers.fitfolio-frontend.entrypoints=websecure'
      - 'traefik.http.routers.fitfolio-frontend.tls.certresolver=letsencrypt'
      - 'traefik.http.routers.fitfolio-frontend.priority=1' # Lower priority than backend
      - 'traefik.http.services.fitfolio-frontend.loadbalancer.server.port=80'

      # HTTP -> HTTPS redirect
      - 'traefik.http.routers.fitfolio-http.rule=Host(`rutabagel.com`)'
      - 'traefik.http.routers.fitfolio-http.entrypoints=web'
      - 'traefik.http.routers.fitfolio-http.middlewares=redirect-to-https'
      - 'traefik.http.middlewares.redirect-to-https.redirectscheme.scheme=https'

networks:
  fitfolio:
    internal: true # Backend/DB/Redis communication
  traefik-net:
    external: true # Your existing Traefik network
```

#### 2. Traefik Configuration (if not already set up)

```yaml
# Your existing Traefik config (likely already has this)
version: '3.8'

services:
  traefik:
    image: traefik:v3.0
    command:
      - '--api.dashboard=true'
      - '--providers.docker=true'
      - '--providers.docker.exposedbydefault=false'
      - '--entrypoints.web.address=:80'
      - '--entrypoints.websecure.address=:443'
      - '--certificatesresolvers.letsencrypt.acme.email=your@email.com'
      - '--certificatesresolvers.letsencrypt.acme.storage=/letsencrypt/acme.json'
      - '--certificatesresolvers.letsencrypt.acme.httpchallenge.entrypoint=web'
    ports:
      - '80:80'
      - '443:443'
    volumes:
      - '/var/run/docker.sock:/var/run/docker.sock:ro'
      - 'traefik-certs:/letsencrypt'
    networks:
      - traefik-net

networks:
  traefik-net:
    driver: bridge

volumes:
  traefik-certs:
```

#### 3. Frontend Nginx Config (No Changes Needed)

Your existing [frontend/nginx.conf](frontend/nginx.conf) and
[frontend/default.conf](frontend/default.conf) stay as-is. Nginx continues serving
static files, Traefik handles external access.

---

## Migration Strategy

### Option 1: Fresh Deployment (Recommended)

Add FitFolio to your existing Traefik stack from day one.

**Steps:**

1. Update compose.prod.yml with Traefik labels (above)
2. `docker compose -f compose.prod.yml up -d`
3. Traefik automatically issues TLS cert
4. Done ✅

**Time:** ~30 minutes **Risk:** Low (no existing FitFolio users to disrupt)

### Option 2: Test Environment First

If you want to validate before touching production:

1. Spin up test Traefik + FitFolio stack
2. Validate TLS, routing, health checks
3. Apply to production

**Time:** ~2 hours **Risk:** Very Low

---

## Alternative: Pure Nginx (If You Insist)

**If you really want Nginx as reverse proxy:**

### Pros:

- Consolidate on one technology (Nginx)
- Simpler mental model (all config in files)

### Cons:

- **Must migrate UniFi and Vaultwarden from Traefik to Nginx**
- Manual TLS management (certbot for all services)
- No automatic service discovery
- More operational overhead

### Recommendation:

❌ **Don't do this.** You'd be throwing away working Traefik setup for minimal gain.

---

## Cost-Benefit Analysis

### Traefik (Recommended)

**Benefits:**

- ✅ Leverage existing infrastructure (sunk cost)
- ✅ Automatic TLS (Let's Encrypt)
- ✅ Zero-touch service addition/removal
- ✅ Unified operational model (all services)
- ✅ Lower long-term maintenance

**Costs:**

- ⚠️ ~50MB extra RAM (negligible)
- ⚠️ Label-based config (less visible)

**Time Investment:**

- Setup: ~1 hour (add labels to compose)
- Maintenance: ~0 hours/month (automatic)

### Nginx (Alternative)

**Benefits:**

- ✅ Slightly lower resource usage
- ✅ Config files (more visible)

**Costs:**

- ❌ Manual TLS management (certbot setup + cron)
- ❌ Static config (reload on changes)
- ❌ Two reverse proxies (Traefik + Nginx)
- ❌ No service discovery

**Time Investment:**

- Setup: ~3-4 hours (certbot, config, testing)
- Maintenance: ~1-2 hours/month (cert renewals, config changes)

---

## Final Recommendation

### Use Traefik as Reverse Proxy ✅

**Decision Rationale:**

1. **You already have it** - Sunk cost, leverage existing investment
2. **Operational harmony** - All services (UniFi, Vaultwarden, FitFolio) use same proxy
3. **Automatic TLS** - Zero-touch Let's Encrypt (saves hours per year)
4. **Future-proof** - Easy to add more services (just labels)
5. **Lower maintenance** - No config reloads, no manual cert management

### Architecture:

```
Traefik (reverse proxy, TLS termination) ← You focus here
  ├─ UniFi
  ├─ Vaultwarden
  └─ FitFolio
      ├─ Frontend (Nginx serves static files) ← Nginx stays here
      └─ Backend (Gunicorn + Uvicorn)
```

**Best of both worlds:** Traefik for routing/TLS, Nginx for static file serving.

---

## Next Steps

1. ✅ Review this analysis
2. Update compose.prod.yml with Traefik labels
3. Test deployment on utility node
4. Validate TLS certificate issuance
5. Update ROADMAP.md with chosen approach

---

## References

- [Traefik Documentation](https://doc.traefik.io/traefik/)
- [Traefik + Docker Compose Guide](https://doc.traefik.io/traefik/user-guides/docker-compose/basic-example/)
- [Let's Encrypt with Traefik](https://doc.traefik.io/traefik/https/acme/)
- Your existing Traefik setup (UniFi + Vaultwarden)

---

**Document Version:** 1.0 **Date:** 2025-10-29 **Decision:** Traefik as reverse proxy
(leverage existing infrastructure)
