<!-- W16d, 24 Oct 2026: research record for the owner's MCP ask. Pins below were read from official
APIs on that day; re-read them before any packet uses them. Nothing here runs yet. -->

# MCP groundwork pilot for patch-factory

## Status (W16g)

Built manual-only in W16g; first owner-dispatched run proves lockdown.

## 1. CI host/client

**Recommendation:** keep the existing Actions integration and pin
`google-github-actions/run-gemini-cli` to **v0.1.22**, full commit
`f77273f4c914e4bf38440cf36a0369cb64a37489` (latest API:
https://api.github.com/repos/google-github-actions/run-gemini-cli/releases/latest;
tag refs: https://api.github.com/repos/google-github-actions/run-gemini-cli/git/matching-refs/tags/v).
The maintained action accepts `settings`, writes `.gemini/settings.json`, and
its official example explicitly supports `mcpServers`:
https://github.com/google-github-actions/run-gemini-cli/blob/main/examples/workflows/CONFIGURATION.md#mcp-servers-mcpservers.

It can pin the installed open-source CLI too: latest release **v0.65.0**, full
commit `6006c14a4decfe4b891c6263ad6ad5992e404b5b` (release API:
https://api.github.com/repos/google-gemini/gemini-cli/releases/latest; tag ref:
https://api.github.com/repos/google-gemini/gemini-cli/git/ref/tags/v0.65.0).
Headless `-p`/JSON output: https://github.com/google-gemini/gemini-cli/blob/main/docs/cli/headless.md.

Minimal starting point (use a pinned server release, not `latest`):

```yaml
- uses: google-github-actions/run-gemini-cli@f77273f4c914e4bf38440cf36a0369cb64a37489 # v0.1.22
  env: { GITHUB_TOKEN: ${{ github.token }} }
  with:
    gemini_api_key: ${{ secrets.GEMINI_API_KEY }}
    gemini_cli_version: '0.65.0'
    settings: |-
      {"mcp":{"allowed":["github"],"autoAllowInHeadless":true},"mcpServers":{"github":{"command":"docker","args":["run","-i","--rm","-e","GITHUB_PERSONAL_ACCESS_TOKEN","ghcr.io/github/github-mcp-server:v2.0.3","stdio","--read-only","--toolsets=repos"],"env":{"GITHUB_PERSONAL_ACCESS_TOKEN":"${GITHUB_TOKEN}"}}}}
    prompt: 'Return only schema-valid candidate provider lines; never modify files or GitHub.'
```

`autoAllowInHeadless` is an explicit opt-in: Gemini policy denies configured
MCP tools by default in non-interactive mode (source:
https://github.com/google-gemini/gemini-cli/blob/main/packages/core/src/policy/types.ts).
The action currently invokes `--yolo`; expose only a read-only MCP server and no
shell/file-write tools.

## 2. Servers that fit

* **GitHub:** official `github/github-mcp-server`, maintained by GitHub, MIT
(https://raw.githubusercontent.com/github/github-mcp-server/main/LICENSE).
Local `--read-only` and toolset/tool exclusion controls are documented at
https://raw.githubusercontent.com/github/github-mcp-server/main/docs/server-configuration.md.
Latest **v2.0.3** resolves via official APIs to commit
`b98d115bbb080e9555466a96656ec4df605aea21` (annotated tag:
https://api.github.com/repos/github/github-mcp-server/git/tags/c491f68db823df67e68a6927a4839c3d39c7a99a;
release: https://api.github.com/repos/github/github-mcp-server/releases/latest).
Use the `v2.0.3` image or build that commit, never `:latest`; release API gives
Linux x86_64 asset digest `sha256:f797c20fe02a755865d0e2d46184ab47e31bf1619b0855b8d89c531e45a651c2`.
`GITHUB_TOKEN` with job `contents: read` suffices for public/repository reads;
least-privilege guidance: https://docs.github.com/en/actions/security-for-github-actions/security-guides/automatic-token-authentication.
Actions `GITHUB_TOKEN` is 1,000 REST requests/hour/repository and search is
stricter: https://docs.github.com/en/rest/using-the-rest-api/rate-limits-for-the-rest-api.

* **Web/release-note fetch:** `modelcontextprotocol/servers` Fetch is a
steering-group reference implementation, explicitly not production-ready
(https://raw.githubusercontent.com/modelcontextprotocol/servers/51b6382a3e827aceb6bce430b1208d69b93d95ea/README.md).
Pin main API commit `51b6382a3e827aceb6bce430b1208d69b93d95ea`:
https://api.github.com/repos/modelcontextprotocol/servers/git/ref/heads/main.
At that commit `src/fetch/LICENSE` is MIT, while new repo contributions are
transitioning to Apache-2.0. Its single fetch tool is read-only/idempotent,
needs no key, obeys robots.txt, rejects private-IP destinations/redirects, and
converts HTML to Markdown: https://raw.githubusercontent.com/modelcontextprotocol/servers/main/src/fetch/README.md.
Pin source/package/container; do not run unpinned `uvx` in CI.

* **GitLab:** the official GitLab MCP is built into GitLab, not a standalone
open-source server. Endpoint `/api/v4/mcp`; auth is OAuth `mcp` scope or a
fine-grained PAT with MCP Execute permission. Legacy/project/group tokens are
rejected and OAuth is interactive, making it a poor headless pilot:
https://docs.gitlab.com/user/model_context_protocol/mcp_server/.
Open-source alternative: `zereight/gitlab-mcp` (project maintainer `zereight`,
MIT) supports PAT and `--permission-mode=readonly`:
https://raw.githubusercontent.com/zereight/gitlab-mcp/main/README.md.
Latest **v2.3.7** is commit `03dd46dfd45829abf0c1da43da6273f29c67919c`; MCP bundle
digest `sha256:bf7cabd84e14e9fe56e6d97a0132e9fc181c0d935bca9b8a3cefa20fd44205e7`
(official APIs: https://api.github.com/repos/zereight/gitlab-mcp/releases/latest and
https://api.github.com/repos/zereight/gitlab-mcp/git/ref/tags/v2.3.7). It needs
`GITLAB_PERSONAL_ACCESS_TOKEN`; add only with an approved read-only GitLab secret.
Public GitLab pages can instead be read by Fetch without a GitLab credential.

## 3. Do not replace store scraping

Keep FlareSolverr + the Cloudflare-bypass container + `pup` for (c): it is
deterministic, bounded, and machine-checkable. Fetch is model-facing HTTP with
truncation/robots/rate-limit/failure variability and no browser challenge solver.
MCP adds model-call cost, latency, API quotas, and prompt-injection exposure.
Use it for discovery and human-readable changelog summaries, not APK version/URL
authority; never feed MCP output directly into the build.

## 4. Weekly pilot (no new schedule)

Add a read-only `provider-research` job to existing weekly `community-watch.yml`
(`13 3 * * 1`), with job `permissions: contents: read` and no issue/action/write
permission; leave existing writer jobs unchanged. Input the 17 package IDs plus
`src/community/bundles.json`; query GitHub MCP for candidates and Fetch for
public GitLab pages, READMEs, release notes, and `CHANGELOG.md`.

Emit an artifact/log of **only plain lines**, e.g.:

```text
github OWNER/REPO com.example.app https://github.com/OWNER/REPO
gitlab PROJECT_ID com.example.app https://gitlab.com/...
```

Reject anything not matching `^(github|gitlab) [^ ]+ [A-Za-z][A-Za-z0-9_.]+ https://[^ ]+$`;
cap lines per app and artifact size. Candidates only: no index edit, issue,
onboarding, bundle download, or build. A deterministic follow-up must use this
repo's existing `list-patches` path (`explore.yml`/Morphe patcher) to prove an
`.mpp` contains the package: **provider facts come only from `list-patches`**,
never model prose. Changelog summaries are advisory and cite URL plus release/tag.

Treat README/issue/release/changelog/HTML bytes as untrusted data, not
instructions. The model gets no write tools, shell, issue permission,
signing/build secrets, or secrets except `GEMINI_API_KEY`; the read-only MCP
subprocess gets only ephemeral read-only `GITHUB_TOKEN`. Instruct it to quote no
fetched instructions and return only the schema. Strict-parse output, reject
non-GitHub/GitLab hosts, cap response length, fail closed on ambiguity, and keep
human review plus deterministic `list-patches` mandatory before any change.

## Decision (W16d)

Owner wants MCP servers to do groundwork. Plan accepted as a pilot for the next packet, not this
one: the Gemini CLI action runs in --yolo mode, so the tool lockdown (no shell, no file writes, only
the read-only GitHub server) must be proven on one real run before it is scheduled. Store scraping
stays deterministic. Candidates reach the owner as Needs you items (take, drop, hold) and are only
facts after list-patches.
