#!/bin/bash
# Is GitHub reachable? Nothing more. This used to download one hardcoded asset
# (patches-1.21.1.mpp from Feb 2026); the day upstream deletes that release, every
# build in the repo reports "connection not stable" and skips. Ask the API instead.
check_connection() {
  local code
  code=$(curl -s -o /dev/null -w '%{http_code}' --max-time 20 \
         ${GITHUB_TOKEN:+-H "Authorization: token $GITHUB_TOKEN"} \
         "https://api.github.com/rate_limit")
  if [ "$code" = "200" ]; then
    echo "internet_error=0" >> $GITHUB_OUTPUT
    echo -e "\e[32mGithub connection OK (rate_limit 200)\e[0m"
  else
    echo "internet_error=1" >> $GITHUB_OUTPUT
    echo -e "\e[31mGithub connection not stable! rate_limit returned $code\e[0m"
  fi
}
check_connection
