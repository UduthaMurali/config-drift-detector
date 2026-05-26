"""Sample Python app — used as test fixture for the Python scanner."""
import os
from dotenv import load_dotenv

load_dotenv()

# Method 1: os.environ["KEY"]  — no default → CRITICAL if missing
database_url = os.environ["DATABASE_URL"]

# Method 2: os.getenv("KEY")  — no default → CRITICAL if missing
api_key = os.getenv("API_KEY")

# Method 3: os.environ.get("KEY", "default")  — has default → WARNING only
redis_host = os.environ.get("REDIS_HOST", "localhost")

# Method 4: os.getenv("KEY", "default")  — has default → WARNING only
log_level = os.getenv("LOG_LEVEL", "INFO")

# INTENTIONALLY MISSING from config: STRIPE_SECRET
stripe_secret = os.environ["STRIPE_SECRET"]
