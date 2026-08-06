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
 # Patch YouTube:
 get_patches_key "youtube-morphe"
 get_apk "com.google.android.youtube" "youtube" "apk"
 patch "youtube" "morphe"
 # Split to arm64-v8a only (archs[0])
 for i in 0; do
 split_arch "youtube" "morphe"
 done
}
case "$1" in
 1)
 1
 ;;
esac
