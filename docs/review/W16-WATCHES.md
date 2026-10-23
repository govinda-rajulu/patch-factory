# W16 watches

The collectors still run on their old schedules and keep their evidence artifacts. One additional workflow, **Needs you**, runs once daily at 10:29 IST (`59 4 * * *`), after Tooling watch at 09:59 IST, and can be started manually. It reads the newest Actions artifact for each collector through the Actions API, renders one issue, and is the only new daily reader/writer.

The renderer groups work as **Decide**, **Install**, **Fix**, then **FYI**. A body that has not changed gets no comment. An empty result is one line: `Needs you: nothing needs you today.` Every collector report remains in the artifact path, so no finding is discarded.

## Issues that remain

- **#27 Nightly watch** remains because `watch_issue.sh` reads its previous body and fingerprint to suppress unchanged comments. Its collector still writes that stateful issue.
- **Tooling watch** remains because `tooling_watch.py --upstreams` reads the previous issue marker with `previous_state()` to detect changes. Its issue is state, not merely presentation.
- **Community watch #221** remains because `community_watch.py report` performs exact issue readback before `advance` is allowed to update `src/community/bundles.json` and `src/community/watch-state.json`.
- **Provider watch #213** and **Selection watch #182** no longer receive collector issue writes. Provider has no issue-backed state; Selection uses the `watch-state` branch for its digest and the adopt PR path does not read #182. Their artifacts are consumed by Needs you.

The old provider and selection issues can remain open as historical records; no new comments are made there.

## Community provider ranker

`community_model.rank_providers()` ranks every index provider that declares an enabled configured app. It puts an official `MorpheApp` repository first, then compares applicable patch count, support for the app's current version, the number of supported versions, and freshness (`appUpdates` for that app, then `updatedAt`). A current version is read from an explicit target version field, with the older `max_app_version` field as a fallback. Unknown support stays unknown.

The ranker marks an app only when an alternative's complete rank is better than the configured provider. It does not switch a provider or create a pull request. The owner decision goes to **Decide** in Needs you; Selection's adopt PR and Rule merge remain unchanged.
