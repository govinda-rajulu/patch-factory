# Security

`patch-factory` downloads Android APKs, rewrites them with third-party patch bundles, signs
them, and publishes them. Anyone reusing this repo is trusting several parties at once, so
here is exactly who, and what stops each one silently changing the output.

## What is trusted, and what checks it

| Trusted input | Control |
|---|---|
| Build tools (`pup`, `APKEditor`) | sha256-pinned in `src/build/TOOLING.sha256`. A mismatch aborts the build. Re-pin deliberately with `src/build/repin.sh`. |
| `morphe-desktop` (the patcher) | Taken as `latest` on purpose: new provider bundles need new patcher versions. **Not pinned.** This is the largest remaining supply-chain surface. |
| Cloudflare-bypass containers | Pinned by image digest in `.github/actions/preparing/action.yml`. |
| Patch bundles from providers | Not pinned; that is the point of the project. Constrained instead: `max_patch_age_days` disqualifies a stale provider, and every applied patch is compared by name against the include list. |
| The APK from the store | Size floor, real zip, `AndroidManifest.xml` present, and the package name verified twice: on the download and against what the patcher says it filtered. |
| Patches themselves | `src/patches/BANNED` blocks server-visible and identity-changing patches from any include list. `CONFIRM` warns. `EXCEPTIONS` documents each deliberate override with a date. |

## Signing

Releases are signed with a keystore that is **not** in this repo and never leaves the owner.
GitHub Actions secrets are write-only, so they are not a backup. A truncated `KEYSTORE_B64`
fails the build rather than producing an unsigned APK. See the key restore drill in
`RECOVERY.md`.

**If you fork this, generate your own keystore.** APKs signed by a different key cannot
update each other, and you do not want your users' apps tied to somebody else's key.

## Workflow permissions

Every workflow declares least-privilege `permissions`. `workflow_dispatch` inputs are passed
to shell through `env:`, never interpolated into a `run:` block, so a crafted input cannot
become a command. There is no `pull_request_target` and no workflow that runs untrusted code
from a fork.

## Verifying a download

Every release body carries the APK filename, its size and its SHA-256. Check it before
installing:

    sha256sum patch-factory-app-vX.Y.Z-arm64-v8a.apk

## Reporting something

Open an issue. This is a personal project with no SLA, and it ships modified builds of apps
whose terms may forbid them: **use at your own risk**, on accounts you are willing to lose.
Patches that are visible to a server (signature spoofing, package renaming, ad-ID spoofing)
are banned here for exactly that reason.
