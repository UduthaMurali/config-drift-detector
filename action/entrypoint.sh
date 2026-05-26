#!/bin/bash
set -e

FAIL_ON_DRIFT=false
ARGS=()

# Parse --fail-on-drift out of args and track it
for arg in "$@"; do
    if [ "$arg" = "--fail-on-drift" ]; then
        FAIL_ON_DRIFT=true
    fi
    ARGS+=("$arg")
done

# Run detector with JSON output (to stdout), human report to stderr
python /app/main.py "${ARGS[@]}" --json > /tmp/drift_report.json 2>/tmp/drift_human.txt || true

# Print human-readable report to Actions log
cat /tmp/drift_human.txt

# Parse JSON for outputs
REPORT=$(cat /tmp/drift_report.json)
STATUS=$(echo "$REPORT" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('status','UNKNOWN'))")
MISSING=$(echo "$REPORT" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('summary',{}).get('missing',0))")

# Set GitHub Action outputs
if [ -n "$GITHUB_OUTPUT" ]; then
    echo "drift-detected=$([ "$STATUS" = "DRIFT_DETECTED" ] && echo true || echo false)" >> "$GITHUB_OUTPUT"
    echo "missing-count=$MISSING" >> "$GITHUB_OUTPUT"
    printf 'report-json=%s\n' "$REPORT" >> "$GITHUB_OUTPUT"
fi

# Fail if requested and drift detected
if [ "$FAIL_ON_DRIFT" = "true" ] && [ "$STATUS" = "DRIFT_DETECTED" ]; then
    echo "::error::Config drift detected — $MISSING variable(s) missing from deployment config."
    exit 1
fi

exit 0
