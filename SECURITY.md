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
| Patch bundles from providers | Intentionally not pinned. `max_patch_age_days` is advisory. Explicitly requested patches must appear in the applied log; this does not prove that provider code or default-on additions are safe. |
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

## Before you make this public

Read this once, properly. The code here is defensible; **the release assets are the exposure.**

### The releases are the liability, not the repo

Publishing a patch is publishing a diff. Publishing a signed APK is redistributing someone
else's application binary, modified. That is a materially different act and it is what a
rights holder acts on. Several of these builds unlock paid functionality:

- Truecaller premium
- MX Player **Pro**
- AdGuard lifetime premium
- Key Mapper premium

Those four are the ones that turn "a hobby build pipeline" into "a distribution channel for
paid software". A takedown against this repo would name the release assets, not `build.sh`.

### What each risk actually looks like

| Risk | How it arrives | What reduces it |
|---|---|---|
| DMCA takedown of the repo | GitHub forwards a notice; the repo is disabled pending response | Publish the pipeline, not the binaries. A public repo whose releases are private, or absent, is far harder to complain about. |
| Trademark complaint | App names and icons in the docs and the Pages catalog | Use package names; do not ship icons or logos you do not own. |
| Provider objection | A patch author objects to being listed or aggregated | `CREDITS.md` names every provider with a link, and offers same-day removal. Keep that promise. |
| Account action against **you** | You install these on accounts you own | Server-visible patches are already banned here. The JioHotstar build got a paid streaming account suspended in Aug 2026: that already happened once. |
| Someone else's device breaks | A stranger installs a build and loses data | The releases carry a checksum and this file carries the warning. Do not add an install script that hides the risk. |

### The honest recommendation

Make the **repository** public if you want it used as a template. Do not advertise the
**releases**. Specifically:

1. Keep the four paid-unlock apps out of any public download page. They are the ones that
   attract a complaint, and they are the least defensible.
2. Do not add a README badge, a Telegram channel or a Reddit post pointing strangers at the
   releases. Distribution scale is what converts legal risk into legal action.
3. Never accept a patch bundle from a provider you have not read. A public repo invites pull
   requests, and a malicious `extra_bundles` entry would be signed with your key.
4. If you ever hand this to someone else, they generate their own keystore. Your key signing
   somebody else's build is your name on their APK.

### What you would regret most

Not a takedown. The realistic worst case is quieter: a provider ships a patch that phones home
or spoofs an identity, it lands in a build you signed, and someone's account is banned by an
app you handed them. That is why `BANNED` exists, why the applied-patch list is printed in every
release body, and why nothing here should ever be installed on an account you cannot afford to
lose. Including yours.
