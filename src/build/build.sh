#!/bin/bash
# Generic per-target build.  Usage: build.sh <target-id>
# Reads src/targets.json, elects a provider, patches arm64-v8a, writes release metadata.
set -uo pipefail

ID="${1:?usage: build.sh <target-id>}"
TARGETS="src/targets.json"

# utils.sh is 29KB of upstream code written without `set -u`.
# Scope strictness off around every call into it; our own logic stays strict.
set +u; source ./src/build/utils.sh; set -u

version=""; lock_version=""; prefer_version=""
excludePatches=""; includePatches=""
KEYSTORE_PASS="${KEYSTORE_PASS:-}"; KEYSTORE_ALIAS="${KEYSTORE_ALIAS:-}"

# --- 1. target -------------------------------------------------------------
T=$(jq -c --arg id "$ID" '.[] | select(.id==$id)' "$TARGETS")
[ -n "$T" ] || { red_log "[-] no target '$ID' in $TARGETS"; exit 1; }
[ "$(jq -r '.enabled' <<<"$T")" = "true" ] || { red_log "[-] target '$ID' is disabled"; exit 1; }

PKG=$(jq      -r '.package'             <<<"$T")
APK_NAME=$(jq -r '.apk_name'            <<<"$T")
APK_TYPE=$(jq -r '.apk_type // "apk"'   <<<"$T")
CEIL=$(jq     -r '.min_sdk_ceiling // 29' <<<"$T")
SRC=$(jq -r '.source // "apkmirror"' <<<"$T")
ANYVER=$(jq -r '.any_version // false' <<<"$T")
PREFIX=$(jq   -r '.tag_prefix // .id'   <<<"$T")
EXCL=$(jq -r '.exclusive // false' <<<"$T")
green_log "[+] target=$ID package=$PKG apk=$APK_NAME tagprefix=$PREFIX"

# --- 2. tooling, then resolve ----------------------------------------------
set +u; dl_gh "morphe-desktop" "MorpheApp" "latest"; set -u
ls morphe-desktop-*.jar >/dev/null 2>&1 || { red_log "[-] morphe-desktop jar not downloaded"; exit 1; }

RES=$(bash ./src/build/resolve.sh "$ID"); RC=$?
echo "$RES"
[ "$RC" -eq 0 ] || { red_log "[-] resolve.sh failed for $ID"; exit 1; }

WINNER=$(sed -n 's/^WINNER=//p'  <<<"$RES" | tail -1)
RVER=$(sed   -n 's/^VERSION=//p' <<<"$RES" | tail -1)
MPP=$(sed    -n 's/^MPP=//p'     <<<"$RES" | tail -1)
[ -n "$WINNER" ] || { red_log "[-] no WINNER line in resolve.sh output"; exit 1; }

C=$(jq -c --arg n "$WINNER" '.candidates[] | select(.name==$n)' <<<"$T")
[ -n "$C" ] || { red_log "[-] winner '$WINNER' is not a candidate of $ID"; exit 1; }
PDIR=$(jq  -r '.patch_dir' <<<"$C")
OPTS=$(jq  -r '.options'   <<<"$C")
OWNER=$(jq -r '.owner'     <<<"$C")
REPO=$(jq  -r '.repo'      <<<"$C")
CHAN=$(jq  -r '.channel'   <<<"$C")
green_log "[+] winner=$WINNER ($OWNER/$REPO $CHAN) app=$RVER patches=$PDIR options=$OPTS"

