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
# A nearest-lower APKMirror result is safe only inside the same release line: the same
# release written with fewer trailing components (Prime Video: 3.0.470.1047 -> 3.0.470) or
# an older build with the same first two numbers (Hotstar: 26.06.22.3 -> 26.06.08.2).
# Anything else (Amazon Music: 2.36.1 -> 2.8.1, a 2013 file) is a real downgrade and is
# refused (W16x, owner rule: never accept a silent downgrade). Every failure path refuses.
pf_strip0() { local x="${1#"${1%%[!0]*}"}"; printf '%s' "${x:-0}"; }
pf_near_version_safe() { # WANTED GOT
  local wanted="$1" got="$2" kw kg wa wb ga gb x rest
  [ -n "$wanted" ] && [ -n "$got" ] || return 1
  kw=$(pf_ver_key "$wanted") || return 1
  kg=$(pf_ver_key "$got") || return 1
  [ -n "$kw" ] && [ -n "$kg" ] || return 1
  [ "$kw" = "$kg" ] && return 0
  case "$got" in *.*) ;; *) return 1 ;; esac
  case "$wanted" in "$got".*) return 0 ;; esac
  IFS=. read -r wa wb rest <<<"$wanted"
  IFS=. read -r ga gb rest <<<"$got"
  for x in "$wa" "$wb" "$ga" "$gb"; do
    case "$x" in ''|*[!0-9]*) return 1 ;; esac
  done
  [ "$(pf_strip0 "$wa")" = "$(pf_strip0 "$ga")" ] && [ "$(pf_strip0 "$wb")" = "$(pf_strip0 "$gb")" ]
}
# W16x: one place for the near-version decision after an APKMirror download (build.sh and
# source_download.sh). Same version: silent. Same release line: a STORE_NEAR_VERSION line.
# Otherwise: STORE_DOWNGRADE_REFUSED ... reason=near_version_gap, the download removed, status 1.
pf_near_guard() { # STORE GOT WANTED NAME
  local store="$1" got="$2" wanted="$3" name="$4" kw kg
  [ -n "$wanted" ] || return 0
  if [ -n "$got" ]; then
    kw=$(pf_ver_key "$wanted") && kg=$(pf_ver_key "$got") && [ -n "$kw" ] && [ "$kw" = "$kg" ] && return 0
  fi
  if pf_near_version_safe "$wanted" "$got"; then
    echo "STORE_NEAR_VERSION store=$store got=$got wanted=$wanted (same release line)"
    return 0
  fi
  echo "STORE_DOWNGRADE_REFUSED store=$store got=${got:-unknown} wanted=$wanted reason=near_version_gap"
  rm -rf "./download/$name.apk" "./download/$name.apkm" "./download/$name.xapk" "./download/$name"
  return 1
}
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
