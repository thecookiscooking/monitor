"""
Auto-configure Uptime Kuma monitors for all apps.

Usage:
  pip install uptime-kuma-api
  python setup-monitors.py

First run: creates admin account + all monitors.
Re-run safe: skips monitors that already exist (matches by name).
"""

import sys
import os
from uptime_kuma_api import UptimeKumaApi, MonitorType

# --- Config ---
KUMA_URL = os.getenv("KUMA_URL", "http://localhost:3001")
KUMA_USER = os.getenv("KUMA_USER", "admin")
KUMA_PASS = os.getenv("KUMA_PASS", "")

# All apps to monitor. Add new apps here as you build them.
APPS = {
    "fwk": {
        "frontend_url": "https://flatwhiteking.com",
        "api_url": "https://api.flatwhiteking.com",
    },
    # "app2": {
    #     "frontend_url": "https://app2.example.com",
    #     "api_url": "https://api.app2.example.com",
    # },
}


def get_fwk_monitors(app):
    """FWK-specific monitors."""
    api = app["api_url"]
    frontend = app["frontend_url"]

    return [
        # --- Infrastructure ---
        {
            "name": "FWK — Frontend",
            "type": MonitorType.HTTP,
            "url": frontend,
            "interval": 300,  # 5 min
            "maxretries": 2,
        },
        {
            "name": "FWK — API Health",
            "type": MonitorType.HTTP,
            "url": f"{api}/api/health",
            "interval": 120,  # 2 min (lightweight)
            "maxretries": 2,
        },
        {
            "name": "FWK — Services Health",
            "type": MonitorType.KEYWORD,
            "url": f"{api}/api/health/services",
            "interval": 300,
            "maxretries": 1,
            "keyword": '"status":"ok"',
        },
        # --- SSL & DNS ---
        {
            "name": "FWK — SSL Certificate",
            "type": MonitorType.HTTP,
            "url": frontend,
            "interval": 86400,  # daily
            "maxretries": 1,
            "expiryNotification": True,
        },
        {
            "name": "FWK — DNS",
            "type": MonitorType.DNS,
            "hostname": "flatwhiteking.com",
            "dns_resolve_server": "1.1.1.1",
            "interval": 3600,  # hourly
        },
        # --- Content integrity ---
        {
            "name": "FWK — Programs exist",
            "type": MonitorType.KEYWORD,
            "url": f"{api}/api/content/programs",
            "interval": 3600,
            "keyword": '"id"',
        },
        {
            "name": "FWK — Exercises exist",
            "type": MonitorType.KEYWORD,
            "url": f"{api}/api/content/exercises",
            "interval": 3600,
            "keyword": '"id"',
        },
        {
            "name": "FWK — Tips exist",
            "type": MonitorType.KEYWORD,
            "url": f"{api}/api/content/tips",
            "interval": 3600,
            "keyword": '"content"',
        },
        # --- Auth flow (real login test via GET — credentials live in Coolify env) ---
        {
            "name": "FWK — Auth Health",
            "type": MonitorType.KEYWORD,
            "url": f"{api}/api/health/auth",
            "interval": 900,  # 15 min
            "maxretries": 2,
            "keyword": '"status":"ok"',
        },
        # --- Push monitor for journey tests (nightly CI pings this) ---
        {
            "name": "FWK — Journey Tests",
            "type": MonitorType.PUSH,
            "interval": 86400,  # expect a ping every 24h
            "maxretries": 0,
        },
    ]


def main():
    if not KUMA_PASS:
        print("Set KUMA_PASS env var (your Uptime Kuma admin password)")
        print("  KUMA_PASS=yourpass python setup-monitors.py")
        sys.exit(1)

    api = UptimeKumaApi(KUMA_URL)

    # Login (or create first admin account)
    try:
        api.login(KUMA_USER, KUMA_PASS)
        print(f"Logged in as {KUMA_USER}")
    except Exception:
        try:
            api.setup(KUMA_USER, KUMA_PASS)
            api.login(KUMA_USER, KUMA_PASS)
            print(f"Created admin account: {KUMA_USER}")
        except Exception as e:
            print(f"Login failed: {e}")
            sys.exit(1)

    # Get existing monitors to avoid duplicates
    existing = {m["name"] for m in api.get_monitors()}
    created = 0
    skipped = 0

    for app_name, app_config in APPS.items():
        # Get monitors for this app
        if app_name == "fwk":
            monitors = get_fwk_monitors(app_config)
        else:
            # Generic monitors for future apps (just frontend + API health)
            monitors = [
                {
                    "name": f"{app_name.upper()} — Frontend",
                    "type": MonitorType.HTTP,
                    "url": app_config["frontend_url"],
                    "interval": 300,
                    "maxretries": 2,
                },
                {
                    "name": f"{app_name.upper()} — API Health",
                    "type": MonitorType.HTTP,
                    "url": f"{app_config['api_url']}/api/health",
                    "interval": 300,
                    "maxretries": 2,
                },
            ]

        for monitor in monitors:
            if monitor["name"] in existing:
                print(f"  skip  {monitor['name']} (exists)")
                skipped += 1
                continue

            try:
                result = api.add_monitor(**monitor)
                print(f"  +     {monitor['name']}")
                created += 1
            except Exception as e:
                print(f"  FAIL  {monitor['name']}: {e}")

    print(f"\nDone: {created} created, {skipped} skipped")

    # Print push monitor token for CI setup
    monitors = api.get_monitors()
    for m in monitors:
        if m.get("type") == MonitorType.PUSH:
            push_url = f"{KUMA_URL}/api/push/{m.get('pushToken', '???')}?status=up&msg=OK"
            print(f"\nPush URL for '{m['name']}':")
            print(f"  {push_url}")
            print("  (Ping this from CI after journey tests pass)")

    api.disconnect()


if __name__ == "__main__":
    main()
