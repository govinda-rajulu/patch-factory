#!/bin/bash
# Report-only minSdk gate.
# Tries four readers. Never hides why a read failed.
APK="${1:?apk path}"; CEIL="${2:-29}"
MIN=""
SDK="${ANDROID_HOME:-/usr/local/lib/android/sdk}"
ERR=$(mktemp); trap 'rm -f "$ERR"' EXIT

AAPT=$(find "$SDK" -name aapt2 -type f 2>/dev/null | sort -V | tail -1)

# 1. aapt2 badging
if [ -n "$AAPT" ]; then
  echo "[i] aapt2: $AAPT"
  MIN=$("$AAPT" dump badging "$APK" 2>"$ERR" | grep -oP "sdkVersion:'\K[0-9]+" | head -1)
  if [ -z "$MIN" ] && [ -s "$ERR" ]; then
    echo "[i] badging failed:"; head -3 "$ERR" | sed 's/^/    /'
  fi
else
  echo "[i] no aapt2 under $SDK"
fi

# 2. aapt2 xmltree, tolerant of unknown API levels
if [ -z "$MIN" ] && [ -n "$AAPT" ]; then
  HEX=$("$AAPT" dump xmltree "$APK" --file AndroidManifest.xml 2>/dev/null \
        | grep -oP 'minSdkVersion[^=]*=\(type 0x10\)\K0x[0-9a-f]+' | head -1)
  [ -n "$HEX" ] && MIN=$((HEX)) && echo "[i] read via xmltree"
fi

# 3. apkanalyzer
if [ -z "$MIN" ]; then
  AK=$(find "$SDK" -name apkanalyzer -type f 2>/dev/null | sort -V | tail -1)
  if [ -n "$AK" ]; then
    MIN=$("$AK" manifest min-sdk "$APK" 2>/dev/null | grep -oE '^[0-9]+' | head -1)
    [ -n "$MIN" ] && echo "[i] read via apkanalyzer"
  fi
fi

# 4. pyaxmlparser
if [ -z "$MIN" ]; then
  if python3 -c 'import pyaxmlparser' 2>/dev/null || pip install -q pyaxmlparser 2>/dev/null; then
    MIN=$(python3 -c "
from pyaxmlparser import APK
print(APK('$APK').get_min_sdk_version() or '')
" 2>/dev/null | grep -oE '^[0-9]+' | head -1)
    [ -n "$MIN" ] && echo "[i] read via pyaxmlparser"
  fi
fi

if [ -z "$MIN" ]; then
  echo "::warning::UNVERIFIED - all four readers failed, minSdk unknown for $(basename "$APK")"
  exit 0
fi

echo "minSdkVersion=$MIN ceiling=$CEIL"
if [ "$MIN" -gt "$CEIL" ]; then
  echo "::error::needs SDK $MIN, device is $CEIL. Set max_app_version in src/targets.json."
  exit 1
fi
echo "OK: installable on SDK $CEIL"
