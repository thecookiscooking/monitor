# Monitor Setup — Learnings

## Uptime Kuma v1 vs v2

| Feature | v1 (current) | v2 (beta) |
|---------|-------------|-----------|
| HTTP GET/POST | Yes | Yes |
| Body encoding: JSON | Yes | Yes |
| Body encoding: XML | Yes | Yes |
| Body encoding: form-urlencoded | **No** | Yes (PR #3499) |

**Lesson:** Don't rely on Uptime Kuma v1 for POST requests with form-urlencoded bodies. The `httpBodyEncoding="form"` value is silently ignored — it always sends as JSON.

## Auth Monitoring Pattern

**Problem:** Login endpoints (like FastAPI's `OAuth2PasswordRequestForm`) require `application/x-www-form-urlencoded` POST. Uptime Kuma v1 can't send that.

**Solution:** Create a dedicated `GET /api/health/auth` endpoint that:
1. Reads test credentials from server env vars (`FWK_TEST_EMAIL`, `FWK_TEST_PASSWORD`)
2. Does a real login internally (DB lookup + password verification)
3. Returns `{"status": "ok"}` or `{"status": "fail"}`
4. Uptime Kuma uses KEYWORD monitor checking for `"status":"ok"`

**Why this is better:**
- Credentials live in Coolify (proper secret management), not in Uptime Kuma's config
- No form encoding issues — it's a simple GET
- Tests the full auth pipeline: DB connection + user lookup + bcrypt verification
- Works with any monitoring tool, not just Uptime Kuma

## VPS / Hetzner Web Console Gotchas

1. **Special characters get mangled** — `>`, `>>`, quotes, pipes don't work reliably. Use `nano` for file creation instead of `echo >>`.
2. **YAML is indent-sensitive** — One wrong space breaks everything. Double-check in nano.
3. **`pip3 install` blocked on modern Ubuntu** — Use `--break-system-packages` flag or create a venv.
4. **`docker compose` (no hyphen)** — Newer Docker uses `docker compose`, not `docker-compose`.
5. **Paste into web console** — Ctrl+Shift+V (not Ctrl+V).
6. **SSH may be disabled** — Coolify setups often use key-only SSH. The Hetzner web console always works.

## Git Clone on VPS for Script Management

Instead of typing scripts into nano on the VPS, push to GitHub and `git clone`:
1. Push `monitor/` repo to GitHub (public, since no secrets in code)
2. `git clone` on VPS into `/opt/monitor/scripts`
3. Future changes: `git pull` + re-run
4. Credentials passed as env vars, never committed

## URL Encoding in Form Data

In `application/x-www-form-urlencoded`:
- `+` means **space** (not literal plus)
- Literal `+` must be encoded as `%2B`
- `@` is safe (doesn't need encoding in values)
- Python's `urllib.parse.quote(value, safe='')` handles this correctly
