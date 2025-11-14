# CSRF Protection - Frontend Integration Guide

## Overview

The backend implements CSRF protection using the **double-submit cookie pattern**. This
document explains how the frontend should integrate with this security feature.

## How It Works

1. **Backend** sets a CSRF token in two places:
   - Cookie: `csrf_token` (HttpOnly=**false**, so JavaScript CAN read it)
   - Response header: `x-csrf-token`

2. **Frontend** must:
   - Read the token from the cookie
   - Send it back in the `X-CSRF-Token` header for all state-changing requests (POST,
     PUT, DELETE, PATCH)

3. **Backend** validates:
   - Token in cookie matches token in header
   - Requests without matching tokens are rejected with 403 Forbidden

## Protected Endpoints

All POST/PUT/DELETE/PATCH endpoints require CSRF tokens, **except**:

- `POST /auth/magic-link/start` - No session exists yet
- `POST /auth/magic-link/verify` - Token in body provides protection
- `GET` requests - Safe methods don't need protection
- `/_debug/*` - Development endpoints

## Frontend Implementation

### Vanilla JavaScript

```javascript
/**
 * Read CSRF token from cookie
 */
function getCsrfToken() {
  const match = document.cookie.match(/csrf_token=([^;]+)/);
  return match ? match[1] : null;
}

/**
 * Make authenticated request with CSRF protection
 */
async function authenticatedFetch(url, options = {}) {
  const csrfToken = getCsrfToken();

  if (
    !csrfToken &&
    ['POST', 'PUT', 'DELETE', 'PATCH'].includes(options.method?.toUpperCase())
  ) {
    throw new Error('CSRF token not found. Please refresh the page.');
  }

  return fetch(url, {
    ...options,
    headers: {
      ...options.headers,
      'X-CSRF-Token': csrfToken,
    },
    credentials: 'include', // IMPORTANT: Sends cookies
  });
}

// Usage example
await authenticatedFetch('/auth/webauthn/register/start', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({ email: 'user@example.com' }),
});
```

### React with Fetch

```javascript
import { useEffect, useState } from 'react';

function getCsrfToken() {
  const match = document.cookie.match(/csrf_token=([^;]+)/);
  return match ? match[1] : null;
}

function useApi() {
  const [csrfToken, setCsrfToken] = useState(getCsrfToken());

  useEffect(() => {
    // Refresh token from cookie on mount
    setCsrfToken(getCsrfToken());
  }, []);

  const apiCall = async (url, options = {}) => {
    const token = getCsrfToken(); // Get fresh token

    return fetch(url, {
      ...options,
      headers: {
        ...options.headers,
        'X-CSRF-Token': token,
      },
      credentials: 'include',
    });
  };

  return { apiCall, csrfToken };
}

// Usage in component
function RegisterForm() {
  const { apiCall } = useApi();

  const handleSubmit = async (email) => {
    const response = await apiCall('/auth/webauthn/register/start', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ email }),
    });

    if (!response.ok) {
      const error = await response.json();
      throw new Error(error.detail);
    }

    return response.json();
  };

  return (/* your form JSX */);
}
```

### Axios Interceptor

```javascript
import axios from 'axios';

// Configure axios instance
const api = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL || 'http://localhost:8080',
  withCredentials: true, // IMPORTANT: Sends cookies
});

// Add CSRF token to all requests
api.interceptors.request.use((config) => {
  if (['post', 'put', 'delete', 'patch'].includes(config.method.toLowerCase())) {
    const match = document.cookie.match(/csrf_token=([^;]+)/);
    const csrfToken = match ? match[1] : null;

    if (csrfToken) {
      config.headers['X-CSRF-Token'] = csrfToken;
    }
  }
  return config;
});

// Handle CSRF errors
api.interceptors.response.use(
  (response) => response,
  (error) => {
    if (
      error.response?.status === 403 &&
      error.response?.data?.detail?.includes('CSRF')
    ) {
      // CSRF token expired or invalid - refresh the page
      console.error('CSRF token invalid. Please refresh the page.');
      // Optionally: window.location.reload();
    }
    return Promise.reject(error);
  }
);

// Usage
await api.post('/auth/webauthn/register/start', { email: 'user@example.com' });
```

### TanStack Query (React Query)

```javascript
import { QueryClient, QueryClientProvider, useMutation } from '@tanstack/react-query';

function getCsrfToken() {
  const match = document.cookie.match(/csrf_token=([^;]+)/);
  return match ? match[1] : null;
}

async function apiPost(url, data) {
  const csrfToken = getCsrfToken();

  const response = await fetch(url, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'X-CSRF-Token': csrfToken,
    },
    credentials: 'include',
    body: JSON.stringify(data),
  });

  if (!response.ok) {
    const error = await response.json();
    throw new Error(error.detail || 'Request failed');
  }

  return response.json();
}

// Usage in component
function RegisterForm() {
  const registerMutation = useMutation({
    mutationFn: (email) => apiPost('/auth/webauthn/register/start', { email }),
    onError: (error) => {
      if (error.message.includes('CSRF')) {
        alert('Session expired. Please refresh the page.');
      }
    },
  });

  const handleSubmit = (email) => {
    registerMutation.mutate(email);
  };

  return (/* your form JSX */);
}
```

