#!/bin/bash
# Start the two local Cloudflare helpers used by the store downloaders.
# This is deliberately idempotent: an attempt reuses healthy services, and
# replaces only a service whose health check failed.
set -u

FLARE_IMAGE='ghcr.io/flaresolverr/flaresolverr@sha256:139dfee1c6f89249c8d665d1333a42e8ec74ec0a86bc6bb1c8461e10d3a66a47'
CFB_IMAGE='ghcr.io/sarperavci/cloudflarebypassforscraping@sha256:0e679c1c0f6ac3209d233c2b7e99737f39a137987171b5bf30b15ef53a01ce33'

healthy() {
  case "$1" in
    flaresolverr) curl -sS --max-time 3 http://localhost:8191/ >/dev/null 2>&1 ;;
    cloudflarebypass) curl -sS --max-time 3 http://localhost:8000/ >/dev/null 2>&1 ;;
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
  if ! docker run -d --name "$name" -p "$port:$port" "$image" >/dev/null; then
    echo "::warning::could not start $name; the corresponding store path may fail" >&2
    return 0
  fi
  # Preserve the prior action's warning-only behavior when a helper is slow or
  # unavailable; downloader and APK verification gates still decide the build.
  wait_healthy "$name" || true
}

ensure flaresolverr 8191 "$FLARE_IMAGE"
ensure cloudflarebypass 8000 "$CFB_IMAGE"
