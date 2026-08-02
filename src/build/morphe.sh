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
	# Patch YouTube arm64-v8a only:
	get_patches_key "youtube-morphe"
	get_apk "com.google.android.youtube" "youtube" "apk" "arm64-v8a"
	patch "youtube" "morphe"
}

2() {
	# Placeholder - no-op for matrix run=2
	:
}

3() {
	# Placeholder - no-op for matrix run=3
	:
}

case "$1" in
    1)
        1
        ;;
    2)
        2
        ;;
    3)
        3
        ;;
esac