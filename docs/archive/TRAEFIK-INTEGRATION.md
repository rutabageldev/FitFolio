# FitFolio Traefik Integration

**Status:** Ready to deploy **Date:** October 30, 2025 **Domain:**
https://fitfolio.dev.rutabagel.com

---

## What Changed

A new Traefik-integrated compose file has been created: **`compose.dev.traefik.yml`**

This file adds Traefik routing to FitFolio while maintaining your existing development
workflow.

---

## Key Changes

### 1. Network Configuration

**Added `traefik-public` network to frontend and backend:**

- Frontend and backend join the external `traefik-public` network
- Database, Redis, and Mail services stay on internal network only
- Services can still communicate internally via default network

### 2. Routing Configuration

**Frontend:**

- Domain: `https://fitfolio.dev.rutabagel.com`
- Routes: All paths except `/api` go to frontend
- Port: 5173 (Vite dev server)
- Middleware: `web-chain@file` (compression + security headers)

**Backend API:**

- Domain: `https://fitfolio.dev.rutabagel.com/api`
- Routes: All `/api` paths go to backend
- Port: 8000 (FastAPI/Uvicorn)
- Middleware: `api-chain@file,cors-dev@file` (compression + security + rate limiting +
  CORS)

### 3. Port Changes

**Removed external port exposure for:**

- Frontend (was 5173) - Now accessed via Traefik
- Backend (was 8080) - Now accessed via Traefik

**Kept exposed for development:**

- PostgreSQL (5432) - For DB clients/tools
- Redis (6379) - For Redis clients/tools
- Mailpit UI (8025) - For email testing

### 4. Environment Variables

**Updated frontend environment:**

```yaml
environment:
  - VITE_API_BASE_URL=https://fitfolio.dev.rutabagel.com/api
```

This tells your frontend to call the API through Traefik at the same domain.

---

## How to Use

### Option 1: Use Traefik-Integrated Version (Recommended)

```bash
cd ~/projects/fitfolio

# Use the Traefik-integrated compose file
docker compose -f compose.dev.traefik.yml up -d

# View logs
docker compose -f compose.dev.traefik.yml logs -f

# Stop services
docker compose -f compose.dev.traefik.yml down
```

### Option 2: Keep Original Direct Access

Your original `compose.dev.yml` is unchanged. You can still use it for direct port
access:

```bash
cd ~/projects/fitfolio

# Use original compose file
docker compose -f compose.dev.yml up -d
```

**Why keep both?**

- Use Traefik version when testing full production-like setup
- Use direct version for quick debugging or when Traefik is down

---

## Access URLs

### With Traefik Integration (compose.dev.traefik.yml)

- **Frontend:** https://fitfolio.dev.rutabagel.com
- **Backend API:** https://fitfolio.dev.rutabagel.com/api
- **Mailpit UI:** http://localhost:8025
- **PostgreSQL:** localhost:5432
- **Redis:** localhost:6379

### With Direct Access (compose.dev.yml)

- **Frontend:** http://localhost:5173
- **Backend API:** http://localhost:8080
- **Mailpit UI:** http://localhost:8025
- **PostgreSQL:** localhost:5432
- **Redis:** localhost:6379

---

## Routing Details

### How Requests are Routed

1. **Frontend Requests**

   ```
   https://fitfolio.dev.rutabagel.com/
   https://fitfolio.dev.rutabagel.com/workouts
   https://fitfolio.dev.rutabagel.com/profile
   → Traefik → Frontend container (port 5173)
   ```

2. **API Requests**

   ```
   https://fitfolio.dev.rutabagel.com/api/v1/workouts
   https://fitfolio.dev.rutabagel.com/api/auth/login
   → Traefik → Backend container (port 8000)
   ```

3. **Priority System**
   - Backend router priority: 10 (higher - matches first)
   - Frontend router priority: 1 (lower - catches everything else)
   - This ensures `/api` paths always go to backend

### Middleware Applied

**Frontend (`web-chain@file`):**

- Gzip compression
- Security headers (XSS protection, CSP, etc.)

**Backend (`api-chain@file,cors-dev@file`):**

- Gzip compression
- Security headers
- Rate limiting (20 req/s)
- CORS (allows fitfolio.dev.rutabagel.com)

---

## Testing the Integration

### 1. Start FitFolio with Traefik

```bash
cd ~/projects/fitfolio
docker compose -f compose.dev.traefik.yml up -d
```

### 2. Check All Services Started

```bash
docker compose -f compose.dev.traefik.yml ps

# Expected output:
# fitfolio-backend    running (healthy)
# fitfolio-frontend   running
# fitfolio-db        running (healthy)
# fitfolio-redis     running (healthy)
# fitfolio-mail      running
```

### 3. Verify Traefik Sees the Services

Visit Traefik dashboard: https://traefik.dev.rutabagel.com

Look for these routers:

- `fitfolio-backend` (https, /api path)
- `fitfolio-frontend` (https, root path)

### 4. Test Frontend

