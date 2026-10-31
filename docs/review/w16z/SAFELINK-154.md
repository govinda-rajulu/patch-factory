# Council desk #154: the portal safeLink report, triaged (W16z, 31 Oct 2026)

Report: Council audit, shard `portal`, 7 Oct 2026 (issue #154, comment 6034523009), one seat each.
Checked against `docs/portal.js` on main `572d7d2b`. Verdict: **not reproducible; closed in writing.**

| Finding (as reported) | Code today | Result |
| --- | --- | --- |
| high: safeLink allows any github.com path for MicroG RE and Obtainium | `kind==='upstream'` returns the URL only when `u.href` equals `MICROG_WEB+'/releases'` or `OBTAINIUM_WEB+'/releases'` exactly | Not reproducible. A tag page or other path returns null (test `upstream links are exact`). |
| high: CI signing certificate exposed in portal JS, enabling forged imports | The value is the public certificate fingerprint every installed APK carries; Obtainium uses it to verify, it cannot sign anything | Not a secret; no change. |
| medium: download kind checks only `releases/download/` | Host must be exactly `github.com`, no port or credentials, path under `/govinda-rajulu/patch-factory/releases/download/` | Not reproducible: other repositories and look-alike hosts return null. |
| medium: run regex could be bypassed | `^/govinda-rajulu/patch-factory/actions/runs/[0-9]+(?:/job/[0-9]+)?$`, anchored at both ends; the repository name has no regex metacharacters | Not reproducible (test `run links are anchored`). |
| low: catch hides errors | Any parse error returns null, so the link is refused, never let through | Fail-closed by design. |

The 7 Oct test comment ("allows github.com.evil.invalid") misread the test: `tests/portal_contracts.cjs`
asserts that URL is refused. Two W16z tests pin the two cases above.

Credit: Anthropic Claude models, for Govindarajulu K.
