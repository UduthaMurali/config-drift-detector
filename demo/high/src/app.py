import os

DB_URL       = os.environ["DATABASE_URL"]       # in config - OK
API_KEY      = os.environ["API_KEY"]            # in config - OK
REDIS_HOST   = os.environ["REDIS_HOST"]         # in config - OK

# MISSING - critical
SECRET_KEY   = os.environ["SECRET_KEY"]
JWT_SECRET   = os.environ["JWT_SECRET"]
SMTP_HOST    = os.environ["SMTP_HOST"]
SMTP_USER    = os.environ["SMTP_USER"]
SMTP_PASS    = os.environ["SMTP_PASSWORD"]
S3_BUCKET    = os.environ["S3_BUCKET"]
S3_KEY       = os.environ["AWS_ACCESS_KEY_ID"]
S3_SECRET    = os.environ["AWS_SECRET_ACCESS_KEY"]
STRIPE_KEY   = os.environ["STRIPE_SECRET_KEY"]

# MISSING - warning (has defaults)
LOG_LEVEL    = os.getenv("LOG_LEVEL", "INFO")
TIMEOUT      = os.getenv("REQUEST_TIMEOUT", "30")
