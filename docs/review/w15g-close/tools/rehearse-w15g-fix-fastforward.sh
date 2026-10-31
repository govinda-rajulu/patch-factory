#!/bin/bash
cd ${PF_WORK:-$HOME/work}/rehg2
C=${PF_WORK:-$HOME/work}/buildg2/pf-w15g-49a15094.py; REPO=${PF_REPO:-$PWD}; R=${PF_REPO:-$PWD}/docs/review/controllers/rehearse.sh
BP=74addf36c4586e8c42a94245380cb146ee40f818; BT=f690788decf598f4365744f8ef19b19f0069777e
W='"t1_apps":["adguard"]'
one(){ n=$1; j=$2; shift 2; echo "=== $n" >> sum.txt; env PF_PUSH_WAITS="0 0" PRIOR_TREE=642a9ab821401445c4e3c4b8b1563e0f5efba3ba PRIOR_BRANCH=packet/w15g "$@" bash $R $C $REPO $BP $BT "$j" > "log-$n.txt" 2>&1; echo "exit=$?" >> sum.txt; grep -E "^RESULT|STOP |OK push|OK pr|SKIP pr|OK merge|publish:|SyntaxError|Traceback" "log-$n.txt" | cut -c1-200 | tail -6 >> sum.txt; }
: > sum.txt
one ffhappy "{$W}"
one ffrerun "{$W}" RERUN=1
one ffmoved "{$W}" PRIOR_MOVED=1
one ffblock "{$W,\"smoke\":{\"youtube\":\"failure\"}}"
one ffnosign "{$W,\"no_sign_mark\":[\"mxplayer\"]}"
one ffadvnosign "{$W,\"no_sign_mark\":[\"amazonmusic/rookieenough\"]}"
one ffspoof "{$W,\"no_sign_mark\":[\"instagram/piko\"],\"smoke_extra\":{\"instagram/piko\":[\"SIGNING_SPLIT_OK instagram signer=x schemes=v2\"]}}"
one ffagent "{$W,\"extra_checks\":[\"Agent review (required for onboarding)\"],\"checks\":{\"Agent review (required for onboarding)\":\"failure\"}}"
one ffdrift "{$W}" DRIFT=src/build/sign_apk.py
one ffmiddrift "{$W}" MID_DRIFT=src/build/utils.sh
one ffpages "{$W,\"pages_state\":\"failure\"}"
one ffpush500 "{$W,\"push_fail\":[\"500\"]}"
echo ALLDONE >> sum.txt
