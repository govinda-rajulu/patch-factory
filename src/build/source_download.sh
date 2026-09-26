#!/bin/bash
# Secret-free preparation adapter to the existing store routines.
set -uo pipefail
ID="${1:?target required}"
RVER="${2:?resolved version required}"
T=$(jq -ce --arg id "$ID" '.[] | select(.id==$id and .enabled==true)' src/targets.json) || exit 1
PKG=$(jq -r '.package' <<<"$T")
APK_NAME=$(jq -r '.apk_name' <<<"$T")
APK_TYPE=$(jq -r '.apk_type // "apk"' <<<"$T")
SRC=$(jq -r '.source // "apkmirror"' <<<"$T")
ANYVER=$(jq -r '.any_version // false' <<<"$T")
set +u; source ./src/build/utils.sh; set -u
version="$RVER"; lock_version=""; prefer_version=""; PF_APK_RAW_ONLY=0
if [ "$ANYVER" = "true" ]; then version=""; lock_version=1; fi
if [ "$SRC" = "apkpure" ]; then
  set +u; get_apkpure "$PKG" "$APK_NAME" "$APK_TYPE"; RC=$?; set -u
else
  near_version=1
  set +u; get_apk "$PKG" "$APK_NAME" "$APK_TYPE"; RC=$?; set -u
fi
if [ "$RC" -ne 0 ]; then
  python3 src/build/source_fallback.py "$ID" "$RVER"
  exit "$?"
fi
exit 0
