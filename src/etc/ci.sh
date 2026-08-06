#!/bin/bash
# date of newest matching asset in a provider repo
provider_date() {
  local json; json=$(wget -qO- "https://api.github.com/repos/$1/releases")
  case "$2" in
    latest)     echo "$json" | jq -r 'first(.[] | select(.prerelease == false) | .assets[] | select(.name | test("\\.(jar|rvp|mpp)$")) | .updated_at)' ;;
    prerelease) echo "$json" | jq -r 'first(.[] | .assets[] | select(.name | test("\\.(jar|rvp|mpp)$")) | .updated_at)' ;;
    *)          echo "$json" | jq -r 'first(.[] | select(.tag_name == "'$2'") | .assets[] | select(.name | test("\\.(jar|rvp|mpp)$")) | .updated_at)' ;;
  esac
}
# date of newest matching asset in MY repo, any tag
mine_date() {
  wget -qO- --header="Authorization: token $GITHUB_TOKEN" \
    "https://api.github.com/repos/$repository/releases" \
    | jq -r 'first(.[] | .assets[] | select(.name | test("'"$1"'")) | .updated_at)'
}
d1=$(provider_date "$1" "$2")
d2=$(mine_date "$3")
echo "provider: ${d1:-none}   mine: ${d2:-none}"
if [ -z "$d1" ] || [ "$d1" = "null" ]; then
  echo "new_patch=0" >> $GITHUB_OUTPUT; echo "could not read provider, skipping"
elif [ -z "$d2" ] || [ "$d2" = "null" ] || [ "$(date -d "$d1" +%s)" -gt "$(date -d "$d2" +%s)" ]; then
  echo "new_patch=1" >> $GITHUB_OUTPUT; echo "New patch, building..."
else
  echo "new_patch=0" >> $GITHUB_OUTPUT; echo "Up to date, not building."
fi
