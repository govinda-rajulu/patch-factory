# Lesson proposals from W15g (31 Oct 2026)

Not in the ledger yet: docs/council/LESSONS.md takes owner-approved entries only. On the owner's yes, append these verbatim (numbers may shift if the ledger moved).

### L115 · A fake tool copies the real tool's output policy, and fixtures carry what real inputs carry
Tags: ci, evidence, tests
W15g's byte compare passed 3 review rounds, 13 rehearsals and a 9-case chain, then stopped 13 of 17
live smokes (wrong call 120): apksig never writes ZIP directory entries or the source-stamp file,
and every fake signer copied the APK whole while the fixtures had neither. Write a fake from the
real tool's source (what it keeps, drops and rewrites), give fixtures the shapes store APKs really
have, and reproduce the live failure with the old code before trusting the fix (13 of 13 real entry
lists replayed: 0 pass before, 13 after).

### L116 · An agent's fix is probed on the real data path before it is taken
Tags: review, evidence
A round-4 tester rated "tag date is patch-controlled" a BLOCKER and bound it to the job stamp. The
tag date is taken at build end, the stamp at job start, so any build across 00:00 UTC would have
been refused at publish. Re-rate agent findings and trace where the value is really produced before
patching; a fix that adds a new way to fail a legitimate run is rejected in writing.
