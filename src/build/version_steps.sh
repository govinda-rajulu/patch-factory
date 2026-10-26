#!/bin/bash
# Version step-down (W7, owner design 9 Oct 2026). Sourced by build.sh after utils.sh.
# Dynamic: the newest version the provider supports, or the store's newest when the
# provider lists no version ("any"). When that APK needs a newer Android than the phone
# cap, the build tries the next lower version, at most PF_MAX_STEPS times.
# Fixed: min_sdk_ceiling, ARM64, max_app_version when set, an exact version_code pin
# (no step-down at all), and PF_MAX_STEPS. Every other gate still decides.
PF_MAX_STEPS=3

# Versions the one primary bundle in the cwd supports for PKG, newest first.
# Empty output with status 0 means the provider lists none (any version).
pf_provider_versions() {
  local pkg="$1" out workdir="${PF_VERSION_WORKDIR:-.}"
  local jars=("$workdir"/morphe-desktop-*.jar) mpps=("$workdir"/*.mpp)
  if [ "${#jars[@]}" -ne 1 ] || [ ! -f "${jars[0]}" ] || [ "${#mpps[@]}" -ne 1 ] || [ ! -f "${mpps[0]}" ]; then
    echo "STEP_DOWN needs exactly one patcher jar and one primary bundle" >&2; return 2
  fi
  if ! out=$(java -jar "${jars[0]}" list-versions --patches="${mpps[0]}" -x -u -f "$pkg" 2>&1); then
    echo "STEP_DOWN list-versions failed" >&2; return 2
  fi
  sed -n 's/^[[:space:]]*\([0-9][0-9.]*\).*(\([0-9]\{1,\}\) patch.*/\1/p' <<<"$out" | sort -urV
}

# Stable versions on the APKMirror listing for PKG (first two pages), newest first.
pf_store_versions() {
  local pkg="$1" list_url url page html="" text root="${PF_VERSION_ROOT:-.}"
  list_url=$(jq -r --arg pkg "$pkg" '.apkmirror[$pkg].list_url // empty' "$root/src/build/helper/apps.json")
  if [ -z "$list_url" ]; then echo "STEP_DOWN no APKMirror listing for $pkg" >&2; return 2; fi
  for page in 1 2; do
    url="$list_url"
    if [ "$page" -gt 1 ]; then
      case "$list_url" in
        *\?*) url="${list_url%%\?*}"; url="${url%/}/page/$page/?${list_url#*\?}" ;;
        *) url="${list_url%/}/page/$page/" ;;
      esac
    fi
    if ! _cf_get "$url"; then echo "STEP_DOWN store listing page $page unreadable" >&2; return 2; fi
    while IFS= read -r text; do
      grep -oE '[0-9]+([.][0-9]+)+' <<<"$text" | tail -1
    done < <(printf '%s' "$html" | python3 "${PF_VERSION_ROOT:-.}/src/build/html_select.py" 'h5.appRowTitle a.fontBlack json{}' | \
      jq -r '.[] | select(.text | test("(?i)beta|alpha") | not) | .text')
  done | sort -urV
}

# Prints "VERSION SOURCE" for the next version below CURRENT (and not above MAXVER).
# Status 1: nothing lower exists. Status 2: the version list could not be read.
# Shared bounded entry point for non-build consumers. The build loop performs the same
# PF_MAX_STEPS check inline; this wrapper exposes that exact limit without duplicating it.
pf_next_version_bounded() {
  local step="$1" pkg="$2" current="$3" maxver="$4"
  [ "$step" -lt "$PF_MAX_STEPS" ] || return 3
  pf_next_version "$pkg" "$current" "$maxver"
}

pf_next_version() {
  local pkg="$1" current="$2" maxver="$3" list src v
  list=$(pf_provider_versions "$pkg") || return 2
  if [ -n "$list" ]; then src=provider; else list=$(pf_store_versions "$pkg") || return 2; src=store; fi
  while IFS= read -r v; do
    [[ "$v" =~ ^[0-9]+([.][0-9]+)*$ ]] || continue
    [ "$v" != "$current" ] || continue
    [ "$(printf '%s\n%s\n' "$v" "$current" | sort -V | tail -1)" = "$current" ] || continue
    if [ -n "$maxver" ] && [ "$maxver" != "null" ]; then
      [ "$(printf '%s\n%s\n' "$v" "$maxver" | sort -V | tail -1)" = "$maxver" ] || continue
    fi
    echo "$v $src"; return 0
  done <<<"$list"
  return 1
}
