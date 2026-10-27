#!/bin/bash
# Secret-free preparation adapter to the existing store routines.
set -uo pipefail
ID="${1:?target required}"
# W16d: an empty version is legal (the provider lists none, e.g. Amazon Music), as in build.sh;
# the argument must still be given. ":?" refused it in 0 s and Qualify went red (24 Oct).
RVER="${2?resolved version required}"
T=$(jq -ce --arg id "$ID" '.[] | select(.id==$id and .enabled==true)' src/targets.json) || exit 1
PKG=$(jq -r '.package' <<<"$T")
APK_NAME=$(jq -r '.apk_name' <<<"$T")
APK_TYPE=$(jq -r '.apk_type // "apk"' <<<"$T")
SRC=$(jq -r '.source // "apkmirror"' <<<"$T")
ANYVER=$(jq -r '.any_version // false' <<<"$T")
ARCH=$(jq -r '.arch // ""' <<<"$T")
DPI=$(jq -r '.dpi // ""' <<<"$T")
export PF_SDK_CEILING="$(jq -r '.min_sdk_ceiling // 29' <<<"$T")"  # W16h (L088): skip variant rows above the cap
PF_PIN_CODE=$(jq -r '.version_code // ""' <<<"$T")  # W15: get_apk picks the row with this code
set +u; source ./src/build/utils.sh; set -u
source ./src/build/store_chain.sh
version="$RVER"; lock_version=""; prefer_version=""; PF_APK_RAW_ONLY=0
if [ "$ANYVER" = "true" ]; then version=""; lock_version=1; fi
if [ "$SRC" = "apkpure" ]; then
  set +u; get_apkpure "$PKG" "$APK_NAME" "$APK_TYPE"; RC=$?; set -u
else
  near_version=1
  set +u; get_apk "$PKG" "$APK_NAME" "$APK_TYPE" "$ARCH" "$DPI"; RC=$?; set -u
fi
if [ "$RC" -eq 0 ]; then pf_apkpure_exact "$SRC" "$version" "$RVER" "$ANYVER" "$APK_NAME" || exit 1; fi
if [ "$RC" -ne 0 ]; then
  try_other_store "$PKG" "$APK_NAME" "$APK_TYPE" "$SRC" "${version:-$RVER}" "$ANYVER" "$ARCH" "$DPI"; RC=$?
fi
if [ "$RC" -ne 0 ]; then
  [ "${PF_STORE_DOWNGRADE_REFUSED:-0}" = "1" ] && exit 1
  python3 src/build/source_fallback.py "$ID" "$RVER"
  exit "$?"
fi
exit 0
