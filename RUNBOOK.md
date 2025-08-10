## Start / Stop

- Start all services: `make up`
- Stop all services: `make down`
- See container status: `make ps`
- Tail logs (all): `make logs`
- Tail logs (backend): `make be-logs`
- Tail logs (frontend): `make fe-logs`

## Health Checks

- Backend health: `make health` (or `curl http://localhost:8080/healthz`)
- Frontend dev server: open `http://localhost:5173`

## Dev Email (Mailpit)

- UI: `http://localhost:8025`
- Send test email: `make mail-verify` (uses `/_debug/mail?to=...`)

## Frontend ↔ Backend (dev)

- Vite proxies `/api/*` to backend on `http://localhost:8080`, stripping `/api`.
- Example call from the UI: `fetch('/api/healthz') -> {"status":"ok"}`
