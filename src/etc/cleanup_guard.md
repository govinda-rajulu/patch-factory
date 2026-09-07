# Cleanup rules

Learned the hard way on 7 Sep 2026, when an automated cleanup deleted `src/patches/_attic`.

## Never delete on "nothing references it" alone

`_attic` is an archive. Being unreferenced is its entire purpose, so that test deletes exactly
the thing the directory exists to hold. The same trap applies to `docs/review/`, `reference/`
and anything else kept for a human rather than for a build.

## The rule

A patch dir may be deleted only when **all** of these hold:

1. No target in `src/targets.json` names it as a `patch_dir`.
2. It is not under `src/patches/_attic/`.
3. Its `include-patches` is empty, so deleting it loses no decision.

Anything with content and no reference gets **reported, not deleted**. `3. Validate` prints
those as warnings. If you want one gone, delete it yourself, in a commit that says why.

## Restoring one

    git checkout <sha>~1 -- src/patches/<dir>

Git keeps everything, so a wrong delete costs a command, not a decision. That is not a reason
to be careless with it: a deleted include list is a lost judgement call, and nobody remembers
why a patch was excluded eight weeks later.