## Error Handling

### Possible CSRF Errors

1. **"CSRF token missing"** (403)
   - Token cookie not present or header not sent
   - **Solution:** Ensure cookies are enabled and `credentials: 'include'` is set

2. **"CSRF token invalid"** (403)
   - Token in cookie doesn't match token in header
   - **Solution:** Refresh the page to get a new token

### Recommended Error Handling

```javascript
try {
  const response = await authenticatedFetch('/api/endpoint', { method: 'POST', ... });
  // Handle success
} catch (error) {
  if (error.response?.status === 403) {
    const message = error.response.data?.detail || '';
    if (message.includes('CSRF')) {
      // CSRF error - ask user to refresh
      alert('Your session has expired. Please refresh the page and try again.');
      // Optionally auto-refresh: window.location.reload();
    }
  }
  // Handle other errors
}
```

## Testing

### Manual Testing with curl

```bash
# 1. Get CSRF token
TOKEN=$(curl -s http://localhost:8080/healthz -D - | grep "^x-csrf-token:" | awk '{print $2}' | tr -d '\r')

# 2. Use token in request
curl -X POST http://localhost:8080/auth/webauthn/register/start \
  -H "Content-Type: application/json" \
  -H "X-CSRF-Token: $TOKEN" \
  -H "Cookie: csrf_token=$TOKEN" \
  -d '{"email": "test@example.com"}'
```

### Browser DevTools Testing

1. Open DevTools Console
2. Check for CSRF token:
   ```javascript
   document.cookie.match(/csrf_token=([^;]+)/)?.[1];
   ```
3. Make a test request:

   ```javascript
   const token = document.cookie.match(/csrf_token=([^;]+)/)?.[1];

   fetch('/auth/webauthn/register/start', {
     method: 'POST',
     headers: {
       'Content-Type': 'application/json',
       'X-CSRF-Token': token,
     },
     credentials: 'include',
     body: JSON.stringify({ email: 'test@example.com' }),
   })
     .then((r) => r.json())
     .then(console.log);
   ```

## Security Considerations

### Do's

✅ **Do** include `credentials: 'include'` in fetch requests ✅ **Do** read the token
fresh from the cookie each time ✅ **Do** handle 403 CSRF errors gracefully ✅ **Do**
use HTTPS in production (set `CSRF_COOKIE_SECURE=true`)

### Don'ts

❌ **Don't** cache the CSRF token in state/localStorage ❌ **Don't** send requests
without the token ❌ **Don't** expose the token in URLs or GET parameters ❌ **Don't**
disable CSRF protection for convenience

## Troubleshooting

### Token not found in cookie

**Problem:** `document.cookie` doesn't show `csrf_token`

**Solutions:**

- Make sure you've made at least one GET request to the backend
- Check that cookies are enabled in the browser
- Verify the backend is setting the cookie (check Network tab → Response Headers)
- Ensure the frontend and backend are on the same domain (or CORS is configured
  correctly)

### CORS errors

**Problem:** Request blocked by CORS policy

**Solutions:**

- Verify `CORS_ORIGINS` in backend `.env` includes your frontend URL
- Ensure `credentials: 'include'` is set in fetch options
- Check that backend CORS middleware allows credentials

### Token mismatch errors

**Problem:** Getting "CSRF token invalid" despite sending token

**Solutions:**

- Ensure the same token is in both cookie and header
- Don't manually modify the token value
- Check for trailing whitespace in token
- Verify constant-time comparison is working (backend logs)

## Configuration

### Backend Environment Variables

```bash
# .env
CSRF_COOKIE_SECURE=false  # Set to true in production with HTTPS
```

### Exempt Paths

Edit `backend/app/middleware/csrf.py` to add paths that don't require CSRF:

```python
EXEMPT_PATHS = {
    "/auth/magic-link/start",
    "/auth/magic-link/verify",
    "/_debug/",
    "/healthz",
    # Add more exempt paths here
}
```

## Additional Resources

- [OWASP CSRF Prevention Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/Cross-Site_Request_Forgery_Prevention_Cheat_Sheet.html)
- [Double Submit Cookie Pattern](https://cheatsheetseries.owasp.org/cheatsheets/Cross-Site_Request_Forgery_Prevention_Cheat_Sheet.html#double-submit-cookie)
- [MDN: Using Fetch](https://developer.mozilla.org/en-US/docs/Web/API/Fetch_API/Using_Fetch)
- [MDN: Document.cookie](https://developer.mozilla.org/en-US/docs/Web/API/Document/cookie)

---

**Last Updated:** 2025-10-27 **Backend CSRF Implementation:**
`backend/app/middleware/csrf.py`
