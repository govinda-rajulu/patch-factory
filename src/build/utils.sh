#!/bin/bash

# W16o: F-03, use a private scratch directory so response bodies and headers cannot
# be redirected through attacker-created names in shared /tmp.
umask 077
# W16o round 1: MED-1, every production caller gets transport enforcement by default.
: "${PF_ENFORCE_EFFECTIVE_URL:=1}"
: "${PF_STORE_MAX_BYTES:=1024M}"
export PF_ENFORCE_EFFECTIVE_URL PF_STORE_MAX_BYTES
if [[ -z "${PF_TMP_DIR:-}" ]]; then
  PF_TMP_DIR=$(mktemp -d "${RUNNER_TEMP:-/tmp}/pf-utils.XXXXXX")
  trap 'rm -rf -- "$PF_TMP_DIR"' EXIT
fi

# The build performs this setup when it needs APK tooling.  Read-only listing probes
# source the same functions with PF_UTILS_NO_SETUP=1 so loading utils.sh cannot create
# artifacts, download tooling, or make the user-agent probe.
if [[ "${PF_UTILS_NO_SETUP:-0}" != "1" ]]; then
  mkdir ./release ./download

  # HTML selector helper is checked into the repository; no downloaded parser is needed.
  #Setup APKEditor for install combine split apks
  bash ./src/build/tooling.sh apkeditor || exit 1
  APKEditor="./APKEditor.jar"
  #Find lastest user_agent
  user_agent=$(wget -qO- https://www.whatismybrowser.com/guides/the-latest-user-agent/firefox | tr '\n' ' ' | sed 's#</tr>#\n#g' | grep 'Firefox (Standard)' | sed -n 's/.*<span class="code">\([^<]*Android[^<]*\)<\/span>.*/\1/p') \
  || user_agent=
  [ -z "$user_agent" ] && {
    user_agent='Mozilla/5.0 (Android 16; Mobile; rv:146.0) Gecko/146.0 Firefox/146.0'
    echo "[-] Can't found lastest user-agent"
  }
else
  APKEditor="${APKEditor:-./APKEditor.jar}"
  user_agent="${user_agent:-Mozilla/5.0 (Android 16; Mobile; rv:146.0) Gecko/146.0 Firefox/146.0}"
fi

#################################################

# Colored output logs
green_log() {
    echo -e "\e[32m$1\e[0m"
}
red_log() {
    echo -e "\e[31m$1\e[0m"
}
yellow_log() {
    echo -e "\e[33m$1\e[0m"
}

#################################################

# Download Github assets requirement:
dl_gh() {
  if [ $3 == "prerelease" ]; then
    local repo=$1
    for repo in $1 ; do
      local owner=$2 tag=$3 found=0 assets=0
      releases=$(wget -qO- "https://api.github.com/repos/$owner/$repo/releases")
      while read -r line; do
        if [[ $line == *"\"tag_name\":"* ]]; then
          tag_name=$(echo $line | cut -d '"' -f 4)
          if [ "$tag" == "latest" ] || [ "$tag" == "prerelease" ]; then
            found=1
          else
            found=0
          fi
        fi
        if [[ $line == *"\"prerelease\":"* ]]; then
          prerelease=$(echo $line | cut -d ' ' -f 2 | tr -d ',')
          if [ "$tag" == "prerelease" ] && [ "$prerelease" == "true" ] ; then
            found=1
          elif [ "$tag" == "prerelease" ] && [ "$prerelease" == "false" ]; then
            found=1
          fi
        fi
        if [[ $line == *"\"assets\":"* ]]; then
          if [ $found -eq 1 ]; then
            assets=1
          fi
        fi
        if [[ $line == *"\"browser_download_url\":"* ]]; then
          if [ $assets -eq 1 ]; then
            url=$(echo $line | cut -d '"' -f 4)
            if [[ $url != *.asc ]]; then
              name=$(basename "$url")
              wget -q -O "$name" "$url"
              green_log "[+] Downloading $name from $owner"
            fi
          fi
        fi
        if [[ $line == *"],"* ]]; then
          if [ $assets -eq 1 ]; then
            assets=0
            break
          fi
        fi
      done <<< "$releases"
    done
  else
    for repo in $1 ; do
      tags=$( [ "$3" == "latest" ] && echo "latest" || echo "tags/$3" )
      wget -qO- "https://api.github.com/repos/$2/$repo/releases/$tags" \
        | jq -r '.assets[] | "\(.browser_download_url) \(.name)"' \
        | while read -r url names; do
          if [[ $url != *.asc ]]; then
            if [[ "$3" == "latest" && "$names" == *dev* ]]; then
              continue
            fi
            green_log "[+] Downloading $names from $2"
            wget -q -O "$names" $url
          fi
        done
    done
  fi
}

dl_gl() {
  local repo=$1 owner=$2 tag=${3:-latest}
  local project_path="${owner}%2F${repo}"
  local api_url="https://gitlab.com/api/v4/projects/${project_path}/releases"

  local releases
  releases=$(wget -qO- "$api_url")

  local release
  if [[ "$tag" == "latest" ]]; then
    release=$(echo "$releases" | jq -r '[.[] | select(.tag_name | test("-dev") | not)][0]')
  elif [[ "$tag" == "prerelease" ]]; then
    release=$(echo "$releases" | jq -r '[.[] | select(.tag_name | test("-dev"))][0]')
  else
    release=$(wget -qO- "$api_url/$tag")
  fi

  if [[ -z "$release" ]] || [[ "$release" == "null" ]]; then
    red_log "[-] No matching release found for $owner/$repo ($tag)"
    return 1
  fi

  local tag_name
  tag_name=$(echo "$release" | jq -r '.tag_name')

  echo "$release" | jq -r '.assets.links[] | "\(.direct_asset_url // .url) \(.name)"' | \
    while read -r url name; do
      if [[ -n "$url" ]] && [[ "$url" != "null" ]] && [[ $url != *.asc ]]; then
        green_log "[+] Downloading $name from $owner"
        wget -q -O "$name" "$url"
      fi
    done
}

#################################################

# Get patches list:
get_patches_key() {
	excludePatches=""
	includePatches=""
	excludeLinesFound=false
	includeLinesFound=false

	local patchDir="src/patches/$1"
	local patch_name line1 line2

	sed -i 's/\r$//' "$patchDir/include-patches"
	sed -i 's/\r$//' "$patchDir/exclude-patches"

	while IFS= read -r line1 || [[ -n "$line1" ]]; do
		[[ -z "$line1" || "$line1" == "#"* ]] && continue
		excludePatches+=" -d \"$line1\""
		excludeLinesFound=true
	done < "$patchDir/exclude-patches"

	while IFS= read -r line2 || [[ -n "$line2" ]]; do
		[[ -z "$line2" || "$line2" == "#"* ]] && continue
		patch_name="${line2%%|*}"
		includePatches+=" -e \"$patch_name\""
		includeLinesFound=true
	done < "$patchDir/include-patches"

	if [ "$excludeLinesFound" = false ]; then
		excludePatches=""
	fi
	if [ "$includeLinesFound" = false ]; then
		includePatches=""
	fi

	export excludePatches
	export includePatches
}

#################################################

# W16o: F-07/F-10, validate the initial store URL and bound final transfers.
# The initial URL is the URL selected by the store page.  The final URL is
# learned only from the real, header-correct binary transfer below.
pf_store_url_check() {
	local url=$1
	python3 - "$url" <<'PY'
import sys
from urllib.parse import urlsplit
u = urlsplit(sys.argv[1])
if u.scheme != 'https' or u.username or u.password or u.port not in (None, 443) or not u.hostname:
    raise SystemExit(1)
h = u.hostname.lower().rstrip('.')
if not (h == 'apkmirror.com' or h.endswith('.apkmirror.com') or
        h == 'apkpure.com' or h.endswith('.apkpure.com')):
    raise SystemExit(1)
PY
}

pf_store_size_limit_bytes() {
	python3 - "${PF_STORE_MAX_BYTES:-1024M}" <<'PY'
import re
import sys

value = sys.argv[1].strip()
match = re.fullmatch(r'(\d+)([BKMG]?)', value, re.IGNORECASE)
if not match:
    print('PF_STORE_MAX_BYTES must be an integer with an optional curl suffix B, K, M, or G', file=sys.stderr)
    raise SystemExit(1)
number = int(match.group(1))
unit = match.group(2).upper()
multiplier = {'': 1, 'B': 1, 'K': 1024, 'M': 1024 ** 2, 'G': 1024 ** 3}[unit]
print(number * multiplier)
PY
}

pf_curl_effective_host_ok() {
	local effective=$1 store=${2:-store}
	python3 - "$effective" "$store" <<'PY'
import sys
from urllib.parse import urlsplit
u = urlsplit(sys.argv[1])
if u.scheme != 'https' or u.username or u.password or u.port not in (None, 443) or not u.hostname:
    raise SystemExit(1)
h = u.hostname.lower().rstrip('.')
known_final_hosts = {'apkpure': {'data.winudf.com'}}
store = sys.argv[2]
if h not in known_final_hosts.get(store, set()):
    print(f'::warning:: STORE_FINAL_HOST {store} unknown final host {h}; allowing until live evidence grows')
print(f'STORE_FINAL_HOST {store} {h}')
PY
}

pf_wget_store_transfer() {
	# W16o smoke run 40398219589: APKMirror's download endpoint answered curl with 403 on 8 of
	# the 14 apps that downloaded from it (6 passed), where this exact wget request built 17 of 17
	# the day before (W16n). Keep the base request byte for byte; add only local checks: a
	# private candidate, never empty, size bounded. wget follows redirects without an HTTPS-only
	# rule, as base did (OPEN-WORK item 2).
	local url=$1 dest=$2 referer=$3 ua=$4 rc=0 candidate_bytes max_bytes
	local -a cookie_args=()
	[[ -n "${FS_COOKIES:-}" ]] && cookie_args=(--header "Cookie: $FS_COOKIES")
	wget -q -O "$dest" \
		--header="User-Agent: $ua" \
		--referer="$referer" \
		"${cookie_args[@]}" \
		--timeout=120 \
		"$url" || rc=$?
	if [[ "$rc" -ne 0 ]]; then
		rm -f -- "$dest"
		return "$rc"
	fi
	max_bytes=$(pf_store_size_limit_bytes) || { rm -f -- "$dest"; return 1; }
	candidate_bytes=$(stat -c %s -- "$dest") || { rm -f -- "$dest"; return 1; }
	if [[ "$candidate_bytes" -eq 0 || "$candidate_bytes" -gt "$max_bytes" ]]; then
		rm -f -- "$dest"
		return 1
	fi
}

pf_curl_store_transfer() {
	local url=$1 dest=$2 referer=$3 ua=$4 store=$5 effective_file effective curl_rc=0
	local candidate_bytes max_bytes
	local -a cookie_args=()
	# --cookie with NAME=VALUE data is sent on every redirected request, as wget sent its
	# Cookie header; a raw --header Cookie is dropped on a cross-host redirect (curl manual).
	# Data without "=" would be read as a file name, so it is never passed.
	[[ "${FS_COOKIES:-}" == *=* ]] && cookie_args=(--cookie "$FS_COOKIES")
	effective_file=$(mktemp "$PF_TMP_DIR/store-effective.XXXXXX") || return 1
	# Keep this as the sole binary request: its headers and cookies match the
	# base wget transfer, while curl records the redirect result privately.
	if curl --fail --silent --show-error --location \
		--proto '=https' --proto-redir '=https' --max-redirs 10 \
		--max-filesize "$PF_STORE_MAX_BYTES" \
		--connect-timeout 30 --speed-limit 1024 --speed-time 120 \
		--retry 5 --retry-delay 5 --retry-connrefused \
		--header "User-Agent: $ua" --referer "$referer" \
		"${cookie_args[@]}" --output "$dest" --write-out '%{url_effective}' "$url" \
		>"$effective_file"; then
		:
	else
		curl_rc=$?
		rm -f -- "$effective_file" "$dest"
		return "$curl_rc"
	fi
	effective=$(cat "$effective_file") || { rm -f -- "$effective_file" "$dest"; return 1; }
	rm -f -- "$effective_file"
	pf_curl_effective_host_ok "$effective" "$store" || { rm -f -- "$dest"; return 1; }
	max_bytes=$(pf_store_size_limit_bytes) || { rm -f -- "$dest"; return 1; }
	candidate_bytes=$(stat -c %s -- "$dest") || { rm -f -- "$dest"; return 1; }
	# --max-filesize checks Content-Length, so stat also bounds chunked bodies.
	if [[ "$candidate_bytes" -eq 0 || "$candidate_bytes" -gt "$max_bytes" ]]; then
		rm -f -- "$dest"
		return 1
	fi
}

_req() {
    local cookie_args=()
    [[ -n "$FS_COOKIES" ]] && cookie_args=(--header "Cookie: $FS_COOKIES")
    if [ "$2" = "-" ]; then
        wget -nv -O "$2" --header="User-Agent: $user_agent" --header="Content-Type: application/octet-stream" --header="Accept-Language: en-US,en;q=0.9" --header="Connection: keep-alive" --header="Upgrade-Insecure-Requests: 1" --header="Cache-Control: max-age=0" --header="Accept: text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8" "${cookie_args[@]}" --keep-session-cookies --timeout=30 "$1" || rm -f "$2"
    else
        wget -nv -O "./download/$2" --header="User-Agent: $user_agent" --header="Content-Type: application/octet-stream" --header="Accept-Language: en-US,en;q=0.9" --header="Connection: keep-alive" --header="Upgrade-Insecure-Requests: 1" --header="Cache-Control: max-age=0" --header="Accept: text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8" "${cookie_args[@]}" --keep-session-cookies --timeout=30 "$1" || rm -f "./download/$2"
    fi
}
req() {
    _req "$1" "$2"
}

detect_version() {
	if [ -z "$version" ] && [ "$lock_version" != "1" ]; then
	  local jar_prefix="morphe-desktop-" patch_glob="*.mpp"

	  if [[ $(ls "${jar_prefix}"*.jar 2>/dev/null) =~ ${jar_prefix}([0-9]+) ]]; then
	    list_patches_flags="list-patches --with-packages --with-versions --with-options --patches"
	    version=$(java -jar "${jar_prefix}"*.jar $list_patches_flags $patch_glob | awk -v pkg="$1" '
		  BEGIN { found = 0; printing = 0 }
		  /^Index:/ { if (printing) exit; found = 0 }
		  /Package name: / { if ($3 == pkg) found = 1 }
		  /Compatible versions:/ { if (found) printing = 1; next }
		  printing && $1 ~ /^[0-9]+\./ { print $1 }
		' | sort -V | tail -n1)
	  fi
	fi
}

_fs_get() {
	local url=$1
	local max_retries=3
	local attempt
	for attempt in $(seq 1 $max_retries); do
		local response request
		# Encode the request safely without requiring a persistent browser session.
		request=$(jq -cn --arg url "$url" \
			'{cmd:"request.get",url:$url,maxTimeout:60000}') || return 1
		# FlareSolverr v3.5.2 starts its browser before applying maxTimeout. The README
		# request.get/maxTimeout contract (https://github.com/FlareSolverr/FlareSolverr/blob/v3.5.2/README.md)
		# therefore needs an outer deadline with room beyond the 60 s request timeout.
		response=$(curl -s --connect-timeout 5 --max-time 180 -X POST 'http://localhost:8191/v1' \
			-H 'Content-Type: application/json' \
			-d "$request")
		# Redacted observation only: never log cookies, signed URLs or raw response.
		if ! PF_DIAG_REQUEST="$url" python3 src/build/transfer_diagnostic.py resolver <<<"$response"; then
			yellow_log "[!] Download diagnostic unavailable"
		fi
		local status
		status=$(echo "$response" | jq -r '.status // empty')
		if [[ "$status" == "ok" ]]; then
			html=$(echo "$response" | jq -r '.solution.response // empty')
			export FS_COOKIES
			FS_COOKIES=$(echo "$response" | jq -r '[.solution.cookies[] | .name + "=" + .value] | join("; ")')
			user_agent=$(echo "$response" | jq -r '.solution.userAgent // empty')
			return 0
		fi
		yellow_log "[!] FlareSolverr attempt $attempt/$max_retries failed (request URL withheld)"
		sleep 5
	done
	red_log "[-] FlareSolverr failed after $max_retries attempts (request URL withheld)"
	return 1
}

_cfb_get() {
	local url=$1
	local max_retries=3
	local attempt

	for attempt in $(seq 1 $max_retries); do
		local response_file headers_file
		response_file=$(mktemp "$PF_TMP_DIR/cfb-response.XXXXXX") || return 1
		headers_file=$(mktemp "$PF_TMP_DIR/cfb-headers.XXXXXX") || { rm -f -- "$response_file"; return 1; }
		local http_code
		http_code=$(curl -s -o "$response_file" -w '%{http_code}' \
			-D "$headers_file" \
			-G --data-urlencode "url=$url" \
			--max-time 120 \
			"http://127.0.0.1:8000/html")
		if [[ "$http_code" == "200" ]]; then
			html=$(cat "$response_file")
			if [[ -n "$html" ]]; then
				export FS_COOKIES
				FS_COOKIES=$(grep -i '^x-cf-bypasser-cookies:' "$headers_file" 2>/dev/null | cut -d':' -f2- | xargs)
				local cfb_ua
				cfb_ua=$(grep -i '^x-cf-bypasser-user-agent:' "$headers_file" 2>/dev/null | cut -d':' -f2- | xargs)
				[[ -n "$cfb_ua" ]] && user_agent="$cfb_ua"
				rm -f -- "$response_file" "$headers_file"
				return 0
			fi
		else
			yellow_log "[!] CFB attempt $attempt/$max_retries: HTTP $http_code (request URL withheld)"
		fi
		rm -f -- "$response_file" "$headers_file"
	done
	return 1
}

_FFS_FAILED=0

_PF_STORE_SVC=0

# Save only HTML responses requested by the read-only pin probe.  The hook is inert for
# normal builds; the probe bounds each evidence file and never asks get_apk for a download.
_pf_capture_html() {
	local url=$1 n file
	[[ -n "${PF_CAPTURE_DIR:-}" ]] || return 0
	mkdir -p -- "$PF_CAPTURE_DIR" || return 1
	PF_CAPTURE_SEQ=$(( ${PF_CAPTURE_SEQ:-0} + 1 ))
	if [[ "$url" == */page/[0-9]*/\?* || "$url" == */page/[0-9]*/ ]]; then
		local page
		page=$(printf '%s' "$url" | sed -n 's#^.*/page/\([0-9][0-9]*\)/.*#\1#p')
		file="$PF_CAPTURE_DIR/uploads-${page:-1}.html"
	elif [[ "$url" == *-release/* || "$url" == *-release/ ]]; then
		file="$PF_CAPTURE_DIR/release.html"
	else
		file=$(printf '%s/capture-%03d.html' "$PF_CAPTURE_DIR" "$PF_CAPTURE_SEQ")
	fi

printf '%s' "$html" | head -c "${PF_CAPTURE_MAX_BYTES:-2097152}" > "$file"
}

_cf_get() {
	if declare -F pf_store_url_check >/dev/null 2>&1; then
		pf_store_url_check "$1" || { red_log "[-] store URL failed HTTPS/host policy"; return 1; }
	fi
	# W16g: the build no longer starts the store helpers up front. Start (or reuse) them the first
	# time this shell needs one, so a step-down inside an attempt still finds them. Only the build step
	# sets PF_STORE_LAZY=1; tests and other jobs never start containers (Validate red 24 Oct, L087).
	if [[ "${PF_STORE_LAZY:-0}" == "1" && "$_PF_STORE_SVC" -eq 0 && -f src/build/store_services.sh ]]; then
		_PF_STORE_SVC=1
		if ! bash src/build/store_services.sh >&2; then
			red_log "[-] store helpers could not be started; refusing store access"
			return 1
		fi
	fi
	if [[ "$_FFS_FAILED" -eq 0 ]]; then
		if _fs_get "$@"; then
			declare -F _pf_capture_html >/dev/null 2>&1 && _pf_capture_html "$1"
			return 0
		fi
		yellow_log "[!] FlareSolverr failed, falling back to CFB"
		_FFS_FAILED=1
	fi
	local cfb_rc=0
	if _cfb_get "$@"; then
		declare -F _pf_capture_html >/dev/null 2>&1 && _pf_capture_html "$1"
	else
		cfb_rc=$?
	fi
	return "$cfb_rc"
}

# wget exit codes (GNU wget manual, "Exit Status").
pf_wget_meaning() {
	case "$1" in
		1) echo generic-error ;; 2) echo parse-error ;; 3) echo file-io-error ;; 4) echo network-failure ;;
		5) echo ssl-verification-failure ;; 6) echo auth-failure ;; 7) echo protocol-error ;;
		8) echo server-error-response ;; *) echo unknown ;;
	esac
}

# W16h (L088): APKMirror rows name their minimum Android ("Android 10+", "Android 12L+").
# pf_android_sdk maps that text to an API level; pf_rows_fit_ceiling keeps the rows at or under
# the device cap. Truecaller 26.41.5 has an Android 12L+ row listed first and an Android 10+ row;
# the picker took the first and the SDK gate stopped (W16g smoke 40108958168).
pf_android_sdk() {
	case "$1" in
		4.4*) echo 19 ;; 5.0*) echo 21 ;; 5.1*) echo 22 ;; 6*) echo 23 ;; 7.0*|7) echo 24 ;; 7.1*) echo 25 ;;
		8.0*|8) echo 26 ;; 8.1*) echo 27 ;; 9*) echo 28 ;; 10*) echo 29 ;; 11*) echo 30 ;;
		12L*|12.1*) echo 32 ;; 12*) echo 31 ;; 13*) echo 33 ;; 14*) echo 34 ;; 15*) echo 35 ;;
		16*) echo 36 ;; 17*) echo 37 ;; *) echo "" ;;
	esac
}
pf_rows_fit_ceiling() {
	local rows=$1 ceil=$2 line ver sdk
	while IFS= read -r line; do
		[[ -n "$line" ]] || continue
		ver=$(grep -oP 'Android \K[0-9]+(\.[0-9]+)?L?(?=\+)' <<<"$line" | head -1)
		sdk=$(pf_android_sdk "$ver")
		# A row with no readable minimum stays: the SDK gate after download still decides.
		if [[ -z "$sdk" || "$sdk" -le "$ceil" ]]; then printf '%s\n' "$line"; fi
	done <<<"$rows"
}

get_apk() {
	local pkg_name=$1 apk_name=$2
	local pkg_type=${3:-apk} arch=${4:-} dpi=${5:-} minver=${6:-}
	local allow_near_version=${near_version:-0}
	unset near_version
	local base_url="https://www.apkmirror.com"
	local html=""

	local apps_json="./src/build/helper/apps.json"
	local list_url example_url
	list_url=$(jq -r --arg pkg "$pkg_name" '.apkmirror[$pkg].list_url // empty' "$apps_json")
	example_url=$(jq -r --arg pkg "$pkg_name" '.apkmirror[$pkg].example_url // empty' "$apps_json")

	if [[ -z "$list_url" ]]; then
		red_log "[-] Package $pkg_name not found in apps.json"
		return 1
	fi

	local base_apk
	if [[ "$pkg_type" == "bundle" ]] || [[ "$pkg_type" == "bundle_extract" ]]; then
		base_apk="$apk_name.apkm"
	else
		base_apk="$apk_name.apk"
	fi

	detect_version "$pkg_name"
	version=$(printf '%s\n' "$version" "$prefer_version" | sort -V | tail -n1)
	unset prefer_version
	export version

	green_log "[+] Detected version: ${version:-latest} [$pkg_name]"
	green_log "[+] Downloading $apk_name (type=$pkg_type arch=${arch:-any} dpi=$dpi)"

	local version_href=""

	if [[ "${PF_APK_RAW_ONLY:-0}" == "1" && -n "${PF_APK_VARIANT_URL:-}" ]]; then
		version_href="${PF_APK_VARIANT_URL#$base_url}"
		version_href="${version_href%/*/}/"
	elif [[ -n "$example_url" && -n "$version" ]]; then
		version_href="${example_url#$base_url}"
		local slug_ver
		slug_ver=$(echo "$version_href" | grep -oP '\d+(-\d+)+' | tail -1)
		local target_ver
		target_ver=$(echo "$version" | tr '.' '-' | grep -oP '\d+(-\d+)+')
		if [[ -n "$slug_ver" ]]; then
			version_href="${version_href/$slug_ver/$target_ver}"
		fi
	else
		_cf_get "$list_url" || return 1

		version_href=$(echo "$html" | python3 ./src/build/html_select.py 'h5.appRowTitle a.fontBlack json{}' | \
			jq -r '.[] | select(.text | test("(?i)beta|alpha") | not) | .href' | head -1)
		[[ -z "$version_href" ]] && \
			version_href=$(echo "$html" | python3 ./src/build/html_select.py 'h5.appRowTitle a.fontBlack attr{href}' | head -1)

		if [[ -z "$version_href" ]]; then
			red_log "[-] Could not find release on APKMirror"
			return 1
		fi

		if [[ -n "$version" ]]; then
			local slug_ver
			slug_ver=$(echo "$version_href" | grep -oP '\d+(-\d+)+' | tail -1)
			local target_ver
			target_ver=$(echo "$version" | tr '.' '-' | grep -oP '\d+(-\d+)+')
			if [[ -n "$slug_ver" ]]; then
				version_href="${version_href/$slug_ver/$target_ver}"
			fi
		fi
	fi

	green_log "[+] APKMirror release page selected (URL withheld)"

	_cf_get "$base_url$version_href" || return 1

	# W16v (27 Oct 2026). Record the first store's selected version before any fallback.
	if [[ -z "$version" ]]; then
		local resolved_version
		resolved_version=$(printf '%s\n' "$version_href" | grep -oP '[0-9]+(?:-[0-9]+)+(?=-release(?:/|$))' | tail -1 | tr '-' '.')
		if [[ -n "$resolved_version" ]]; then
			version="$resolved_version"
			export version
		fi
	fi

	if [[ "$html" == *"Page Not Found"* ]] || [[ "$html" == *"404 Whoops"* ]]; then
		yellow_log "[!] Version page not found, searching uploads pages..."
		local target_ver_dot="$version"
		local near_version_href="" near_version_value=""
		version_href=""
		for page_num in $(seq 1 10); do
			local page_url="$list_url"
			if [[ $page_num -gt 1 ]]; then
				page_url="${list_url%%\?*}/page/$page_num/?${list_url#*\?}"
			fi
			_cf_get "$page_url" || return 1
			if [[ -n "$target_ver_dot" ]]; then
				version_href=$(echo "$html" | python3 ./src/build/html_select.py 'h5.appRowTitle a.fontBlack json{}' | \
					jq -r --arg v "$target_ver_dot" '.[] | select(.text | contains($v)) | .href' | head -1)
				if [[ -z "$version_href" && "$allow_near_version" == "1" ]]; then
					local release_text release_href release_version
					while IFS=$'\t' read -r release_text release_href; do
						release_version=$(echo "$release_text" | grep -oP '\d+(\.\d+)+' | tail -1)
						[[ -z "$release_version" ]] && continue
						if [[ "$(printf '%s\n' "$release_version" "$target_ver_dot" | sort -V | tail -n1)" == "$target_ver_dot" && "$release_version" != "$target_ver_dot" ]]; then
							if [[ -z "$near_version_value" || "$(printf '%s\n' "$near_version_value" "$release_version" | sort -V | tail -n1)" == "$release_version" ]]; then
								near_version_value="$release_version"
								near_version_href="$release_href"
							fi
						fi
					done < <(echo "$html" | python3 ./src/build/html_select.py 'h5.appRowTitle a.fontBlack json{}' | \
						jq -r '.[] | select(.text | test("(?i)beta|alpha") | not) | [.text, .href] | @tsv')
				fi
			else
				version_href=$(echo "$html" | python3 ./src/build/html_select.py 'h5.appRowTitle a.fontBlack json{}' | \
					jq -r '.[] | select(.text | test("(?i)beta|alpha") | not) | .href' | head -1)
			fi
			[[ -n "$version_href" ]] && break
		done
		if [[ -z "$version_href" && -n "$near_version_href" ]]; then
			version_href="$near_version_href"
			version="$near_version_value"
			export version
			yellow_log "[!] Exact version $target_ver_dot unavailable; using nearest lower version $version"
		fi
		if [[ -z "$version_href" ]]; then
			red_log "[-] Could not find version on APKMirror"
			return 1
		fi
		green_log "[+] APKMirror release page selected (URL withheld)"
	_cf_get "$base_url$version_href" || return 1
		if [[ -z "$version" ]]; then
			local resolved_version
			resolved_version=$(printf '%s\n' "$version_href" | grep -oP '[0-9]+(?:-[0-9]+)+(?=-release(?:/|$))' | tail -1 | tr '-' '.')
			if [[ -n "$resolved_version" ]]; then
				version="$resolved_version"
				export version
			fi
		fi
	fi

	local type_badge="APK"
	[[ "$pkg_type" == "bundle" || "$pkg_type" == "bundle_extract" ]] && type_badge="BUNDLE"

	local vtable_html rows variant_href=""
	# Qualified alternates select a reviewed page, not the first matching row.
	# Successful primary behavior is unchanged; this lever requires raw-only mode.
	if [[ "${PF_APK_RAW_ONLY:-0}" == "1" && -n "${PF_APK_VARIANT_URL:-}" ]]; then
		variant_href="${PF_APK_VARIANT_URL#$base_url}"
		local matched_type="$type_badge"
		local variant_page_loaded=false
	else
	vtable_html=$(echo "$html" | python3 ./src/build/html_select.py 'div.variants-table')
	rows=$(echo "$vtable_html" | tr '\n' ' ' | sed 's/<div class="table-row/\n<div class="table-row/g')

	local dpi_fallback=("120-640dpi" "120-480dpi" "480-640dpi" "480dpi")
	local type_attempts=("$type_badge")
	if [[ "$type_badge" == "BUNDLE" ]]; then
		type_attempts+=("APK")
	else
		type_attempts+=("BUNDLE")
	fi

	local matched_type=""
	local variant_page_loaded=false
	# W16k (owner, 25 Oct 2026: "what about architecture and sdk match?"): variant_pick.py judges
	# every row on chip, minimum Android and screen together and never keeps a row that does not
	# fit. Exit 4 = rows exist but none fits this phone: the caller tries the other store, then a
	# lower version (build.sh). type_attempts stays for the log line only.
	local pick pick_rc pick_log
	pick_log=$(mktemp "$PF_TMP_DIR/variant-pick.XXXXXX")
	pick=$(printf '%s\n' "$rows" | python3 ./src/build/variant_pick.py --type "$type_badge" --arch "$arch" --dpi "$dpi" \
		--ceiling "${PF_SDK_CEILING:-}" --minver "$minver" --pin "${PF_PIN_CODE:-}" 2>"$pick_log")
	pick_rc=$?
	grep -E 'VARIANT_PICK (chose|none|skip)' "$pick_log" | head -12 | while IFS= read -r l; do yellow_log "[i] $l"; done
	grep -q 'VARIANT_PICK arch fallback' "$pick_log" && yellow_log "[!] Arch fallback: $arch -> universal"
	rm -f "$pick_log"
	if [[ "$pick_rc" -eq 4 ]]; then
		red_log "[-] no build of version ${version:-latest} fits this phone (Android API ${PF_SDK_CEILING:-?}, arm64)"
		return 4
	fi
	if [[ "$pick_rc" -eq 0 && -n "$pick" ]]; then
		matched_type="${pick%%$'\t'*}"
		variant_href="${pick#*$'\t'}"
		[[ "$matched_type" != "$type_badge" ]] && yellow_log "[!] Type fallback: $type_badge -> $matched_type"
		[[ -n "${PF_PIN_CODE:-}" ]] && grep -qw -- "$PF_PIN_CODE" <<<"$(printf '%s\n' "$rows" | grep -F "$variant_href")" && green_log "[+] variant row carries the pinned version code $PF_PIN_CODE"
	fi

	if [[ -z "$variant_href" ]]; then
		local direct_apk_href
		direct_apk_href=$(echo "$html" | python3 ./src/build/html_select.py 'a.downloadButton attr{href}' | grep 'forcebaseapk' | head -1)
		if [[ -n "$direct_apk_href" && -z "$arch" && -z "$dpi" && -z "$minver" ]]; then
			matched_type="APK"
			variant_page_loaded=true
			[[ "$type_badge" != "APK" ]] && yellow_log "[!] Type fallback: $type_badge -> APK"
			yellow_log "[!] APKMirror redirected directly to the APK download page"
		else
			red_log "[-] Could not find variant (type=$type_badge arch=${arch:-any} dpi=$dpi)"
			return 1
		fi
	fi
	fi
	# Read-only pin probes stop after the same release-row extraction and picker.  In
	# particular, do not fetch the variant page, download-button page, or final binary URL.
	if [[ "${PF_PIN_CHECK_ONLY:-0}" == "1" ]]; then
		local pin_row=""
		if [[ -n "${PF_PIN_CODE:-}" ]]; then
			pin_row=$(printf '%s\n' "$rows" | python3 -c '
import re, sys
code = sys.argv[1]
for row in sys.stdin.read().splitlines():
    if re.search(r"(?i)(?:version[ _-]?code|versionCode|\bcode\b)[^0-9]{0,40}" + re.escape(code) + r"(?![0-9])", row):
        print(row)
        break
' "$PF_PIN_CODE")
		fi
		if [[ -z "$pin_row" ]]; then
			red_log "[-] pinned version code ${PF_PIN_CODE:-?} not found in a release variant row"
			return 2
		fi
		green_log "[+] pinned version code $PF_PIN_CODE found in release variant row"
		return 0
	fi
	if [[ "$variant_page_loaded" == false ]]; then
		variant_href=$(echo "$variant_href" | sed 's/&amp;/\&/g')
		green_log "[+] APKMirror variant page selected (URL withheld)"
	fi

	if [[ "$matched_type" == "BUNDLE" ]]; then
		base_apk="$apk_name.apkm"
	else
		base_apk="$apk_name.apk"
	fi

	if [[ "$variant_page_loaded" == false ]]; then
		_cf_get "$base_url$variant_href" || return 1
	fi

	local dl_btn_href
	local all_dl_btns
	all_dl_btns=$(echo "$html" | python3 ./src/build/html_select.py 'a.downloadButton attr{href}')
	if [[ "$matched_type" == "BUNDLE" ]]; then
		dl_btn_href=$(echo "$all_dl_btns" | grep -v 'forcebaseapk' | head -1)
		[[ -z "$dl_btn_href" ]] && dl_btn_href=$(echo "$all_dl_btns" | head -1)
	else
		dl_btn_href=$(echo "$all_dl_btns" | grep 'forcebaseapk' | head -1)
		[[ -z "$dl_btn_href" ]] && dl_btn_href=$(echo "$all_dl_btns" | head -1)
	fi

	if [[ -z "$dl_btn_href" ]]; then
		red_log "[-] Could not find download button"
		return 1
	fi
	dl_btn_href=$(echo "$dl_btn_href" | sed 's/&amp;/\&/g')

	_cf_get "$base_url$dl_btn_href" || return 1

	local final_href
	final_href=$(echo "$html" | python3 ./src/build/html_select.py 'a#download-link attr{href}' | head -1)
	[[ -z "$final_href" ]] && \
		final_href=$(echo "$html" | grep -oP 'id="download-link"[^>]*href="\K[^"]+' | head -1)

	if [[ -z "$final_href" ]]; then
		red_log "[-] Could not find final download link"
		return 1
	fi
	final_href=$(echo "$final_href" | sed 's/&amp;/\&/g')
	local final_url="$base_url$final_href"
	if declare -F pf_store_url_check >/dev/null 2>&1; then
		pf_store_url_check "$final_url" || { red_log "[-] APKMirror final URL failed HTTPS/host policy"; return 1; }
	fi

	# Do not print endpoint or redirected signed URLs; retain redacted diagnostics.
	local cookie_args=()
	[[ -n "$FS_COOKIES" ]] && cookie_args=(--header "Cookie: $FS_COOKIES")
	if ! PF_DIAG_DEST="$final_url" PF_DIAG_REFERER="$base_url$dl_btn_href" \
		PF_DIAG_COOKIES="$FS_COOKIES" PF_DIAG_UA="$user_agent" \
		python3 src/build/transfer_diagnostic.py handoff; then
		yellow_log "[!] Download diagnostic unavailable"
	fi
	# W15b (Photos, run 38643057188): wget -q hid why the transfer failed. Print wget's exit
	# code and its documented meaning (never the URL, headers or cookies), retry once.
	local wrc=0 try
	local output_base_apk="$base_apk" transfer_tmp="" transfer_path="./download/$base_apk"
	if [[ "${PF_ENFORCE_EFFECTIVE_URL:-0}" == "1" ]]; then
		transfer_tmp=$(mktemp "./download/.$base_apk.XXXXXX") || return 1
		transfer_path="$transfer_tmp"
	fi
	for try in 1 2; do
		wrc=0
		if [[ "$try" -eq 2 ]] && declare -F _cf_get >/dev/null 2>&1; then
			# W16v (27 Oct 2026). Refresh the download page so retry never reuses a stale link;
			# a failed refresh ends the attempt instead of retrying the old link.
			final_href=""; final_url=""
			if _cf_get "$base_url$dl_btn_href"; then
				cookie_args=()
				[[ -n "$FS_COOKIES" ]] && cookie_args=(--header "Cookie: $FS_COOKIES")
				final_href=$(echo "$html" | python3 ./src/build/html_select.py 'a#download-link attr{href}' | head -1)
				[[ -z "$final_href" ]] && final_href=$(echo "$html" | grep -oP 'id="download-link"[^>]*href="\K[^"]+' | head -1)
				if [[ -n "$final_href" ]]; then
					final_href=$(echo "$final_href" | sed 's/&amp;/\&/g')
					final_url="$base_url$final_href"
					if declare -F pf_store_url_check >/dev/null 2>&1; then
						pf_store_url_check "$final_url" || final_href=""
					fi
				fi
			fi
			[[ -n "$final_href" ]] || wrc=1
		fi
		if [[ "$wrc" -eq 0 && "${PF_ENFORCE_EFFECTIVE_URL:-0}" == "1" ]]; then
			pf_wget_store_transfer "$final_url" "$transfer_path" "$base_url$dl_btn_href" "$user_agent" || wrc=$?
		elif [[ "$wrc" -eq 0 ]]; then
			wget -q -O "./download/$base_apk" \
				--header="User-Agent: $user_agent" \
				--referer="$base_url$dl_btn_href" \
				"${cookie_args[@]}" \
				--timeout=120 \
				"$base_url$final_href" || wrc=$?
		fi
		if [[ "$wrc" -eq 0 ]]; then
			if [[ -n "$transfer_tmp" ]]; then mv -f -- "$transfer_tmp" "./download/$output_base_apk" || { rm -f -- "$transfer_tmp" "./download/$output_base_apk"; return 1; }; fi
			base_apk="$output_base_apk"
			break
		fi
		if [[ "${PF_ENFORCE_EFFECTIVE_URL:-0}" == "1" ]]; then
			echo "TRANSFER_FAILED store=apkmirror try=$try wget_exit=$wrc meaning=$(pf_wget_meaning "$wrc") bytes=$(stat -c %s "$transfer_path" 2>/dev/null || echo 0)"
		else
			echo "TRANSFER_FAILED store=apkmirror try=$try wget_exit=$wrc meaning=$(pf_wget_meaning "$wrc") bytes=$(stat -c %s "$transfer_path" 2>/dev/null || echo 0)"
		fi
		rm -f -- "$transfer_path"
		if [[ "$try" -eq 1 ]]; then
			sleep "${PF_TRANSFER_RETRY_WAIT:-20}"
			if [[ "${PF_ENFORCE_EFFECTIVE_URL:-0}" == "1" ]]; then
				transfer_tmp=$(mktemp "./download/.$output_base_apk.XXXXXX") || return 1
				transfer_path="$transfer_tmp"
			fi
		fi
	done
	if [[ "$wrc" -ne 0 ]]; then
		red_log "[-] APKMirror transfer failed; refusing partial or empty output"
		return 1
	fi

	if [[ -s "./download/$base_apk" ]]; then
		green_log "[+] Successfully downloaded $apk_name"
	else
		red_log "[-] Failed to download $apk_name"
		return 1
	fi

	# The qualified alternate consumer verifies original bytes/signatures before merging.
	if [[ "${PF_APK_RAW_ONLY:-0}" == "1" ]]; then return 0; fi
	if [[ "$matched_type" == "BUNDLE" ]]; then
		if [[ "$pkg_type" == "bundle_extract" && "$type_badge" == "BUNDLE" ]]; then
			unzip "./download/$base_apk" -d "./download/$(basename "$base_apk" .apkm)" > /dev/null 2>&1
		else
			green_log "[+] Merge splits apk to standalone apk"
			python3 src/build/split_list.py "./download/$apk_name.apkm"
			# W15b: this merge used to ignore its own failure (the APKPure path below never did).
			if ! java -jar $APKEditor m -i "./download/$apk_name.apkm" -o "./download/$apk_name.apk" > /dev/null 2>&1; then
				red_log "[-] Failed to merge $apk_name.apkm to standalone apk"
				return 1
			fi
		fi
	fi
}

get_apkpure() {
	local pkg_name=$1 apk_name=$2 pkg_type=${3:-apk}
	local html=""

	local apps_json="./src/build/helper/apps.json"
	local base_download_url
	base_download_url=$(jq -r --arg pkg "$pkg_name" '.apkpure[$pkg].download_url // empty' "$apps_json")

	if [[ -z "$base_download_url" ]]; then
		red_log "[-] Package $pkg_name not found in apps.json (apkpure)"
		return 1
	fi

	detect_version "$pkg_name"
	version=$(printf '%s\n' "$version" "$prefer_version" | sort -V | tail -n1)
	unset prefer_version
	export version

	if [[ "$pkg_type" == "bundle" ]] || [[ "$pkg_type" == "bundle_extract" ]]; then
		local base_apk="$apk_name.xapk"
	else
		local base_apk="$apk_name.apk"
	fi

	local dl_page_url
	if [[ -n "$version" ]]; then
		dl_page_url="${base_download_url%/}/$version"
	else
		dl_page_url="$base_download_url"
	fi

	green_log "[+] Downloading $apk_name from APKPure (type=$pkg_type)"
	green_log "[+] APKPure download page selected (URL withheld)"

	_cf_get "$dl_page_url" || return 1
	# Covers both resolver routes. Observation only: do not alter link selection.
	if ! printf '%s' "$html" | python3 src/build/transfer_diagnostic.py page; then
		yellow_log "[!] Download page diagnostic unavailable"
	fi

	local page_version
	page_version=$(echo "$html" | python3 ./src/build/html_select.py 'h2 text{}' | grep -oP '\d+(\.\d+)+' | head -1)
	if [[ -n "$page_version" ]]; then
		version="$page_version"
	fi
	green_log "[+] Version: $version"

	local download_url
	download_url=$(echo "$html" | python3 ./src/build/html_select.py 'a#download_link attr{href}' | head -1)
	[[ -z "$download_url" ]] && \
		download_url=$(echo "$html" | grep -oP '<a[^>]+id="download_link"[^>]+href="\Khttps://[^"]+' | head -1)

	if [[ -z "$download_url" ]]; then
		red_log "[-] Could not find download link on APKPure"
		printf '%s\n' 'DOWNLOAD_FAILURE {"source":"apkpure","stage":"link-extraction","reason":"missing-download-link","binary_transfer_started":false}'
		return 1
	fi
	if declare -F pf_store_url_check >/dev/null 2>&1; then
		pf_store_url_check "$download_url" || { red_log "[-] APKPure final URL failed HTTPS/host policy"; return 1; }
	fi
	if ! PF_DIAG_DEST="$download_url" PF_DIAG_REFERER="$dl_page_url" \
		PF_DIAG_COOKIES="$FS_COOKIES" PF_DIAG_UA="$user_agent" \
		python3 src/build/transfer_diagnostic.py handoff; then
		yellow_log "[!] Download diagnostic unavailable"
	fi

	local cookie_args=()
	[[ -n "$FS_COOKIES" ]] && cookie_args=(--header "Cookie: $FS_COOKIES")
	local output_base_apk="$base_apk" transfer_tmp="" transfer_path="./download/$base_apk"
	local crc=0
	if [[ "${PF_ENFORCE_EFFECTIVE_URL:-0}" == "1" ]]; then
		transfer_tmp=$(mktemp "./download/.$base_apk.XXXXXX") || return 1
		transfer_path="$transfer_tmp"
	fi
	# W16o: F-10, remove any stale destination before the bounded candidate transfer.
	rm -f -- "$transfer_path"
	if [[ "${PF_ENFORCE_EFFECTIVE_URL:-0}" == "1" ]]; then
		if pf_curl_store_transfer "$download_url" "$transfer_path" "$dl_page_url" "$user_agent" apkpure; then
			:
		else
			crc=$?
			echo "TRANSFER_FAILED store=apkpure curl_exit=$crc bytes=$(stat -c %s "$transfer_path" 2>/dev/null || echo 0)"
			rm -f -- "$transfer_path"
			red_log "[-] APKPure transfer failed; refusing partial or empty output"
			return 1
		fi
	else
		if ! wget -q -O "./download/$base_apk" \
			--header="User-Agent: $user_agent" \
			--referer="$dl_page_url" \
			"${cookie_args[@]}" \
			--timeout=120 \
			"$download_url"; then
			rm -f -- "$transfer_path"
			red_log "[-] APKPure transfer failed; refusing partial or empty output"
			return 1
		fi
	fi
	if [[ -n "$transfer_tmp" ]]; then
		mv -f -- "$transfer_path" "./download/$output_base_apk" || { rm -f -- "$transfer_path" "./download/$output_base_apk"; return 1; }
		base_apk="$output_base_apk"
	fi

	if [[ -s "./download/$base_apk" ]]; then
		green_log "[+] Successfully downloaded $apk_name"
	else
		rm -f -- "./download/$base_apk"
		red_log "[-] Failed to download $apk_name"
		return 1
	fi
	# Preserve the original signed container for qualified alternate verification.
	if [[ "${PF_APK_RAW_ONLY:-0}" == "1" ]]; then return 0; fi
	if [[ "$pkg_type" == "bundle" ]]; then
		if unzip -l "./download/$base_apk" '*.apk' > /dev/null 2>&1; then
			green_log "[+] Merge splits apk to standalone apk"
			python3 src/build/split_list.py "./download/$apk_name.xapk"
			if ! java -jar $APKEditor m -i "./download/$apk_name.xapk" -o "./download/$apk_name.apk" > /dev/null 2>&1; then
				red_log "[-] Failed to merge $apk_name.xapk to standalone apk"
				return 1
			fi
		elif unzip -l "./download/$base_apk" AndroidManifest.xml > /dev/null 2>&1; then
			green_log "[+] File is already a standalone APK, renaming"
			mv "./download/$base_apk" "./download/$apk_name.apk"
		else
			red_log "[-] Unknown file format for $base_apk"
			return 1
		fi
	elif [[ "$pkg_type" == "bundle_extract" ]]; then
		unzip "./download/$base_apk" -d "./download/$(basename "$base_apk" .xapk)" > /dev/null 2>&1
	fi
}

#################################################

# Patching apps with CLI:
# W15g: this legacy helper signed inside the patch job. Patching runs only through
# src/build/patch_target.py (unsigned); the release key exists only in the Sign job.
patch() {
	red_log "[-] legacy patch helper removed (W15g): use src/build/patch_target.py"
	return 1
}

# W15g: this legacy helper signed inside the patch job. Patching runs only through
# src/build/patch_target.py (unsigned); the release key exists only in the Sign job.
patch_multi() {
	red_log "[-] legacy patch_multi helper removed (W15g): use src/build/patch_target.py"
	return 1
}

npatch() {
	green_log "[+] Patching $1:"
	if [ -f "./download/$1.apk" ]; then
		local module
		if [[ "$2" == *.apk ]]; then
			local -a matches=($2)
			module="${matches[0]}"
		else
			module="$2.apk"
		fi
		if [[ ! -f "$module" ]]; then
			red_log "[-] Module not found: $2"
			return 1
		fi
		java -jar jar*.jar ./download/$1.apk -k ./src/fiorenmas.ks "fiorenmas" "morphe" "fiorenmas" $4 -m "$module" -o ./release/
		mv ./release/$1-*-npatched.apk ./release/$1-$3-npatched.apk
		unset version
		unset lock_version
	else
		red_log "[-] Not found $1.apk"
		exit 1
	fi
}
#################################################

split_editor() {
    if [[ -z "$3" || -z "$4" ]]; then
        green_log "[+] Merge splits apk to standalone apk"
        java -jar $APKEditor m -i "./download/$1" -o "./download/$1.apk" > /dev/null 2>&1
        return 0
    fi
    IFS=' ' read -r -a include_files <<< "$4"
    mkdir -p "./download/$2"
    for file in "./download/$1"/*.apk; do
        filename=$(basename "$file")
        basename_no_ext="${filename%.apk}"
        if [[ "$filename" == "base.apk" ]]; then
            cp -f "$file" "./download/$2/" > /dev/null 2>&1
            continue
        fi
        if [[ "$3" == "include" ]]; then
            if [[ " ${include_files[*]} " =~ " ${basename_no_ext} " ]]; then
                cp -f "$file" "./download/$2/" > /dev/null 2>&1
            fi
        elif [[ "$3" == "exclude" ]]; then
            if [[ ! " ${include_files[*]} " =~ " ${basename_no_ext} " ]]; then
                cp -f "$file" "./download/$2/" > /dev/null 2>&1
            fi
        fi
    done

    green_log "[+] Merge splits apk to standalone apk"
    java -jar $APKEditor m -i ./download/$2 -o ./download/$2.apk > /dev/null 2>&1
}

#################################################

archs=("arm64-v8a" "armeabi-v7a" "x86_64" "x86")
libs=("armeabi-v7a x86_64 x86" "arm64-v8a x86_64 x86" "armeabi-v7a arm64-v8a x86" "armeabi-v7a arm64-v8a x86_64")

# Remove unused architectures directly
apk_editor() {
	local apk="$1" keep="$2"; shift 2
	local dir="./download/$apk"
	rm -rf "$dir" && unzip -q "./download/$apk.apk" -d "$dir" || return 1
	for r in "$@"; do rm -rf "$dir/lib/$r"; done
	(cd "$dir" && zip -qr "../$apk-$keep.apk" .)
}

# Split architectures using Morphe cli
# W15g: this legacy helper signed inside the patch job. Patching runs only through
# src/build/patch_target.py (unsigned); the release key exists only in the Sign job.
split_arch() {
	red_log "[-] legacy split_arch helper removed (W15g): use src/build/patch_target.py"
	return 1
}

#################################################
