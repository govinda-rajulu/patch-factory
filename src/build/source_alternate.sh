#!/bin/bash
# Called only in a fresh isolated directory by source_fallback.py after admission.
set -uo pipefail
ID="${1:?target required}"
RVER="${2:?exact version required}"
SRC="${3:?source required}"
[[ "$RVER" =~ ^[0-9]+(\.[0-9]+)*$ ]] || exit 1
[[ "$SRC" = apkmirror || "$SRC" = apkpure ]] || exit 1
T=$(jq -ce --arg id "$ID" '.[] | select(.id==$id and .enabled==true)' src/targets.json) || exit 1
PKG=$(jq -er '.package' <<<"$T") || exit 1
APK_NAME=$(jq -er '.apk_name' <<<"$T") || exit 1
APK_TYPE=$(jq -er '.apk_type // "apk"' <<<"$T") || exit 1
# Only source_fallback.py creates this selector after exact admission.
APK_TYPE=$(python3 src/build/source_variant.py kind qualified-variant.json "$SRC" "$PKG" "$RVER") || exit 1
PF_APK_VARIANT_URL=""
if [ "$SRC" = apkmirror ]; then
  PF_APK_VARIANT_URL=$(python3 src/build/source_variant.py apkmirror_url qualified-variant.json "$SRC" "$PKG" "$RVER") || exit 1
fi
set +u; source ./src/build/utils.sh; set -u
version="$RVER"; lock_version=1; prefer_version=""; near_version=0
PF_APK_RAW_ONLY=1
if [ "$SRC" = apkpure ]; then
  set +u; get_apkpure "$PKG" "$APK_NAME" "$APK_TYPE"; RC=$?; set -u
else
  set +u; get_apk "$PKG" "$APK_NAME" "$APK_TYPE"; RC=$?; set -u
fi
[ "$RC" -eq 0 ] && [ "$version" = "$RVER" ] || exit 1
