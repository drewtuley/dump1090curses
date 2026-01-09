#!/usr/bin/env bash
# Wait for a HTTP /health endpoint to return 200
# Usage:
#   ./wait-for-regserver-health.sh                # uses defaults
#   ./wait-for-regserver-health.sh -u URL -t 60 -i 2
#
# Exits 0 if healthy, 1 on timeout or other failure.

set -u
: "${WAIT_URL:=http://localhost:5001/health}"
: "${TIMEOUT:=60}"    # total seconds to wait before failing
: "${INTERVAL:=2}"    # seconds between attempts

print_help() {
  cat <<EOF
wait-for-regserver-health.sh - wait for an HTTP /health endpoint to return 200

Options:
  -u URL       Health URL (default: ${WAIT_URL})
  -t SECONDS   Timeout in seconds (default: ${TIMEOUT})
  -i SECONDS   Poll interval in seconds (default: ${INTERVAL})
  -h           Show this help
EOF
}

# parse args
while getopts "u:t:i:h" opt; do
  case $opt in
    u) WAIT_URL="$OPTARG" ;;
    t) TIMEOUT="$OPTARG" ;;
    i) INTERVAL="$OPTARG" ;;
    h) print_help; exit 0 ;;
    *) print_help; exit 2 ;;
  esac
done

echo "Waiting for health endpoint: ${WAIT_URL}"
echo "Timeout: ${TIMEOUT}s, Interval: ${INTERVAL}s"

start_ts=$(date +%s)
end_ts=$((start_ts + TIMEOUT))
attempt=0

check_once() {
  attempt=$((attempt + 1))
  # prefer curl if available
  if command -v curl >/dev/null 2>&1; then
    # -s silent, -S show error, -f fail non-2xx, -m timeout per request
    if curl -fsS --max-time "${INTERVAL}" "${WAIT_URL}" >/dev/null 2>&1; then
      return 0
    else
      return 1
    fi
  fi

  # fallback to python if curl not present
  if command -v python3 >/dev/null 2>&1; then
    python3 - <<PYCODE
import sys, urllib.request
try:
    resp = urllib.request.urlopen("${WAIT_URL}", timeout=${INTERVAL})
    if resp.getcode() == 200:
        sys.exit(0)
    else:
        sys.exit(1)
except Exception:
    sys.exit(1)
PYCODE
    return $?
  fi

  # if neither curl nor python available, fail
  echo "Error: neither curl nor python3 is available to check health" >&2
  return 2
}

while true; do
  now=$(date +%s)
  if check_once; then
    echo "✔ Health check passed (attempt ${attempt})"
    exit 0
  else
    echo "⟳ attempt ${attempt} failed, waiting ${INTERVAL}s..."
  fi

  if [ "$now" -ge "$end_ts" ]; then
    echo "✖ Timeout after ${TIMEOUT}s waiting for ${WAIT_URL}" >&2
    # show last few logs to help debugging (if docker is present and regserver container exists)
    if command -v docker >/dev/null 2>&1 && docker ps --filter "name=regserver" --format '{{.Names}}' | grep -q regserver; then
      echo "----- last 200 lines of container logs (regserver) -----"
      docker logs --tail 200 regserver || true
      echo "-------------------------------------------------------"
    fi
    exit 1
  fi

  sleep "${INTERVAL}"
done

