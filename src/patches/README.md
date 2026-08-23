# Patch selection standard

One rule for every target, no per-app judgement calls.

## BANNED

Lowercase substrings. No include list may contain a match. These patches break
installing an update in place, expose app data to other installed apps, or turn
the build into a different app wearing the same name. Substring matching is
deliberate: providers spell them differently and a name blocklist already let
two through.

## CONFIRM

Reported, never fatal. Hardware and device identity spoofing, plus resource
stripping patches that can break the app on an older phone. Each one needs an
explicit decision before it is used.

## EXCEPTIONS

`patch_dir|patch name|reason|date`. Matched exactly, not by substring. An
undocumented deviation is a bug.

## Gating

`exclusive: true` plus a non-empty include list makes build.sh refuse to publish
unless the applied count equals the list exactly. 16 of 17 targets.

`youtube` is the exception: it builds from provider defaults minus an exclude
list, so gating it means enumerating all 61 patch names. Known gap, not an
oversight.

## Enforcement

`src/etc/bancheck.sh`, run locally and by "3. Validate" on every push.
