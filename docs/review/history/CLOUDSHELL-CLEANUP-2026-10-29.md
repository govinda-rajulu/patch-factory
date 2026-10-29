# Cloud Shell cleanup: 29 October 2026

The owner instruction was: **delete as much as possible, keep only what is needed**.

Two cleanup runs removed old build folders, logs, temporary files, and old source snapshots. The receipt byte totals below use MiB (receipt bytes divided by 1,048,576), rounded to two decimals; the headline totals are rounded to whole MB as requested.

## Deleted

| Run | Family | Items | MiB |
| --- | --- | ---: | ---: |
| 2026-10-28 23:19Z | home-level files | 27 | 3.75 |
|  | work directories | 61 | 445.98 |
|  | work files and archives | 67 | 10.38 |
|  | run logs | 280 | 415.49 |
| **Run total** |  | **435** | **875.60 (876 MB)** |
| 2026-10-28 23:25Z | archive directories | 100 | 1,407.97 |
|  | archive files | 153 | 76.16 |
| **Run total** |  | **253** | **1,484.13 (1,484 MB)** |

The first run freed 876 MB and the second freed 1,484 MB. The reported `/home` use fell from 81% to 27%.

## Kept material

The two keep folders retain only the cleanup receipts and archive lists, small evidence records, Git bundles, and a small number of worktree archives needed for review. No APKs, raw captures, cookies, keys, or live credentials are part of this history record.

## Review verdicts

- The one W2 Git bundle contains six commits. Its implementation and decisions are already recorded in the 8 October history and in the current source; it is not added again.
- The four older archive bundles contain previously merged work and rehearsal-only commits with no file changes. Their changes are already in the repository history; they are not added again.
- The worktree archives are old source snapshots or an empty source placeholder. Differences are version drift, generated files, unrelated source, or files already represented by repository history; none is a missing repository change.
- The evidence archives contain result records, pull-request notes, receipts, logs, JSON/TSV captures, and text records. They add no public-safe decision or result that is missing from the review history.

The keep folders are therefore review evidence only, not material to add to the repository.
