# Signing split design (W15g; owner yes 21 Oct 2026)

Goal: third-party patch code never runs where the release key or a write token is.

Today one job (1. Manual Patch, "Patch <app>") decodes the keystore, runs the patcher (which
executes provider code in the JVM with the keystore password on argv) and publishes with a
contents: write token.

Plan, three jobs:
1. **patch**: contents: read, no secrets. A throwaway BKS key made with keytool; identity, release
   contract and shadow observation as today, against the throwaway signer. *(Superseded by W15h
   below and built that way in W15g: no key at all, the patcher writes an unsigned APK.)*
2. **sign**: release key only, first-party code only. Re-sign with apksigner (v1, v2, v3), prove
   every entry except META-INF signature files is byte-identical to the patch job's APK, check the
   signer is the CI certificate, update the identity report (unsigned and signed records).
3. **publish**: contents: write, no key. Release action as today.

Found 22 Oct while building it (why it is its own packet): the shadow publication receipt
(`shadow_inputs.publish_receipt`) re-reads the consumed files after publication: the patcher jar,
the bundles, the input APK (up to 330 MB) and the request ledger, all of which exist only in the
patch job. W15g moves the receipt draft into the patch job (sealed, bound to the unsigned APK) and
lets the publish job finish it with the signing record (unsigned sha -> signed sha), so no
evidence check is weakened (L061). Gate: a full nonpublishing batch of every app through all
three jobs before merge, then one publishing build of a small app.

## W15h note (22 Oct 2026): the patcher can now skip signing

morphe-desktop 1.19.0 (22 Oct, Patcher 2.0) has `--unsigned` ("Disable signing of the final apk",
commit 4505091). The patch job can therefore produce an unsigned APK with no keystore at all, and
the sign job runs `apksigner` alone; no throwaway BKS key is needed. Check in the W15g rehearsal:
the unsigned output is zipaligned and `apksigner verify` passes after signing; the Obtainium
certificate pin (`src/build/ci-signer.json`) must still match the signed APK.

## Built in W15g (31 Oct 2026)

Implemented as designed, with the W15h `--unsigned` patch job (no throwaway key). Two findings
while building it: a fallback or override build runs with `src/targets.json` pinned to the winning
candidate, so the hand-off carries that file and the Sign and Publish jobs accept it only as the
checkout's own bytes or exactly that candidate's view; and current apksigner defaults would add v3,
a v4 `.idsig` and a 16 KiB realign, so the Sign job passes the patcher's own scheme rule (v2 only at
minimum SDK 24 and up, else v1 v2 v3; never v4) and `--alignment-preserved true`. Record:
[HANDOVER-2026-10-31-W15g.md](HANDOVER-2026-10-31-W15g.md).
