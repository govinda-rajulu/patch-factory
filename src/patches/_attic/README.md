# Attic

Patch directories no longer referenced by any target in `src/targets.json`.

Kept, not deleted: several were curated by hand and a future target may want
them back. `bancheck.sh` and `namecheck.sh` skip anything under a `_` prefix,
so nothing here is scanned or validated.

To revive one: `git mv src/patches/_attic/NAME src/patches/NAME` and add a
`patch_dir` reference in `targets.json`.
