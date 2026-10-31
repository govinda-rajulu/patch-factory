#!/bin/bash
# Fetch the same APKMirror listing/release pages as get_apk, but stop at the
# pinned variant row.  This script must never request a variant page or a binary.
set -uo pipefail

ROOT=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/../.." && pwd)
cd "$ROOT" || exit 1

pin_fetch_main() {
  local package=${1:?package} apk_name=${2:?apk_name} apk_type=${3:?apk_type}
  local wanted_version=${4:?version} wanted_code=${5:?version_code}
  local arch=${6:-} dpi=${7:-} ceiling=${8:-29} evidence=${9:?evidence_dir}
  mkdir -p -- "$evidence" || return 1
  export PF_STORE_LAZY=1 PF_UTILS_NO_SETUP=1 PF_PIN_CHECK_ONLY=1
  export PF_CAPTURE_DIR="$evidence" PF_CAPTURE_MAX_BYTES=2097152 PF_CAPTURE_SEQ=0
  export PF_PIN_CODE="$wanted_code" PF_SDK_CEILING="$ceiling"
  export version="$wanted_version" lock_version=0 prefer_version=""
  unset near_version PF_APK_RAW_ONLY PF_APK_VARIANT_URL
  # get_apk owns list-page selection, exact-version slug rewriting, ten-page fallback,
  # release-row extraction, and VARIANT_PICK.  Its PF_PIN_CHECK_ONLY branch returns
  # before the first variant-page/download request.
  set +u
  get_apk "$package" "$apk_name" "$apk_type" "$arch" "$dpi"
  local rc=$?
  set -u
  return "$rc"
}

# Tests may source this file with PF_PIN_FETCH_SOURCE_ONLY=1, replace _cf_get with a
# fixture transport, and call pin_fetch_main directly to record every requested URL.
export PF_STORE_LAZY=1 PF_UTILS_NO_SETUP=1
export PF_TMP_DIR="${PF_TMP_DIR:-$(mktemp -d "${TMPDIR:-/tmp}/pf-pin.XXXXXX")}"
if [[ "${PF_PIN_FETCH_SOURCE_ONLY:-0}" != "1" ]]; then
  cleanup() { rm -rf -- "$PF_TMP_DIR"; }
  trap cleanup EXIT
fi
set +u
source ./src/build/utils.sh
set -u
if [[ "${PF_PIN_FETCH_SOURCE_ONLY:-0}" != "1" ]]; then
  if [[ $# -ne 9 ]]; then
    echo "usage: $0 PACKAGE APK_NAME APK_TYPE VERSION VERSION_CODE ARCH DPI SDK_CEILING EVIDENCE_DIR" >&2
    exit 64
  fi
  pin_fetch_main "$@"
fi
