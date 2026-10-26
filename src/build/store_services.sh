#!/bin/bash
# Start the two local Cloudflare helpers used by the store downloaders.
# This is deliberately idempotent: an attempt reuses healthy services, and
# replaces only a service whose health check failed.
set -u

# W16o: F-08, keep helper APIs on loopback and provide an explicit job-exit cleanup.


FLARE_IMAGE='ghcr.io/flaresolverr/flaresolverr@sha256:c80ae007ce2ccdcd217a12426e4f039ef763ff90738c808d38810c3e59323767' # v3.5.2 ghcr.io/flaresolverr/flaresolverr@sha256:c80ae007ce2ccdcd217a12426e4f039ef763ff90738c808d38810c3e59323767
CFB_IMAGE='ghcr.io/sarperavci/cloudflarebypassforscraping@sha256:0e679c1c0f6ac3209d233c2b7e99737f39a137987171b5bf30b15ef53a01ce33'

healthy() {
  case "$1" in
    flaresolverr) curl -sS --max-time 3 http://127.0.0.1:8191/ >/dev/null 2>&1 ;;
    cloudflarebypass) curl -sS --max-time 3 http://127.0.0.1:8000/ >/dev/null 2>&1 ;;
    *) return 2 ;;
  esac
}

wait_healthy() {
  local name=$1 i
  for i in $(seq 1 30); do
    if healthy "$name"; then
      echo "[+] $name is ready (reused or started in this job)."
      return 0
    fi
    sleep 2
  done
  echo "::warning::$name did not start within 60 s; the corresponding store path may fail" >&2
  echo "- $name did not start; the corresponding store path may fail" >> "${GITHUB_STEP_SUMMARY:-/dev/null}"
  return 1
}

ensure() {
  local name=$1 port=$2 image=$3
  # The health check is the reuse gate. Never restart a healthy service.
  if healthy "$name"; then
    echo "[+] Reusing healthy $name on port $port."
    return 0
  fi

  echo "[*] Starting fresh $name on port $port after a failed health check..."
  docker rm -f "$name" >/dev/null 2>&1 || true
  if ! docker run -d --name "$name" -p "127.0.0.1:$port:$port" "$image" >/dev/null; then
    echo "::error::could not start $name; refusing store access" >&2
    docker rm -f "$name" >/dev/null 2>&1 || true
    return 1
  fi
  if ! wait_healthy "$name"; then
    echo "::error::$name failed its health check; refusing store access" >&2
    docker rm -f "$name" >/dev/null 2>&1 || true
    return 1
  fi
}

cleanup() {
  docker rm -f flaresolverr cloudflarebypass >/dev/null 2>&1 || true
}

if [ "${1:-}" = cleanup ]; then
  cleanup
  exit 0
fi
ensure flaresolverr 8191 "$FLARE_IMAGE" || exit 1
ensure cloudflarebypass 8000 "$CFB_IMAGE" || exit 1
