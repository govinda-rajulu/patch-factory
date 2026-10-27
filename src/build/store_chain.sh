#!/bin/bash
# Second store, same gates (owner design, 6 Oct 2026). Called by build.sh and
# source_download.sh after the configured store failed and before the qualified
# exact-version fallback. Trust does not change: the caller's package, version, SDK,
# pinned version-code and finished-identity gates still decide; only the store differs.
# Usage: try_other_store PKG APK_NAME APK_TYPE SRC RVER ANYVER ARCH DPI
# W16v (27 Oct 2026): two version strings name the same release when their dot parts match as
# numbers, ignoring leading zeros and trailing .0 parts (26.36.01 = 26.36.1, 9.0 = 9). Any
# other text must match exactly.
pf_ver_key() {
  # Strings, not awk numbers: mawk turns long digit runs into 1e+15 (W16v round 2).
  printf '%s\n' "$1" | awk -F. '{n=NF; while (n>1 && $n ~ /^0+$/) n--; s=""; for (i=1;i<=n;i++) {x=$i; if (x ~ /^[0-9]+$/) {sub(/^0+/, "", x); if (x == "") x="0"}; s=s (i>1?".":"") x}; print s}'
}
# W16v round 2: APKPure answers /download/V with the page of another version at times; its h2
# names what was served. An exact-version request that got another version is refused.
pf_apkpure_exact() { # STORE GOT WANTED ANYVER NAME
  [ "$1" = "apkpure" ] && [ -n "$3" ] && [ "$4" != "true" ] || return 0
  pf_ver_same "$2" "$3" && return 0
  echo "STORE_DOWNGRADE_REFUSED store=apkpure got=${2:-unknown} wanted=$3"
  rm -rf -- "./download/$5.apk" "./download/$5.apkm" "./download/$5.xapk" "./download/$5"
  return 1
}
pf_ver_same() { [ -n "$1" ] && [ -n "$2" ] && [ "$(pf_ver_key "$1")" = "$(pf_ver_key "$2")" ]; }
try_other_store() {
  local pkg="$1" name="$2" type="$3" src="$4" rver="$5" anyver="$6" arch="$7" dpi="$8" alt rc
  if [ "$src" = "apkpure" ]; then alt=apkmirror; else alt=apkpure; fi
  if ! jq -e --arg p "$pkg" --arg s "$alt" '(.[$s][$p] // {}) | ((.list_url // .download_url) // "") | length > 0' src/build/helper/apps.json > /dev/null 2>&1; then
    echo "STORE_CHAIN no $alt mapping for $pkg; going to the qualified fallback"
    return 1
  fi
  echo "STORE_CHAIN $src failed for $pkg ${rver:-latest}; trying $alt"
  version="$rver"; lock_version=""; prefer_version=""
  if [ "$anyver" = "true" ] && [ -z "$rver" ]; then version=""; lock_version=1; fi
  if [ "$alt" = "apkpure" ]; then
    set +u; get_apkpure "$pkg" "$name" "$type"; rc=$?; set -u
  else
    near_version=1
    set +u; get_apk "$pkg" "$name" "$type" "$arch" "$dpi"; rc=$?; set -u
  fi
  if [ "$rc" -eq 0 ] && [ -n "$rver" ] && ! pf_ver_same "$version" "$rver"; then
    echo "STORE_DOWNGRADE_REFUSED store=$alt got=${version:-unknown} wanted=$rver"
    PF_STORE_DOWNGRADE_REFUSED=1
    export PF_STORE_DOWNGRADE_REFUSED
    rm -f -- "./download/$name.apk" "./download/$name.apkm" "./download/$name.xapk" "./download/$name"
    return 1
  fi
  if [ "$rc" -eq 0 ]; then echo "STORE_CHAIN used $alt"; fi
  return "$rc"
}
