#!/bin/bash
APK="${1:?apk path}"; CEIL="${2:-29}"
AAPT=$(find "${ANDROID_HOME:-/usr/local/lib/android/sdk}" -name aapt2 -type f 2>/dev/null | sort -V | tail -1)
[ -z "$AAPT" ] && { echo "::warning::aapt2 not found, skipping"; exit 0; }
MIN=$("$AAPT" dump badging "$APK" 2>/dev/null | grep -oP "sdkVersion:'\K[0-9]+" | head -1)
[ -z "$MIN" ] && { echo "::warning::could not read minSdk"; exit 0; }
echo "minSdkVersion=$MIN ceiling=$CEIL"
if [ "$MIN" -gt "$CEIL" ]; then
  echo "::error::needs SDK $MIN, device is $CEIL. Set max_app_version in src/targets.json."
  exit 1
fi
echo "OK: installable on SDK $CEIL"
