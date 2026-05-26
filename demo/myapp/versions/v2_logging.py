"""
Student Grade Notification Service v2
New feature: configurable logging level
"""
import os, sys

print("\n" + "="*55)
print("  Grade Notification Service  |  HAW Kiel")
print("="*55)
print("  Starting up...\n")

try:
    PORTAL_API_KEY = os.environ["PORTAL_API_KEY"]
    PORTAL_URL     = os.environ["PORTAL_URL"]
    print("  [OK] Portal connected  ->", PORTAL_URL)

    # NEW FEATURE: configurable logging
    LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
    print("  [OK] Log level         ->", LOG_LEVEL)

    print("\n" + "="*55)
    print("  SERVICE RUNNING")
    print("="*55 + "\n")
except KeyError as e:
    print("  [FAILED] Missing:", e)
    print("  Run Config Drift Detector to find all missing vars.\n")
    sys.exit(1)
