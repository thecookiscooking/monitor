"""
Replace the broken Login Flow monitor with Auth Health (GET-based).

Usage:
  KUMA_PASS=xxx python fix-login-monitor.py
"""

import sys
import os
from uptime_kuma_api import UptimeKumaApi, MonitorType

KUMA_URL = os.getenv("KUMA_URL", "http://localhost:3001")
KUMA_USER = os.getenv("KUMA_USER", "admin")
KUMA_PASS = os.getenv("KUMA_PASS", "")

if not KUMA_PASS:
    print("Set KUMA_PASS env var")
    sys.exit(1)

api = UptimeKumaApi(KUMA_URL)
api.login(KUMA_USER, KUMA_PASS)

# Delete old Login Flow monitor
monitors = api.get_monitors()
for m in monitors:
    if "Login" in m.get("name", ""):
        print(f"Deleting old monitor: {m['name']} (id={m['id']})")
        api.delete_monitor(m["id"])

# Create new Auth Health monitor (GET-based, no credentials needed)
result = api.add_monitor(
    name="FWK — Auth Health",
    type=MonitorType.KEYWORD,
    url="https://api.flatwhiteking.com/api/health/auth",
    interval=60,  # 60s for testing, change to 900 once confirmed
    maxretries=2,
    keyword='"status":"ok"',
)
print(f"Created: FWK — Auth Health (id={result['monitorID']})")
print("  Checks login with test credentials stored in Coolify env vars")
print("  interval = 60s (for testing, change to 900 once confirmed)")

api.disconnect()
print("\nDone! Add FWK_TEST_EMAIL + FWK_TEST_PASSWORD to Coolify env vars.")
