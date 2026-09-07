# Instructions for AI agents working in this repository

Jules, Codex, Copilot and Gemini CLI all read this file. It is the contract. If a request
conflicts with anything here, refuse the request and say which line forbids it.

## What this repo does

It patches Android APKs in GitHub Actions and publishes **signed** releases that the owner's
phones install through Obtainium. A wrong change here does not break a website: it ships a
modified, signed binary to a real device, and some of these apps can ban an account for it.

## Hard limits

**You open pull requests. You never push to `main`.** No exceptions, including for a one-line fix.

You must never modify:

- `.github/workflows/**` or `.github/actions/**` — these run with secrets and can publish releases
- `src/patches/BANNED`, `src/patches/CONFIRM`, `src/patches/QUARANTINE` — the safety rules
- `src/build/TOOLING.sha256` — the supply-chain pins
- `LICENSE`, `SECURITY.md`, `CREDITS.md`, `.github/CODEOWNERS`
- anything under `src/patches/_attic/` — an archive, unreferenced on purpose

A PR touching any of those should be closed unread. `CODEOWNERS` enforces review; this file
tells you not to try.

## What you may propose

| Allowed | How |
|---|---|
| Add or remove a patch name in an `include-patches` file | One target per PR, and say why per patch |
| Add a provider as an `extra_bundles` entry | It needs its own `patch_dir` with both files |
| Promote an extra bundle to a second `candidate` | Only if you can show it supports the app version being built |
| Update a `note` field | Dated, factual, one sentence |
| Open an issue describing something you cannot fix | Always preferred over a speculative PR |

## The rules you are enforcing

1. **A patch a server can see does not ship.** `BANNED` holds lowercase **substrings**, not exact
   names, so `spoof signature` matches `Spoof signature verification`. Never "fix" a filter by
   making it exact: an exact-match filter here once matched zero of 45 and shipped six spoof
   patches in a published APK.
2. **`CONFIRM` means a human decides**, not that you decide carefully.
3. **`-e` and `-d` bind to the nearest preceding `-p`.** A multi-bundle target needs a `patch_dir`
   per bundle, and `selections.sh` emits every `-d` before the `-e` of the same bundle, so **`-d`
   wins**. If you add a patch to `include-patches`, check it is not also in `exclude-patches`.
4. **One patch name may not appear under two bundles of one target.** The build aborts on it.
5. **Provider age is advisory.** A bundle that still applies is still good. Never disqualify a
   provider for being old; the applied-vs-requested gate is the real test.
6. **`list-patches` must be run with `-x`.** Without it the patcher hides every app version marked
   experimental, which makes a current provider look years stale. Also pass `-u`.

## Before you claim anything

Run the command and read its output. Do not reason from a filename or a commit message. Every
serious mistake in this repo's history came from skipping that step, and they are listed at the
end of `docs/review/REPORT-2026-09-07.md` so you do not repeat them.

Facts you may rely on, because they are generated and gated in CI:

- `README.md` current-state block — targets, providers, stores, the gates
- `CREDITS.md` — every provider and where its bundle lives
- `docs/review/PATCHES-*.txt` — the patcher's own output, ground truth for patch names
- `docs/review/DECISIONS-*.tsv` — classified patches; **column 1 belongs to the owner**
- `docs/review/OPEN-WORK.md` — what is actually open

Facts you may not rely on: anything you remember, and any number typed into prose.

## How to open a good PR here

1. One target, one concern. A PR that changes three targets cannot be reviewed.
2. Title: `<target>: <what changed>`. No emoji.
3. Body: for each patch added or removed, one line saying which rule or measurement justifies it,
   and paste the `list-patches` line that proves the patch exists under that exact name.
4. Say what you did **not** do and why, if you noticed something out of scope.
5. Never claim a build passes. You cannot run one. Say "unverified, needs a dispatch".

## If you are unsure

Open an issue instead. An issue costs a read; a wrong PR merged costs a phone reinstall and
possibly an account.
