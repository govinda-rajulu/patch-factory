#!/bin/bash
# Local copy of 3. Validate's offline steps (no shellcheck, no action smoke).
cd "$1" || exit 9
F=0
run(){ if "$@" > /tmp/suite-step.log 2>&1; then echo "PASS $*"; else echo "FAIL $*"; tail -30 /tmp/suite-step.log; F=1; fi; }
run python3 src/etc/preflight.py
for p in test_repair.py test_identity.py test_transport.py '*_contracts.py' test_source_inputs.py; do run python3 -m unittest discover -s tests -p "$p"; done
run node tests/portal_contracts.cjs
run node tests/notify_contracts.cjs
run bash src/etc/bancheck.sh
run bash src/etc/quarantine.sh
run python3 src/etc/pagegen.py --check
run python3 src/etc/dropgen.py --check
run python3 src/etc/credits.py --check
run bash src/etc/orphans.sh
run python3 src/etc/schedules.py --check
run python3 src/etc/readmegen.py --check
run python3 src/etc/obtainium.py --check
run bash src/etc/nointerp.sh
for f in src/build/*.sh src/etc/*.sh; do bash -n "$f" || { echo "FAIL bash -n $f"; F=1; }; done
echo "SUITE $([ $F = 0 ] && echo OK || echo FAIL)"
exit $F
