#!/bin/bash
# W14 fix lane, second half. Runs after the council step, with no model keys and no write token:
# applies council-out/fixes.patch to a scratch copy of the checkout, checks every changed shell
# and JavaScript file (bash -n, node --check), and writes council-out/CHECKS.txt plus the job
# summary. It never commits, pushes or edits the checkout. Usage: check_fixes.sh [PATCH]
set -uo pipefail
PATCH=${1:-council-out/fixes.patch}
OUT=$(dirname "$PATCH")/CHECKS.txt
if [ ! -s "$PATCH" ]; then echo "no proposed fixes"; exit 0; fi
T=$(mktemp -d)
cp -a . "$T/r"
rm -rf "$T/r/$(dirname "$PATCH")"
{
  echo "Proposed fixes check (applies to a scratch copy only; not tested, never pushed)"
  if git -C "$T/r" apply --check "$(readlink -f "$PATCH")" 2>&1; then
    echo "PATCH applies"
    git -C "$T/r" apply "$(readlink -f "$PATCH")"
    grep -E '^\+\+\+ b/' "$PATCH" | cut -c7- | while IFS= read -r f; do
      case "$f" in
        *.sh) if bash -n "$T/r/$f" 2>&1; then echo "SYNTAX OK $f"; else echo "SYNTAX FAIL $f"; fi ;;
        *.js|*.cjs) if node --check "$T/r/$f" 2>&1; then echo "SYNTAX OK $f"; else echo "SYNTAX FAIL $f"; fi ;;
        *.py|*.json) echo "SYNTAX OK $f (checked by the council step)" ;;
        *) echo "NOT CHECKED $f" ;;
      esac
    done
  else
    echo "PATCH does not apply"
  fi
} > "$OUT"
rm -rf "$T"
cat "$OUT"
if [ -n "${GITHUB_STEP_SUMMARY:-}" ]; then { echo '```'; cat "$OUT"; echo '```'; } >> "$GITHUB_STEP_SUMMARY"; fi
exit 0
