#!/bin/bash
# Fail-closed minSdk gate: an unreadable SDK is not a pass.
# Tries four readers. Never hides why a read failed.
APK="${1:?apk path}"; CEIL="${2:-29}"
MIN=""
SDK="${ANDROID_HOME:-/usr/local/lib/android/sdk}"
READER="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)/sdk_metadata.py"
[[ "$CEIL" =~ ^[1-9][0-9]{0,8}$ ]] || { echo "::error::invalid SDK ceiling"; exit 1; }
ERR=$(mktemp) || exit 1
OUT=$(mktemp) || { rm -f "$ERR"; exit 1; }
trap 'rm -f "$ERR" "$OUT"' EXIT

# Only parse stdout from successful readers. Absent metadata permits a fallback;
# a present but malformed/duplicate declaration is a hard stop.
read_sdk() {
  local rc
  MIN=$(python3 "$READER" "$1" "$OUT")
  rc=$?
  if [ "$rc" -eq 2 ]; then
    MIN=""
  elif [ "$rc" -ne 0 ]; then
    echo "::error::minimum SDK reader refused metadata"
    exit 1
  fi
}

AAPT=$(find "$SDK" -name aapt2 -type f 2>/dev/null | sort -V | tail -1)

# 1. aapt2 badging
if [ -n "$AAPT" ]; then
  echo "[i] aapt2: $AAPT"
  if "$AAPT" dump badging "$APK" >"$OUT" 2>"$ERR"; then
    read_sdk badging
  else
    echo "[i] badging reader exited unsuccessfully; stdout ignored"
  fi
  if [ -z "$MIN" ] && [ -s "$ERR" ]; then
    echo "[i] badging failed:"; head -3 "$ERR" | sed 's/^/    /'
  fi
else
  echo "[i] no aapt2 under $SDK"
fi

# 2. aapt2 xmltree, tolerant of unknown API levels
if [ -z "$MIN" ] && [ -n "$AAPT" ]; then
  if "$AAPT" dump xmltree "$APK" --file AndroidManifest.xml >"$OUT" 2>"$ERR"; then
    read_sdk xmltree
    [ -n "$MIN" ] && echo "[i] read via xmltree"
  else
    echo "[i] xmltree reader exited unsuccessfully; stdout ignored"
  fi
fi

# 3. apkanalyzer
if [ -z "$MIN" ]; then
  AK=$(find "$SDK" -name apkanalyzer -type f 2>/dev/null | sort -V | tail -1)
  if [ -n "$AK" ]; then
    if "$AK" manifest min-sdk "$APK" >"$OUT" 2>"$ERR"; then
      read_sdk scalar
      [ -n "$MIN" ] && echo "[i] read via apkanalyzer"
    else
      echo "[i] apkanalyzer reader exited unsuccessfully; stdout ignored"
    fi
  fi
fi

# 4. pyaxmlparser
if [ -z "$MIN" ]; then
  if python3 -c 'import pyaxmlparser' 2>/dev/null || pip install -q pyaxmlparser 2>/dev/null; then
    if python3 -c "
import sys
from pyaxmlparser import APK
print(APK(sys.argv[1]).get_min_sdk_version() or '')
" "$APK" >"$OUT" 2>"$ERR"; then
      read_sdk scalar
      [ -n "$MIN" ] && echo "[i] read via pyaxmlparser"
    else
      echo "[i] pyaxmlparser reader exited unsuccessfully; stdout ignored"
    fi
  fi
fi

if [ -z "$MIN" ]; then
  echo "::error::UNVERIFIED - all four readers failed, minSdk unknown for $(basename "$APK")"
  exit 1
fi

echo "minSdkVersion=$MIN ceiling=$CEIL"
if [ "$MIN" -gt "$CEIL" ]; then
  echo "::error::needs SDK $MIN, device is $CEIL. Set max_app_version in src/targets.json."
  exit 1
fi
echo "OK: minimum SDK requirement fits ceiling $CEIL (not a device compatibility test)"
