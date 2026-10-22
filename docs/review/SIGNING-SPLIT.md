# Signing split design (W15g; owner yes 21 Oct 2026)

Goal: third-party patch code never runs where the release key or a write token is.

Today one job (1. Manual Patch, "Patch <app>") decodes the keystore, runs the patcher (which
executes provider code in the JVM with the keystore password on argv) and publishes with a
contents: write token.

Plan, three jobs:
1. **patch**: contents: read, no secrets. A throwaway BKS key made with keytool; identity, release
   contract and shadow observation as today, against the throwaway signer.
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
