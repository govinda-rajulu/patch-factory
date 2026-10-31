#!/bin/bash
cd ${PF_WORK:-$HOME/work}/rehg
C=$(ls ${PF_WORK:-$HOME/work}/buildg/pf-w15g-????????.py | grep -v combo); REPO=${PF_REPO:-$PWD}; R=${PF_REPO:-$PWD}/docs/review/controllers/rehearse.sh
BP=74addf36c4586e8c42a94245380cb146ee40f818; BT=f690788decf598f4365744f8ef19b19f0069777e
W='"t1_apps":["adguard"]'
one(){ n=$1; j=$2; shift 2; echo "=== $n" >> sum.txt; env PF_PUSH_WAITS="0 0" "$@" bash $R $C $REPO $BP $BT "$j" > "log-$n.txt" 2>&1; echo "exit=$?" >> sum.txt; echo "results=$(grep -c '^RESULT' log-$n.txt)" >> sum.txt; grep -E "^RESULT|STOP |NOTE push|publish|SyntaxError|SIGNING_SPLIT" "log-$n.txt" | cut -c1-220 | tail -6 >> sum.txt; }
: > sum.txt
one happy "{$W}"
one rerun "{$W}" RERUN=1
one push500 "{$W,\"push_fail\":[\"500\"]}"
one pushrej "{$W,\"push_fail\":[\"rejected\"]}"
one agent "{$W,\"extra_checks\":[\"Agent review (required for onboarding)\"],\"checks\":{\"Agent review (required for onboarding)\":\"failure\"}}"
one advfail "{$W,\"smoke\":{\"amazonmusic/rookieenough\":\"failure\"}}"
one blockfail "{$W,\"smoke\":{\"telegram/rahul9999xda\":\"failure\"}}"
one nosign "{$W,\"no_sign_mark\":[\"hotstar\"]}"
one spoof "{$W,\"no_sign_mark\":[\"edge\"],\"smoke_extra\":{\"edge\":[\"SIGNING_SPLIT_OK edge signer=x schemes=v2\"]}}"
one advnosign "{$W,\"no_sign_mark\":[\"amazonmusic/rookieenough\"]}"
one drift "{$W}" DRIFT=src/build/sign_apk.py
one middriftpkt "{$W}" MID_DRIFT=src/build/utils.sh
one pagesfail "{$W,\"pages_state\":\"failure\"}"

one cancel "{$W,\"smoke\":{\"youtube\":\"cancelled\"}}"
one combofail "{$W,\"smoke\":{\"truecaller-combo\":\"failure\"}}"
one esnosign "{$W,\"no_sign_mark\":[\"esfile/rushiranpise-fallback\"]}"
one twofail "{$W,\"smoke\":{\"edge\":\"failure\",\"photos\":\"timed_out\"}}"
echo ALLDONE >> sum.txt
