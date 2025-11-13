# ADR-0005: Redis Configuration and Access Patterns

**Status:** Accepted **Date:** 2025-11-06 **Author:** Development Team **Related:**
[ADR-0004: Opaque Server-Side Sessions](0004-opaque-server-side-sessions.md)

## Context

FitFolio uses Redis for ephemeral data storage including:

- Rate limiting state (sliding window counters)
- WebAuthn challenge storage (temporary cryptographic challenges)
- Session rotation management
- Magic link token storage

The application runs in multiple environments:

1. **Development**: Docker Compose with services on a shared network
2. **Testing**: Within a devcontainer accessing Docker Compose services
3. **Production**: Docker Compose on VPS with external Traefik

Different environments require different Redis connection strategies, which has caused
confusion and connectivity issues during development.

## Decision

### Redis Connection Strategy by Environment

We will use **Docker service name-based connections** across all environments,
leveraging Docker's built-in DNS resolution:

**Connection URL Format:**

```
redis://redis:6379/{db_number}
```

**Database Allocation:**

- `db=0` - Production data
- `db=1` - Test data (isolated from development)
- `db=2+` - Reserved for future use

### Environment-Specific Configuration

#### 1. Development (`compose.dev.yml`)

```yaml
services:
  redis:
    image: redis:7-alpine
    container_name: fitfolio-redis
    ports:
      - '6379:6379' # Exposed for external tools (RedisInsight, etc.)
    command:
      redis-server --maxmemory 256mb --maxmemory-policy allkeys-lru --appendonly yes
    networks:
      - default # Shared with backend/frontend
```

**Backend connection:** `redis://redis:6379/0` **Test connection:**
`redis://redis:6379/1`

#### 2. Testing (pytest in devcontainer)

**Location:** `backend/tests/conftest.py`

```python
# Use separate Redis database for tests to avoid conflicts with dev data
os.environ.setdefault("REDIS_URL", "redis://redis:6379/1")
```

**Why `redis` hostname works:**

- Devcontainer is configured to use `compose.dev.yml` as its Docker Compose file
- Backend service and Redis service share the same Docker network
- Docker's internal DNS resolves `redis` to the Redis container's IP

**Why NOT to use `localhost`:**

- `localhost` inside a devcontainer refers to the devcontainer itself, not the host
- Redis is running in a separate Docker container, not on the devcontainer's localhost
- Port forwarding (6379:6379) only makes Redis accessible from the **host** machine, not
  from other containers

#### 3. Production (`compose.prod.yml`)

**Architecture:** Single shared Redis instance serving multiple applications on the same
Docker network.

```yaml
services:
  redis:
    image: redis:7-alpine
    container_name: fitfolio-redis-prod
    # NO external port mapping (security best practice)
    command:
      redis-server --maxmemory 512mb --maxmemory-policy allkeys-lru --appendonly yes
    volumes:
      - redis-prod-data:/data # Persistent storage for AOF
    networks:
      - default # Shared network with backend, other apps
    restart: unless-stopped
```

**Backend connection:** `redis://redis:6379/0`

**Multi-Application Support:**

- `db=0` - FitFolio production data
- `db=1` - Reserved for future FitFolio features
- `db=2+` - Available for other applications on the same VPS

**Why a shared Redis instance:**

1. **Resource efficiency** - Single Redis process for multiple apps
2. **Simplified management** - One Redis instance to monitor/backup
3. **Cost effective** - No need for separate Redis containers per app
4. **Same network** - All apps can connect via `redis://redis:6379/{db}`
5. **Data isolation** - Different database numbers keep data separate

### Connection Testing

To verify Redis connectivity from the devcontainer:

```bash
# Python socket test
python -c "import socket; sock = socket.socket(); result = sock.connect_ex(('redis', 6379)); print('Redis:', 'OPEN' if result == 0 else 'CLOSED'); sock.close()"

# Application-level test
python -c "import asyncio; from app.core.redis_client import get_redis; asyncio.run((await get_redis()).ping()); print('Redis connected!')"

# Run a single test
pytest tests/test_deps.py::test_get_current_session_no_token -v
```

## Consequences

### Positive

1. **Consistent across environments** - Same `redis://redis:6379` pattern everywhere
2. **Docker-native** - Leverages Docker's service discovery
3. **Isolated test data** - Tests use db=1, development uses db=0
4. **No port conflicts** - Multiple instances can run without port collisions
5. **Secure by default** - Production Redis not exposed externally

### Negative

