#!/bin/bash
# Rehearse a built controller against fake_gh.py. Usage:
#   rehearse.sh CONTROLLER.py REPO_DIR BASE_PARENT BASE_TREE ['{"state":"overrides"}']
# REPO_DIR holds BASE_PARENT; a fake base commit (BASE_TREE on BASE_PARENT) stands in for main.
# RERUN=1 runs the controller a second time in the same world (a rerun must change nothing).
set -e
C=$(readlink -f "$1"); REPO=$(readlink -f "$2"); HERE=$(dirname "$(readlink -f "$0")")
W=$(mktemp -d); mkdir -p "$W/home" "$W/bin"
git clone -q --bare "$REPO" "$W/origin.git"
B=$(cd "$W/origin.git" && GIT_AUTHOR_NAME=g GIT_AUTHOR_EMAIL=g@x GIT_COMMITTER_NAME=g GIT_COMMITTER_EMAIL=g@x git commit-tree "$4" -p "$3" -m base)
git -C "$W/origin.git" update-ref refs/heads/main "$B"
for r in $(git -C "$W/origin.git" for-each-ref --format='%(refname)' refs/heads | grep -v '^refs/heads/main$'); do git -C "$W/origin.git" update-ref -d "$r"; done
cp "$HERE/fake_gh.py" "$W/bin/gh"; chmod +x "$W/bin/gh"
# cleanup.py reads tags with git ls-remote; answer with one tag, pass everything else to git.
printf '#!/bin/bash\nif [ "$1" = ls-remote ] && [ "$2" = --tags ]; then printf "%%s\\trefs/tags/adguard-v1.0-b20260901\\n" 0000000000000000000000000000000000000001; exit 0; fi\nexec %s "$@"\n' "$(command -v git)" > "$W/bin/git"; chmod +x "$W/bin/git"
# PRIOR_TREE=TREE PRIOR_BRANCH=NAME: a packet already pushed (a commit of TREE on the fake main)
# with an open pull request #900; the controller gets PF_PARENT and must fast-forward it.
P=""; if [ -n "${PRIOR_TREE:-}" ]; then P=$(cd "$W/origin.git" && GIT_AUTHOR_NAME=g GIT_AUTHOR_EMAIL=g@x GIT_COMMITTER_NAME=g GIT_COMMITTER_EMAIL=g@x git commit-tree "$PRIOR_TREE" -p "$B" -m prior); git -C "$W/origin.git" update-ref "refs/heads/$PRIOR_BRANCH" "$P"; export PF_PARENT="$P"; fi
# PRIOR_MOVED=1: someone pushed on top of the prior head; the controller must stop at push.
if [ -n "$P" ] && [ -n "${PRIOR_MOVED:-}" ]; then M2=$(cd "$W/origin.git" && GIT_AUTHOR_NAME=g GIT_AUTHOR_EMAIL=g@x GIT_COMMITTER_NAME=g GIT_COMMITTER_EMAIL=g@x git commit-tree "$PRIOR_TREE" -p "$P" -m moved); git -C "$W/origin.git" update-ref "refs/heads/$PRIOR_BRANCH" "$M2"; fi
# MIRROR_REPO=DIR: a second repository for the W13 mirror phase (fake openskip).
if [ -n "${MIRROR_REPO:-}" ]; then git clone -q --bare "$MIRROR_REPO" "$W/mirror.git"; fi
python3 -c "import json,sys; s={'origin':sys.argv[1],'main':sys.argv[2],'runs':[],'pulls':[],'mirror_origin':sys.argv[5]}; s['pulls']=[{'number':900,'head':{'sha':sys.argv[6],'ref':sys.argv[7]},'merged_at':None,'html_url':'u','state':'open'}] if sys.argv[6] else []; s.update(json.loads(sys.argv[3])); open(sys.argv[4],'w').write(json.dumps(s))" "$W/origin.git" "$B" "${5:-{\}}" "$W/state.json" "$W/mirror.git" "$P" "${PRIOR_BRANCH:-}"
for pass in 1 ${RERUN:+2}; do
  echo "-- run $pass"; cp "$C" "$W/home/"
  (cd "$W/home" && PATH="$W/bin:$PATH" FAKE_STATE="$W/state.json" PF_HOME="$W/home" PF_REMOTE="$W/origin.git" PF_BASE="$B" PF_POLL=0 PF_WAIT=5 PF_BUILD_WAIT=5 PF_PAGES_WAIT=5 PF_MIRROR_REMOTE="$W/mirror.git" PF_MIRROR_QUIET=1 python3 "$W/home/$(basename "$C")") || true
done
echo "world: $W"
