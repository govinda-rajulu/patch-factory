# W15g packet: ZIP/APK scenario report

| ID | Shape | Expected | Actual | Result |
|---|---|---|---|---|
| L01 | descriptor/zero/dir/UTF8/CP437/.SO/compressed SO | accept | accept | PASS |
| L02 | ZIP64 / 65536 zero-length stored entries | accept | accept | PASS |
| L03 | v2-only block insertion; stale RSA/SF/MANIFEST unchanged; services/version compared | accept | accept | PASS |
| L04 | v1 replacement of stale signature files, appended and deflated | accept | accept | PASS |
| L05 | apksigner rewrites only local extra-field padding | accept | accept | PASS |
| B01 | changed entry bytes | refuse | refuse | PASS |
| B02 | changed method | refuse | refuse | PASS |
| B03 | CRC changed in local header only (data descriptor) | refuse | refuse | PASS |
| B04 | local header name differs from central directory | refuse | refuse | PASS |
| B05 | dropped non-signature entry | refuse | refuse | PASS |
| B06 | added non-signature entry | refuse | refuse | PASS |
| B07 | reordered entries | refuse | refuse | PASS |
| B08 | duplicate names | refuse | refuse | PASS |
| B09 | entry renamed by case only | refuse | refuse | PASS |
| B10 | META-INF/X.SF hides dex-like payload | refuse | accept | FINDING |
| B11 | META-INF/sub/x.RSA must not be excluded | refuse | refuse | PASS |
| B12 | lost 4-byte alignment | refuse | refuse | PASS |
| B13 | lost 16 KiB .so alignment | refuse | refuse | PASS |
| B14 | truncated entry | refuse | refuse | PASS |
| B15 | overlapping entries | refuse | refuse | PASS |
| J01 | non-signature META-INF/MANIFEST.MF changed | refuse | accept | FINDING |
| J02 | META-INF/SIG-* name | accept | accept | PASS |
| Z01 | zipalign -c 4 success and 16K preservation check | accept | accept | PASS |
| Z02 | zipalign -c 4 failure | refuse | refuse | PASS |

## Findings

### B10 — BLOCKER

- **Evidence:** `python3 -m unittest discover -s tests -p scenario_zip_contracts.py` → `no exception (accepted)`
- **Smallest fix:** Do not trust the filename regex alone: authenticate newly added signature files and reject unverified signature-like payloads.

### J01 — BLOCKER

- **Evidence:** `python3 -m unittest discover -s tests -p scenario_zip_contracts.py` → `no exception (accepted)`
- **Smallest fix:** Classify MANIFEST.MF by authenticated signing context; do not blanket-exclude arbitrary runtime-readable manifest payloads.

