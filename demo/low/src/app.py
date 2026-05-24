import os

# All variables except LOG_LEVEL are in config
DB_URL   = os.environ["DATABASE_URL"]
API_KEY  = os.environ["API_KEY"]
PORT     = os.getenv("PORT", "8080")          # has default
LOG_LVL  = os.getenv("LOG_LEVEL", "INFO")     # has default — MISSING from config but has default => warning