# split_arch globs `-p *.mpp` in the cwd, so exactly one must be present
rm -f ./*.mpp
set +u; dl_gh "$REPO" "$OWNER" "$CHAN"; set -u
if ! ls ./*.mpp >/dev/null 2>&1; then
  if [ -n "$MPP" ] && [ -f "$MPP" ]; then
    yellow_log "[!] no .mpp asset on $OWNER/$REPO, falling back to resolver cache: $MPP"
    cp "$MPP" ./
  fi
fi
# --- 2b. extra bundles, numbered so glob order is ours ----------------------
WANT=1
FIRST=$(ls ./*.mpp 2>/dev/null | head -1)
[ -n "$FIRST" ] || { red_log "[-] no winner bundle in cwd"; exit 1; }
PV=$(basename "$FIRST" .mpp | grep -oE '[0-9]+([.][0-9]+)+' | tail -1)
echo "PV=${PV:-unknown}"
mv "$FIRST" "./09-$WINNER.mpp"
green_log "[+] bundle 09 $WINNER $(wc -c < "./09-$WINNER.mpp") bytes"
EJ=0
while IFS= read -r E; do
  [ -n "$E" ] || continue
  EJ=$((EJ+1))
  EH=$(jq -r '.host // "github"' <<<"$E")
  ENM=$(jq -r '.name' <<<"$E")
  ECH=$(jq -r '.channel // "prerelease"' <<<"$E")
  if [ "$EH" = "gitlab" ]; then
    EID=$(jq -r '.project_id' <<<"$E")
  else
    EID="$(jq -r '.owner' <<<"$E")/$(jq -r '.repo' <<<"$E")"
  fi
  EK=$(printf "%02d" "$EJ")
  FB=$(bash ./src/build/fetch_bundle.sh "$EH" "$EID" "$ECH" "./$EK-$ENM.mpp" 2>&1) || { red_log "[-] extra bundle $ENM failed: $FB"; exit 1; }
  green_log "[+] bundle $EK $ENM $(sed -n "s/^TAG=//p" <<<"$FB") $(sed -n "s/^SIZE=//p" <<<"$FB") bytes"
  WANT=$((WANT+1))
done < <(jq -c '(.extra_bundles // [])[]' <<<"$T")
N=$(ls ./*.mpp 2>/dev/null | wc -l)
[ "$N" -eq "$WANT" ] || { red_log "[-] need exactly $WANT .mpp in cwd, found $N"; ls ./*.mpp 2>/dev/null; exit 1; }
green_log "[+] patch bundle: $(ls ./*.mpp)"

# --- 3. patch selection ----------------------------------------------------
[ -d "src/patches/$PDIR" ]      || { red_log "[-] missing src/patches/$PDIR"; exit 1; }
INC="src/patches/$PDIR/include-patches"
EXC="src/patches/$PDIR/exclude-patches"
if [ ! -s "$INC" ] && [ ! -s "$EXC" ]; then
 red_log "[-] src/patches/$PDIR has no selections at all - refusing to build an unpatched apk"
 exit 1
fi
[ -f "src/options/$OPTS.json" ] || { red_log "[-] missing src/options/$OPTS.json"; exit 1; }
set +u; get_patches_key "$PDIR"; set -u
# --- 3b. one bundle stays in cwd, the rest become extra -p flags ------------
mkdir -p ./extra
EXTRA_P=""
for M in $(ls ./*.mpp | sort | tail -n +2); do
  BN=$(basename "$M")
  mv "$M" "./extra/$BN"
  EXTRA_P="$EXTRA_P -p ./extra/$BN"
done
SELO=$(bash ./src/build/selections.sh "$ID" "$WINNER") || { red_log "[-] selections.sh failed"; exit 1; }
WANT_E=$(sed -n 's/^WANT=//p' <<<"$SELO")
SEL=$(sed -n 's/^SEL=//p' <<<"$SELO")
if [ "$EXCL" = "true" ]; then
  [ "${WANT_E:-0}" -gt 0 ] || { red_log "[-] exclusive needs a non-empty include list"; exit 1; }
  excludePatches=" --exclusive$SEL"
  green_log "[+] exclusive on, expecting $WANT_E patches"
else
  excludePatches="$SEL"
fi
includePatches=""
NC=$(ls ./*.mpp 2>/dev/null | wc -l)
[ "$NC" -eq 1 ] || { red_log "[-] want 1 .mpp in cwd, found $NC"; exit 1; }
green_log "[+] primary bundle: $(ls ./*.mpp)"
green_log "[+] extra -p flags:$EXTRA_P"

# --- 4. apk ----------------------------------------------------------------
version="$RVER"
if [ "$ANYVER" = "true" ]; then version=""; lock_version=1; yellow_log "[!] any_version on, taking the store latest"; fi
if [ "$SRC" = "apkpure" ]; then
  set +u; get_apkpure "$PKG" "$APK_NAME" "$APK_TYPE"; GA=$?; set -u
else
near_version=1
set +u; get_apk "$PKG" "$APK_NAME" "$APK_TYPE"; GA=$?; set -u
fi
[ "$GA" -eq 0 ] || { red_log "[-] get_apk failed for $PKG"; exit 1; }
[ -f "./download/$APK_NAME.apk" ] || { red_log "[-] ./download/$APK_NAME.apk missing"; exit 1; }
SZ=$(wc -c < "./download/$APK_NAME.apk")
green_log "[+] downloaded $SZ bytes"
[ "$SZ" -gt 1000000 ] || { red_log "[-] only $SZ bytes, download did not complete"; head -c 200 "./download/$APK_NAME.apk"; exit 1; }
unzip -l "./download/$APK_NAME.apk" > /dev/null 2>&1 || { red_log "[-] not a zip, apkmirror served an error page or the wrong variant"; head -c 200 "./download/$APK_NAME.apk"; exit 1; }
unzip -l "./download/$APK_NAME.apk" | grep -q AndroidManifest.xml || { red_log "[-] zip has no AndroidManifest.xml, not an apk"; exit 1; }
PKG_SEEN=""
if command -v aapt2 > /dev/null 2>&1; then
  PKG_SEEN=$(aapt2 dump packagename "./download/$APK_NAME.apk" 2>/dev/null | head -1)
fi
if [ -z "$PKG_SEEN" ] && command -v apkanalyzer > /dev/null 2>&1; then
  PKG_SEEN=$(apkanalyzer manifest application-id "./download/$APK_NAME.apk" 2>/dev/null | head -1)
fi
if [ -z "$PKG_SEEN" ]; then
  if [ "$(unzip -p "./download/$APK_NAME.apk" AndroidManifest.xml 2>/dev/null | tr -d '\000' | grep -cF "$PKG")" != "0" ]; then
    PKG_SEEN="$PKG"
  fi
fi
if [ -z "$PKG_SEEN" ]; then
  yellow_log "[!] UNVERIFIED - could not read a package name from the downloaded apk"
elif [ "$PKG_SEEN" != "$PKG" ]; then
  red_log "[-] package mismatch: apk is $PKG_SEEN, target wants $PKG"; exit 1
else
  green_log "[+] package confirmed $PKG_SEEN"
fi
green_log "[+] apk verified"

# --- 4b. version backfill: any_version clears $version, tags need it back ---
if [ -z "$version" ]; then
  VN=""
  if command -v aapt2 > /dev/null 2>&1; then
    VN=$(aapt2 dump badging "./download/$APK_NAME.apk" 2>/dev/null | tr " " "\n" | sed -n "s/^versionName=//p" | tr -d "'" | head -1)
  fi
  if [ -z "$VN" ] && command -v apkanalyzer > /dev/null 2>&1; then
    VN=$(apkanalyzer manifest version-name "./download/$APK_NAME.apk" 2>/dev/null | head -1)
  fi
  [ -n "$VN" ] || { red_log "[-] version is empty and unreadable from the apk - refusing to build a release nothing can tag"; exit 1; }
  version="$VN"
  green_log "[+] version read from apk: $version"
fi
# --- 5. sdk gate, report only ----------------------------------------------
bash ./src/build/check_sdk.sh "./download/$APK_NAME.apk" "$CEIL" 2>&1 \
  | sed 's/::error::/::warning::/'

# --- 6. patch, arm64-v8a is archs[0] ---------------------------------------
for i in 0; do
  set +u; split_arch "$APK_NAME" "$OPTS" > /tmp/patch.log 2>&1; SA=$?; set -u
 cat /tmp/patch.log
 AP=$(grep -c "Applied: " /tmp/patch.log)
 green_log "[+] applied $AP patches (rc=$SA)"
 grep "Applied: " /tmp/patch.log | sed 's/.*Applied: /- /' | sort > ./release/.applied
 if [ "$EXCL" = "true" ] && [ "$AP" != "$WANT_E" ]; then
  red_log "[-] applied $AP but include list says $WANT_E - refusing to release"
  grep "Skipping disabled" /tmp/patch.log | head -30; exit 1
 fi
done

# --- 7. release metadata ---------------------------------------------------
echo "$version" > ./release/.version
echo "$PREFIX"  > ./release/.tagprefix
for A in ./release/*-arm64-v8a.apk; do
  [ -f "$A" ] || continue
  B=$(basename "$A"); NB="${B%-arm64-v8a.apk}-v$version-arm64-v8a.apk"
  case "$B" in *-v$version-*) continue ;; esac
  mv "$A" "./release/$NB" && green_log "[+] renamed $B -> $NB"
done
echo "-b$(date -u +%Y%m%d)" > ./release/.tagsuffix
echo "${PV:-unknown}" > ./release/.patchver
PROV=""
for M in ./*.mpp ./extra/*.mpp; do
  [ -f "$M" ] || continue
  NM=$(basename "$M" .mpp | sed 's/^[0-9]*-//')
  case " $PROV " in *" $NM "*) continue ;; esac
  PROV="${PROV:+$PROV + }$NM"
done
[ -n "$PROV" ] || PROV="$WINNER"
echo "$PROV" > ./release/.provider
green_log "[+] providers: $PROV"
green_log "[+] release tag: $PREFIX-v$version$(cat ./release/.tagsuffix)"

# --- 8. assert -------------------------------------------------------------
COUNT=$(ls ./release/*.apk 2>/dev/null | wc -l)
[ "$COUNT" -ge 1 ] || { red_log "[-] no APK produced in ./release/"; ls -la ./release/; exit 1; }
green_log "[+] $COUNT APK(s) built"
ls -la ./release/
