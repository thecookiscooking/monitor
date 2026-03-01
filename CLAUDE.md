# Monitor — Cross-App Health Monitoring

Central monitoring hub using Uptime Kuma. Monitors all apps from a single dashboard.

## Quick Reference

| What | Where |
|------|-------|
| Uptime Kuma UI | `http://<VPS_IP>:3001` |
| Admin user | admin |
| VPS scripts | `/opt/monitor/scripts` (git clone of this repo) |
| Docker Compose | `/opt/monitor/docker-compose.yml` |

## Full Setup Playbook (from scratch)

### 1. Deploy Uptime Kuma on VPS

```bash
# SSH or Hetzner web console
mkdir -p /opt/monitor
cd /opt/monitor
nano docker-compose.yml
```

```yaml
services:
  uptime-kuma:
    image: louislam/uptime-kuma:1
    restart: unless-stopped
    ports:
      - "3001:3001"
    volumes:
      - uptime-kuma-data:/app/data
volumes:
  uptime-kuma-data:
```

```bash
docker compose up -d
```

### 2. Clone this repo on VPS

```bash
cd /opt/monitor
git clone https://github.com/thecookiscooking/monitor.git scripts
cd scripts
apt install python3-pip -y
pip3 install uptime-kuma-api --break-system-packages
```

### 3. Open Uptime Kuma UI, create admin account

Go to `http://<VPS_IP>:3001`, create admin account (username: `admin`).

### 4. Add env vars to the app (Coolify)

For each app being monitored, add test credentials as **runtime** env vars:

```
FWK_TEST_EMAIL=<test-account-email>
FWK_TEST_PASSWORD=<test-account-password>
```

**Important:** No quotes in Coolify UI. Coolify handles escaping. Quotes caused build failures.
**Important:** Variable names matter — `FWK_TEST_EMAIL` not `FKW_TEST_EMAIL`.

### 5. Run setup script

```bash
cd /opt/monitor/scripts
KUMA_PASS=<admin_password> python3 setup-monitors.py
```

### 6. Verify

All monitors should turn green within 5 minutes (except Journey Tests which needs CI).

## Updating Monitors

```bash
cd /opt/monitor/scripts
git pull
KUMA_PASS=<admin_password> python3 setup-monitors.py
```

Script is idempotent — skips monitors that already exist (matches by name).
To change an existing monitor: delete in UI first, then re-run script.

## Architecture

```
Uptime Kuma (port 3001)
  ├── FWK monitors (10)
  │     ├── Frontend (HTTPS ping, 5min)
  │     ├── API Health (GET /api/health, 2min)
  │     ├── Services Health (GET /api/health/services, keyword: "ok", 5min)
  │     ├── Auth Health (GET /api/health/auth, keyword: "ok", 15min)
  │     ├── SSL cert expiry (daily)
  │     ├── DNS resolution (hourly)
  │     ├── Programs exist (keyword check, hourly)
  │     ├── Exercises exist (keyword check, hourly)
  │     ├── Tips exist (keyword check, hourly)
  │     └── Journey Tests (Push monitor, pinged by CI, daily)
  └── Future apps (add to APPS dict in setup-monitors.py)
```

## Adding a New App

1. Build health endpoints in the app (see Health Endpoint Contract below)
2. Add test user + env vars in the app's hosting platform
3. Add entry to `APPS` dict in `setup-monitors.py`
4. Write a `get_<app>_monitors()` function (copy `get_fwk_monitors` as template)
5. Push, pull on VPS, re-run setup script

## Health Endpoint Contract

Every app should expose:
- `GET /api/health` — quick DB ping (for hosting platform liveness checks)
- `GET /api/health/services` — deep check of all external deps, returns:
  ```json
  {"status": "ok|degraded|down", "database": {}, "stripe": {}, ...}
  ```
- `GET /api/health/auth` — real login test using env var credentials, returns:
  ```json
  {"status": "ok"}
  ```

**Why GET for auth?** Uptime Kuma v1 can't send form-urlencoded POST bodies.
The endpoint does the login internally — credentials stay in Coolify, not in Kuma.
See `LEARNINGS.md` for the full story.

## Env Vars

### On VPS (for setup script)
| Var | Purpose |
|-----|---------|
| `KUMA_PASS` | Uptime Kuma admin password (required) |
| `KUMA_URL` | Uptime Kuma URL (default: http://localhost:3001) |
| `KUMA_USER` | Admin username (default: admin) |

### In Coolify (for each app)
| Var | Purpose |
|-----|---------|
| `FWK_TEST_EMAIL` | Test account email for auth health check |
| `FWK_TEST_PASSWORD` | Test account password for auth health check |

## Troubleshooting

| Symptom | Cause | Fix |
|---------|-------|-----|
| `status: skip` in Auth Health | Env vars not set or wrong names | Check Coolify: `FWK_TEST_EMAIL` (not `FKW_`) |
| `status: fail, reason: Test user not found` | Test account doesn't exist | Sign up at the app with the test email |
| `status: fail, reason: Password mismatch` | Wrong password in env var | Update `FWK_TEST_PASSWORD` in Coolify |
| Build fails with `command not found` | Special chars in env values | Remove quotes from Coolify UI values |
| `pip3 install` fails | Externally managed Python | Add `--break-system-packages` flag |
| Monitor says DOWN but endpoint works in browser | Keyword mismatch | Check exact keyword string matches response JSON |