1. **Local debugging complexity** - Cannot connect to Redis from host machine using
   localhost
   - **Mitigation**: Use port forwarding (6379:6379) in dev only, connect via
     `localhost` from **host** tools
2. **Requires Docker networking knowledge** - Developers must understand container DNS
   - **Mitigation**: This ADR documents the behavior

### Neutral

1. **External tool access** - Tools like RedisInsight need Docker-specific connection
   - Use `localhost:6379` when running tools on **host machine**
   - Use `redis:6379` when running tools **inside containers**

## Implementation Details

### Environment Variable Precedence

```python
# 1. Explicit test configuration (highest priority)
os.environ.setdefault("REDIS_URL", "redis://redis:6379/1")  # conftest.py

# 2. Docker Compose environment variables
REDIS_URL=redis://redis:6379/0  # compose.dev.yml, compose.prod.yml

# 3. Application defaults (lowest priority)
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")  # app code
```

### Redis Client Configuration

**File:** `app/core/redis_client.py`

```python
async def get_redis() -> redis.Redis:
    """Get Redis client instance (singleton pattern)."""
    global _redis_client

    if _redis_client is None:
        redis_url = os.getenv("REDIS_URL", "redis://localhost:6379/0")
        _redis_client = redis.from_url(
            redis_url,
            encoding="utf-8",
            decode_responses=True,
            socket_keepalive=True,
            socket_connect_timeout=5,
            retry_on_timeout=True,
            health_check_interval=30,
        )

    return _redis_client
```

### Test Isolation

**File:** `backend/tests/conftest.py`

```python
@pytest_asyncio.fixture(scope="function", autouse=True)
async def cleanup_redis():
    """Flush Redis database before each test to prevent state leakage."""
    from app.core.redis_client import get_redis

    # Flush Redis before test to start clean
    try:
        redis = await get_redis()
        await redis.flushdb()  # Clear all keys in current database (db=1 for tests)
    except Exception:
        pass  # Ignore if Redis is not available

    yield
    # No cleanup after - let Redis connection persist across tests for performance
```

## Troubleshooting

### "Connection refused" errors in tests

**Symptoms:**

```
redis.exceptions.ConnectionError: Error ... connecting to localhost:6379
```

**Cause:** Test configuration using `localhost` instead of `redis` hostname

**Fix:** Update `backend/tests/conftest.py`:

```python
os.environ.setdefault("REDIS_URL", "redis://redis:6379/1")
```

### "Cannot connect to Docker daemon" errors

**Symptoms:**

```
Cannot connect to the Docker daemon at unix:///var/run/docker.sock
```

**Cause:** This is expected - the devcontainer cannot manage Docker
(Docker-outside-of-Docker)

**Not a problem:** Redis is still accessible via the `redis` hostname on the Docker
network

### Redis not accessible from host machine tools

**Symptoms:** RedisInsight or redis-cli on host cannot connect to `localhost:6379`

**Solution:**

1. Ensure port mapping exists in `compose.dev.yml`: `- "6379:6379"`
2. Connect to `localhost:6379` from host machine
3. Connect to `redis:6379` from inside containers

## References

- Docker Compose networking: https://docs.docker.com/compose/networking/
- Redis connection pooling: https://redis.io/docs/connect/clients/python/
- pytest fixtures: https://docs.pytest.org/en/stable/reference/fixtures.html
- ADR-0004: Opaque Server-Side Sessions (Redis session storage decision)

## Alternatives Considered

### Alternative 1: Use `localhost` everywhere

**Rejected because:**

- Doesn't work inside devcontainer (localhost is the container, not the Redis container)
- Requires different configuration per environment
- Breaks Docker Compose service discovery

### Alternative 2: Use `host.docker.internal`

**Rejected because:**

- Only works on Docker Desktop (Mac/Windows), not Linux
- Adds unnecessary complexity
- Doesn't work in all devcontainer configurations

### Alternative 3: Dynamic hostname resolution

**Rejected because:**

- Overcomplicates a simple problem
- Docker service discovery already solves this
- Adds runtime overhead

## Future Considerations

1. **Redis Sentinel** - If we need high availability, use Redis Sentinel with service
   discovery
2. **Redis Cluster** - If we need horizontal scaling, multiple `redis-node-{n}` services
3. **External Redis** - If moving to managed Redis (AWS ElastiCache, etc.), update
   connection URLs accordingly
4. **TLS connections** - If adding encryption, use `rediss://` scheme with TLS
   configuration

---

**Last Updated:** 2025-11-06 **Next Review:** When adding new environments or Redis use
cases
