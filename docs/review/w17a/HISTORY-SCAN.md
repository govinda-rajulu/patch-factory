# History scan: credentials and personal data (W17a, 31 Oct 2026)

Result: **0 real secrets, 0 real personal data.** Nothing to rewrite in history.

## Scope

- All 54 refs of a `git bundle --all` of main `b1c34e50`, 567 unique commits.
- Every commit compared with its first parent (root against the empty tree), merges included.
- 6121 text patches read, 73 binary diffs skipped.
- Read-only. No ref or file changed.

## Checks

GitHub token prefixes, AWS key ids, Google API keys, Slack tokens, JWTs, PEM private-key blocks,
credential assignments and keystore passwords, base64 over 200 characters, email addresses,
phone patterns, IPv4/IPv6, `/home/<name>` paths, two-word names in credit and author fields.

## Counts

| Type | False positive | Public by design | Flagged real | Total |
|---|---:|---:|---:|---:|
| IP address | 2220 | 0 | 0 | 2220 |
| phone number | 2814 | 0 | 132 | 2946 |
| personal name | 211 | 369 | 14 | 594 |
| email address | 44 | 9 | 6 | 59 |
| base64 over 200 chars | 15 | 1 | 0 | 16 |
| GitHub token | 6 | 0 | 0 | 6 |
| credential assignment | 5 | 0 | 0 | 5 |
| Cloud Shell home path | 0 | 0 | 5 | 5 |
| private key | 0 | 4 | 0 | 4 |
| AWS, Google, Slack, JWT, keystore | 0 | 0 | 0 | 0 |
| **Total** | **5315** | **383** | **157** | **5855** |

## Re-rating of the 157 flagged rows (checked by hand against the code)

| Flag | Rows | What it really is | Disposition |
|---|---:|---|---|
| phone number | 131 | GitHub run and job ids in records | keep, public ids |
| phone number | 1 | version code inside an APKMirror URL | keep, public |
| email | 2 | the github-actions bot noreply address in `rehearse.sh` | keep, public |
| email | 4 | the `x-access-token:%s@github.com` format string in two watchers | keep, no value |
| personal name | 14 | owner and upstream credits | keep, credit by design |
| home path | 5 | the owner's old Cloud Shell username in 2 dated patch lists, history only (not on main) | keep, decided in W16y-a |

The 6 token-shaped strings and 4 private-key blocks are test fixtures for the log redactor
(`tests/combo_contracts.py`, `tests/status_contracts.py`): short fake values such as `LEAKEDKEY`.

## Limits

- Pattern and context based. It cannot tell whether a credential is live, and no external service was asked.
- Missed by design: single-word names, names without a credit context, values inside images or binaries.
- Only refs in the bundle. Forks and deleted refs outside it are not covered.
- The full per-row table (about 5800 rows, values redacted) stays out of the repo; this summary is the record.

Scan by a review agent; re-rating by hand. Engineering: Anthropic Claude models, Google Cloud Shell, GitHub.
