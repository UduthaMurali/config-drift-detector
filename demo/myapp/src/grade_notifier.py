"""
Student Grade Notification Service v1
Basic version - connects to HAW grade portal
"""
import os, sys

print("\n" + "="*55)
print("  Grade Notification Service  |  HAW Kiel")
print("="*55)
print("  Starting up...\n")

# --- Drift introduced: LOW severity (has defaults, WARNING) ---
LOG_LEVEL          = os.getenv("LOG_LEVEL", "INFO")
NOTIFICATION_EMAIL = os.getenv("NOTIFICATION_EMAIL", "admin@haw-kiel.de")

# --- Drift introduced: CRITICAL severity (no defaults, app will crash) ---
SMTP_PASSWORD = os.environ["SMTP_PASSWORD"]
DATABASE_URL  = os.environ["DATABASE_URL"]

try:
    PORTAL_API_KEY = os.environ["PORTAL_API_KEY"]
    PORTAL_URL     = os.environ["PORTAL_URL"]
    print("  [OK] Portal connected ->", PORTAL_URL)
    print("  [OK] Log level:", LOG_LEVEL)
    print("  [OK] Notify:", NOTIFICATION_EMAIL)
    print("  [OK] DB:", DATABASE_URL)
    print("\n" + "="*55)
    print("  SERVICE RUNNING")
    print("="*55 + "\n")
except KeyError as e:
    print("  [FAILED] Missing:", e)
    print("  Run Config Drift Detector to find all missing vars.\n")
    sys.exit(1)
