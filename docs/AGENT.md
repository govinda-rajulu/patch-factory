# A guardrailed agent for this repo

The job is narrow and real: **watch every patch provider, notice what changed, and propose a
selection change.** That is judgement over a small amount of text, on a schedule, and it is the
one task in this repo a human keeps forgetting to do.

## The only architecture that is safe here

    provider releases  ->  agent reads  ->  opens a PULL REQUEST  ->  3. Validate runs  ->  you merge

The agent never pushes to `main`. It has no keystore access, cannot dispatch a build, and cannot
publish a release. Every gate this repo already has becomes its test suite, and the PR diff is
the review surface. If the agent is wrong, the cost is a closed PR.

Set **Settings, Actions, General, Allow GitHub Actions to create and approve pull requests**, and
give the agent a token with `contents: write` and `pull-requests: write` on this repo only. Never
`workflow: write`: an agent that can edit `.github/workflows` can edit its own guardrails.

## What it may decide, and what it may not

| May propose in a PR | Must never touch |
|---|---|
| Add or remove a patch name in an `include-patches` file | `src/patches/BANNED`, `CONFIRM`, `QUARANTINE` |
| Raise or lower `max_patch_age_days` on one target | Anything in `.github/workflows/` |
| Add a provider as an `extra_bundles` entry | `src/build/TOOLING.sha256` |
| Open an issue describing a provider that went quiet | The keystore, the secrets, the release action |
| Update a `note` field with a dated reason | `LICENSE`, `SECURITY.md`, `CREDITS.md` |

A PR that touches a "never" column file should be closed unread. Add that as a CODEOWNERS rule
so it cannot be merged by accident.

## Which model, on a free tier

You will be on free tiers, so pick for the shape of the work, not the benchmark score.

- **Google Jules** (jules.google.com) is the closest fit to what you described. It clones the
  repo into a cloud VM, plans, edits multiple files, runs commands, and opens a PR. Free tier is
  15 tasks per rolling 24 hours, 3 concurrent. PR-only by design, which is exactly the guardrail
  above. Start here.
- **GitHub Copilot** free tier is chat and completions, not an autonomous repo agent; the cloud
  agent that opens PRs is on the paid plans. Fine as a reviewer on a PR, not as the driver.
- **Gemini CLI** is what you already have in Cloud Shell. Note that as of mid-2026 unpaid access
  is being moved to Antigravity CLI, so treat its free tier as unstable. It also cannot run shell
  commands in your environment, which is why every gate in this repo is shell you run yourself.
- **Anything self-hosted** is not worth it. The task is a few thousand tokens of provider
  changelog per week. Free hosted quota covers it many times over.

Verify the current free limits yourself before you rely on any of them; they move constantly and
whatever this file says will age.

## The context the agent needs

Do not paste a chat history at it. Point it at the repo, which is now self-describing:

- `README.md` current-state block: every target, its providers, and the nine gates.
- `SECURITY.md`: the trust boundaries and the ban rules, which are its constraints.
- `CREDITS.md`: every provider and where its bundle lives.
- `docs/review/PATCHES-*.txt`: the patcher's own output, which is the ground truth for what a
  patch is actually called.
- `docs/review/SESSION-*.md` and `AUDIT-*.md`: the failures already made, so it does not repeat
  them.

That set is deliberately generated rather than written, so an agent reading it cannot be misled
by a stale hand-typed number. It is also why the drift gates exist.

## The first task to give it, and the last one

First: *"Read `docs/review/PATCHES-youtube.txt`. For each patch that is default-on and not in
`src/patches/youtube-morphe/include-patches`, say whether it is safe under the rules in
`SECURITY.md`, and open one PR adding only the safe ones."* Small, reviewable, and it clears real
backlog.

Never: *"keep the repo healthy."* An open-ended instruction against a repo that can publish
signed binaries is how you get a surprise you cannot audit.
