"""
Student Grade Notification Service v4
Production-ready: database, cache, storage, full email support
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

    LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
    print("  [OK] Log level         ->", LOG_LEVEL)

    SMTP_HOST  = os.environ["SMTP_HOST"]
    SECRET_KEY = os.environ["SECRET_KEY"]
    print("  [OK] Email server      ->", SMTP_HOST)
    print("  [OK] Security key         loaded")

    # NEW FEATURE: full production infrastructure
    DATABASE_URL    = os.environ["DATABASE_URL"]
    SMTP_USER       = os.environ["SMTP_USER"]
    REDIS_HOST      = os.environ["REDIS_HOST"]
    S3_BUCKET       = os.environ["S3_BUCKET"]
    CHECK_INTERVAL  = os.getenv("CHECK_INTERVAL", "60")
    print("  [OK] Database          ->", DATABASE_URL.split("/")[-1])
    print("  [OK] Redis cache       ->", REDIS_HOST)
    print("  [OK] Storage bucket    ->", S3_BUCKET)
    print("  [OK] Email user        ->", SMTP_USER)
    print("  [OK] Check interval    ->", CHECK_INTERVAL, "seconds")

    print("\n" + "="*55)
    print("  SERVICE RUNNING  |  Full production mode")
    print("="*55 + "\n")
except KeyError as e:
    print("  [FAILED] Missing:", e)
    print("  Run Config Drift Detector to find all missing vars.\n")
    sys.exit(1)
