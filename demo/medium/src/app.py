import os

# These are in config - OK
DB_URL      = os.environ["DATABASE_URL"]
API_KEY     = os.environ["API_KEY"]
REDIS_HOST  = os.environ["REDIS_HOST"]
SMTP_PORT   = os.environ["SMTP_PORT"]
S3_BUCKET   = os.environ["S3_BUCKET"]
TIMEOUT     = os.getenv("REQUEST_TIMEOUT", "30")

# These are MISSING from config
SECRET_KEY  = os.environ["SECRET_KEY"]          # critical - no default
JWT_SECRET  = os.environ["JWT_SECRET"]          # critical - no default
RETRY_COUNT = os.getenv("RETRY_COUNT", "3")     # warning  - has default