```bash
curl -k https://fitfolio.dev.rutabagel.com/

# Or open in browser:
# https://fitfolio.dev.rutabagel.com
```

### 5. Test Backend API

```bash
curl -k https://fitfolio.dev.rutabagel.com/api/healthz

# Expected: {"status": "ok"} or similar
```

### 6. Test Frontend Calling Backend

The frontend should automatically call the backend via:

```javascript
// Frontend makes API call
fetch('/api/v1/workouts')  // Uses VITE_API_BASE_URL
→ https://fitfolio.dev.rutabagel.com/api/v1/workouts
→ Traefik routes to backend
```

---

## Troubleshooting

### Frontend Not Loading

```bash
# Check if frontend is running
docker logs fitfolio-frontend

# Check if Traefik sees it
curl -k -v https://fitfolio.dev.rutabagel.com/

# Look for "traefik.http.routers.fitfolio-frontend" in Traefik dashboard
```

### API Not Responding

```bash
# Check backend health
docker logs fitfolio-backend

# Test backend directly (inside container)
docker exec fitfolio-backend curl http://localhost:8000/healthz

# Test via Traefik
curl -k https://fitfolio.dev.rutabagel.com/api/healthz
```

### CORS Errors

If you see CORS errors in the browser console:

1. **Verify CORS middleware is applied:**

   ```bash
   docker inspect fitfolio-backend | grep cors-dev
   ```

2. **Check backend CORS configuration** in your FastAPI app:
   ```python
   # Should include fitfolio.dev.rutabagel.com in allowed origins
   app.add_middleware(
       CORSMiddleware,
       allow_origins=["https://fitfolio.dev.rutabagel.com"],
       allow_credentials=True,
       allow_methods=["*"],
       allow_headers=["*"],
   )
   ```

### Service Not in Traefik Dashboard

```bash
# Check if service has traefik.enable=true
docker inspect fitfolio-backend | grep traefik.enable

# Check if service is on traefik-public network
docker inspect fitfolio-backend | grep -A 10 Networks

# Check Traefik logs
cd ~/dev-infra/traefik
docker compose logs | grep -i fitfolio
```

### 503 Service Unavailable

This usually means the service isn't healthy or reachable:

```bash
# Check service health
docker ps | grep fitfolio

# Check backend is listening on port 8000
docker exec fitfolio-backend netstat -tlnp | grep 8000

# Check frontend is listening on port 5173
docker exec fitfolio-frontend netstat -tlnp | grep 5173
```

---

## Important Notes

### Certificate Warnings

You'll see "Your connection isn't private" warnings for local development. This is
**expected and safe**:

- Local domains can't get Let's Encrypt certificates
- Traefik uses self-signed certificates locally
- Click "Advanced" → "Proceed" to continue
- In production with real domains, warnings will disappear

### Hot Reload Still Works

Both frontend and backend hot reload still function:

- Frontend: Vite dev server detects file changes
- Backend: Uvicorn --reload detects code changes
- No need to rebuild containers for code changes

### Database Access

Database and Redis remain directly accessible for development:

```bash
# PostgreSQL
psql -h localhost -p 5432 -U ${POSTGRES_USER} -d ${POSTGRES_DB}

# Redis
redis-cli -h localhost -p 6379
```

---

## Migration Path

### Current State

- ✅ Original `compose.dev.yml` - Works as before
- ✅ New `compose.dev.traefik.yml` - Traefik integrated
- ✅ Both can coexist

### Recommended Next Steps

1. **Test with Traefik version:**

   ```bash
   docker compose -f compose.dev.traefik.yml up -d
   ```

2. **Verify everything works:**
   - Frontend loads
   - API calls succeed
   - No errors in console

3. **Once confident, switch default:**

   ```bash
   # Rename files (backup original)
   mv compose.dev.yml compose.dev.direct.yml
   mv compose.dev.traefik.yml compose.dev.yml
   ```

4. **Then use standard commands:**
   ```bash
   docker compose up -d  # Uses compose.dev.yml (Traefik version)
   ```

---

## Production Considerations

When deploying to production:

1. **Use `compose.prod.yml`** with similar Traefik labels
2. **Change domain** from `fitfolio.dev.rutabagel.com` to your production domain
3. **Update CORS** to allow production domain
4. **Remove debug ports** (PostgreSQL, Redis should not be exposed)
5. **Use production builds** (not dev servers)
6. **Set resource limits** on all services

---

## Summary

**What You Have:**

- ✅ Traefik-integrated compose file ready
- ✅ DNS configured (fitfolio.dev.rutabagel.com)
- ✅ Routing configured (frontend at /, backend at /api)
- ✅ Security middleware applied
- ✅ Original compose file preserved

**Next Step:**

```bash
cd ~/projects/fitfolio
docker compose -f compose.dev.traefik.yml up -d
```

**Access:**

```
https://fitfolio.dev.rutabagel.com
```

**Note:** Accept the certificate warning (expected for local dev).
