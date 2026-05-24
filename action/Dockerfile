FROM python:3.11-slim

LABEL maintainer="HAW Kiel Release Engineering"
LABEL description="Config Drift Detector — Java/Python/C++ code-to-config drift detection"

# Install Java (for Java scanner)
RUN apt-get update && apt-get install -y --no-install-recommends \
    openjdk-17-jre-headless \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy project
COPY . .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Make entrypoint executable
RUN chmod +x action/entrypoint.sh

ENTRYPOINT ["/app/action/entrypoint.sh"]
