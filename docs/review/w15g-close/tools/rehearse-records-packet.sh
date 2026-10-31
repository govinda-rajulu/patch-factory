#!/bin/bash
cd ${PF_WORK:-$HOME/work}/rehc2
C=$(ls ${PF_WORK:-$HOME/work}/buildc2/pf-w15gc-????????.py | grep -v combo); REPO=${PF_REPO:-$PWD}; R=${PF_REPO:-$PWD}/docs/review/controllers/rehearse.sh
BP=3c8cc58; BT=2e483365ae7ee18fac5de32188eb0da9fb9bb9b1
W='"t1_apps":["adguard"]'
one(){ n=$1; j=$2; shift 2; echo "=== $n" >> sum.txt; env PF_PUSH_WAITS="0 0" "$@" bash $R $C $REPO $BP $BT "$j" > "log-$n.txt" 2>&1; echo "exit=$?" >> sum.txt; grep -E "^RESULT|STOP |OK merge|publish|smoke|Traceback|Error" "log-$n.txt" | cut -c1-200 | tail -5 >> sum.txt; }
: > sum.txt
one happy "{$W}"
one rerun "{$W}" RERUN=1
one push500 "{$W,\"push_fail\":[\"500\"]}"
one pushrej "{$W,\"push_fail\":[\"rejected\"]}"
one drift "{$W}" DRIFT=docs/review/OPEN-WORK.md
one botok "{$W}" DRIFT=docs/status.json
one middrift "{$W}" MID_DRIFT=knowledge/STATE.md
one pagesfail "{$W,\"pages_state\":\"failure\"}"
one valfail "{$W,\"checks\":{\"Validate targets and scripts\":\"failure\"}}"
echo ALLDONE >> sum.txt
