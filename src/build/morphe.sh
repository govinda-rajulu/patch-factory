#!/bin/bash
# Morphe build
source ./src/build/utils.sh
# Download requirements
morphe_dl(){
 dl_gh "morphe-patches" "MorpheApp" "latest"
 dl_gh "morphe-desktop" "MorpheApp" "latest"
}
1() {
 morphe_dl
 # Patch YouTube, arm64-v8a only
 get_patches_key "youtube-morphe"
 get_apk "com.google.android.youtube" "youtube" "apk"
 # split_arch patches straight from ./download/youtube.apk
 for i in 0; do
 split_arch "youtube" "morphe"
 done
 # hand the version and tag prefix to the release action
 echo "$version" > ./release/.version
 echo "youtube-morphe" > ./release/.tagprefix
}
case "$1" in
 1)
 1
 ;;
esac
