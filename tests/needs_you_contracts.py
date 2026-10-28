import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from datetime import datetime, timezone, timedelta
import re
from types import SimpleNamespace

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src/etc'))
import needs_you as n  # noqa: E402
import community_model as model  # noqa: E402


class EvidenceReasonSkipsDocumentedException(unittest.TestCase):
    def test_documented_exception_is_not_the_reason(self):
        import importlib.util, pathlib as P
        spec = importlib.util.spec_from_file_location('ny', str(P.Path(__file__).resolve().parents[1] / 'src/etc/needs_you.py'))
        ny = importlib.util.module_from_spec(spec); spec.loader.exec_module(ny)
        text = ('# Nightly watch: FAILED\n| Banned / confirm scan | 1 documented exceptions |\n'
                '- gg-photos Change package name: documented exception, missing on purpose\n'
                '- adguard/adguard-hoo-dles: provider list unreadable - UNVERIFIED (error: LIST_COMMAND_FAILED)\n')
        r = ny._evidence_reason(text, None)
        self.assertNotIn('Change package name', r)
        self.assertIn('LIST_COMMAND_FAILED', r)


class Renderer(unittest.TestCase):
    def test_empty_day_is_one_plain_line(self):
        with tempfile.TemporaryDirectory() as d:
            paths = {}
            for name in n.ISSUES:
                p = Path(d) / (name + '.md'); p.write_text('# report: OK\n'); paths[name] = p
            body = n.render(paths)
        # W16j: no daily 'Keep building X?' questions; the three plain lines lead.
        self.assertNotIn('Keep building', body)
        self.assertIn('**What happened:**', body)
        self.assertIn('`yes all`', body)

    def test_groups_decide_install_fix_and_keeps_reports(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d)
            files = {
                'selection': '# Selection watch: NEEDS YOU\n\n## Needs you\n\n- add or skip Name\n',
                'tooling': '# Tooling watch\n\nnew update available\n',
                'nightly': '## Nightly Watch: UNKNOWN\n',
                'provider': '# Provider watch: OK\n',
                'community': '## Provider ranker\n**Needs you:** choose whether to switch.\n- **app**: better provider\n',
            }
            for name, text in files.items(): (p / (name + '.md')).write_text(text)
            body = n.render({name: p / (name + '.md') for name in n.ISSUES})
        self.assertIn('## G8 · Other things to look at', body)
        self.assertIn('FYI (', body)
        self.assertIn('add or skip Name', body)
        self.assertNotIn('What this watch does not check', body)

    def test_each_watch_source_reaches_its_owner_group(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d)
            files = {
                "selection": "## Needs you\n\n- decide whether to add or skip a patch\n",
                "tooling": "# Tooling watch\n\nupdate available\n",
                "nightly": "## Nightly Watch: UNKNOWN\n",
                "provider": "# Provider watch: FAILED\nprovider could not be read\n",
                "community": "## Provider ranker\n**Needs you:** choose whether to switch.\n- **app**: better provider\n",
            }
            for name, text in files.items(): (p / (name + ".md")).write_text(text)
            body = n.render({name: p / (name + ".md") for name in n.ISSUES})
        self.assertIn("## G8", body)
        self.assertIn("Review the tooling report", body)
        self.assertIn("inspect and rerun it", body)
        self.assertIn("FYI (", body)
        self.assertIn("decide whether to add", body)
        self.assertIn("install any update", body)
        self.assertIn("Nightly reported", body)
        self.assertIn("Provider reported", body)

    def test_fix_item_uses_recorded_reason_and_run_link_or_explicitly_says_none(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            reports = {}
            for name in n.ISSUES:
                path = root / (name + '.md')
                path.write_text('# %s report\nRun: https://github.com/o/r/actions/runs/1\n' % name)
                reports[name] = path
            reports['nightly'].write_text(
                '# Nightly Watch: UNKNOWN\nstop code: COVERAGE_UNAVAILABLE\n'
                'Run: https://github.com/o/r/actions/runs/99\n')
            body = n.render(reports, targets=[])
        self.assertIn('Nightly reported COVERAGE_UNAVAILABLE; inspect and rerun it.', body)
        self.assertIn('[run](https://github.com/o/r/actions/runs/99)', body)
        self.assertNotIn('read or run problem', body)

    def test_held_selection_names_are_separate_stable_decisions(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            selection = root / 'selection.md'
            selection.write_text("""# Selection watch: NEEDS YOU

## Needs you

- nothing blocked

## Older names never chosen, held by the rule (3)

| Why held | Names | Apps |
|---|---|---|
| paid word on an account app | 3 (amazonmusic, hotstar, instagram) | amazonmusic, hotstar, instagram |
<details><summary>Every held name with its reason</summary>

- amazonmusic / rookieenough: `Skip account` (held: paid word "account")
- hotstar / chiggi: `Premium` (held: paid word "account")
- instagram / piko: `Open account` (held: paid word "account")

</details>
""")
            reports = {name: root / (name + '.md') for name in n.ISSUES}
            for name, path in reports.items():
                if name != 'selection':
                    path.write_text('# %s report\n' % name)
            reports['selection'] = selection
            targets = [{'id': 'amazonmusic', 'enabled': True,
                        'candidates': [{'name': 'rookieenough', 'patch_dir': 'amazonmusic-rookieenough'}]}]
            body = n.render(reports, targets=targets)
            rows = n.held_items(selection, targets)
            changed = root / 'selection-changed.md'
            changed.write_text(selection.read_text().replace('paid word "account"', 'matches CONFIRM'))
            changed_rows = n.held_items(changed, targets)
        self.assertEqual(len(rows), 3)
        self.assertIn("amazonmusic: rookieenough offers 'Skip account' (held: paid word", body)
        self.assertIn("hotstar: chiggi offers 'Premium' (held: paid word", body)
        self.assertIn("instagram: piko offers 'Open account' (held: paid word", body)
        self.assertNotIn('paid word on an account app | 3 (amazonmusic, hotstar, instagram)', body)
        self.assertIn("| amazonmusic | rookieenough | Skip account |", body)
        self.assertIn('"group":"G7"', body)
        self.assertEqual([row['id'] for row in rows], [row['id'] for row in changed_rows])

    def test_live_233_new_name_rows_and_rule_off_names(self):
        # W16h: copied from live Needs you #233 (24 Oct). The waiting new-name table
        # leaked as "N-7236b6 — | Kind | What to do |", and BANNED or second-copy
        # names were offered as takes that cannot change anything.
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            selection = root / 'selection.md'
            selection.write_text("""# Selection watch: NEEDS YOU

## Needs you

| Kind | What to do |
|---|---|
| new name | instagram / piko: `Hide hidden requests` (since 2026-10-23; held: changes what the app shows for good: no off switch and no ad, tracking or suggestion target in its description). Add: "5. Add target", action patch, id `instagram`, patches `Hide hidden requests`; skip: patches `-Hide hidden requests` |
| new name | **BAN** reddit / adobo: `Spoof thing` (since 2026-10-24; held: matches BANNED). Add: "5. Add target", action patch, id `reddit`, patches `Spoof thing`; skip: patches `-Spoof thing` |

## Older names never chosen, held by the rule (3)

<details><summary>Every held name with its reason</summary>

- photos / rushiranpise: `Spoof app signature` (held: matches BANNED)
- photos / rushiranpise: `Spoof Widevine / DRM level` (held: matches CONFIRM: owner decides)
- instagram / brosssh: `Hide notes tray` (held: another bundle of this app (piko) offers the same name; one bundle per name (AGENTS rule 4))

</details>
""")
            reports = {name: root / (name + '.md') for name in n.ISSUES}
            for name, path in reports.items():
                if name != 'selection':
                    path.write_text('# %s report\n' % name)
            reports['selection'] = selection
            body = n.render(reports, targets=[])
        self.assertNotIn('| Kind | What to do |', body)
        self.assertNotIn('— | Kind', body)  # the W16h leak; W16j tables are deliberate
        self.assertIn("instagram: piko offers 'Hide hidden requests' (held: changes what the app shows", body)
        self.assertIn("photos: rushiranpise offers 'Spoof Widevine / DRM level' (held: matches CONFIRM", body)
        self.assertNotIn("offers 'Spoof app signature'", body)
        self.assertNotIn("offers 'Spoof thing'", body)
        self.assertNotIn("offers 'Hide notes tray'", body)
        fyi = body.split('FYI (', 1)[1]
        self.assertIn('- photos / rushiranpise: 1 name(s) stay off by the BANNED rule: `Spoof app signature`', fyi)
        self.assertIn('- reddit / adobo: 1 name(s) stay off by the BANNED rule: `Spoof thing`', fyi)
        self.assertIn('- instagram / brosssh: 1 name(s) wait for the bundle that offers them first', fyi)
        self.assertIn('**What happened:** 2 choice(s)', body)

    def test_changed_issue_edits_then_comments_and_unchanged_is_quiet(self):
        calls = []
        def run(args, **kwargs):
            calls.append(args)
            if args[1:3] == ['issue', 'list']:
                return SimpleNamespace(returncode=0, stdout=json.dumps([{'number': 9, 'title': 'Needs you', 'body': 'old', 'author': {'is_bot': True, 'login': 'github-actions[bot]'}}]), stderr='')
            return SimpleNamespace(returncode=0, stdout='', stderr='')
        # W16j: a body edit with no new item ids is quiet; new ids get one comment listing them.
        self.assertEqual(n.deliver('new\n', run=run), 'EDITED')
        self.assertEqual([x[1:3] for x in calls], [['issue', 'list'], ['issue', 'edit']])
        calls.clear()
        self.assertEqual(n.deliver('| N-abc123 | new row |\n', run=run), 'EDITED')
        self.assertEqual([x[1:3] for x in calls], [['issue', 'list'], ['issue', 'edit'], ['issue', 'comment']])
        self.assertIn('N-abc123', calls[-1][-1])
        calls.clear()
        def same(args, **kwargs):
            calls.append(args)
            return SimpleNamespace(returncode=0, stdout=json.dumps([{'number': 9, 'title': 'Needs you', 'body': 'new\n', 'author': {'is_bot': True, 'login': 'github-actions[bot]'}}]), stderr='')
        self.assertEqual(n.deliver('new\n', run=same), 'UNCHANGED')
        self.assertEqual(len(calls), 1)


class NeedsYouDecisions(unittest.TestCase):
    def test_parser_accepts_valid_mixed_case_and_ignores_unknown_ids(self):
        self.assertEqual(n.parse_decisions("take N-a1B2c3\nDROP n-deadbe\nhello\nhold N-ffffff", ["N-A1B2C3", "N-DEADBE"]),
                         [("take", "N-A1B2C3"), ("drop", "N-DEADBE")])

    def test_ledger_hold_expires_after_fourteen_days(self):
        stamp = datetime(2026, 1, 1, tzinfo=timezone.utc)
        row = {"id": "N-a1b2c3", "verb": "hold", "time": stamp.isoformat()}
        item = {"id": "N-a1b2c3"}
        self.assertEqual(n.decision_state(item, [row], stamp + timedelta(days=13, hours=23)), "held")
        self.assertEqual(n.decision_state(item, [row], stamp + timedelta(days=14)), "visible")

    def test_workflow_guards_owner_title_association_and_bot(self):
        base = {"issue": {"title": "Needs you"}, "comment": {"user": {"login": "govinda-rajulu", "type": "User"}, "author_association": "OWNER"}}
        self.assertTrue(n.authorized_comment(base, "govinda-rajulu"))
        for mutate in ({"issue": {"title": "Other"}}, {"comment": {"user": {"login": "other", "type": "User"}}}, {"comment": {"author_association": "MEMBER"}}, {"comment": {"user": {"login": "govinda-rajulu", "type": "Bot"}}}):
            event = {"issue": {"title": "Needs you"}, "comment": {"user": {"login": "govinda-rajulu", "type": "User"}, "author_association": "OWNER"}}
            event.update(mutate)
            self.assertFalse(n.authorized_comment(event, "govinda-rajulu"))

    def test_repeated_command_is_recorded_once_and_does_not_dispatch_again(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            comment = root / "comment.txt"
            ledger = root / "ledger.json"
            comment.write_text("take N-AAAAAA\n")
            prior = [{"id": "N-AAAAAA", "verb": "take", "kind": "unknown", "except": []}]
            ledger.write_text(json.dumps(prior))
            body = '<!-- needs-you-item:{"id":"N-AAAAAA","kind":"decide","action":"patch","target":"example","patches":"Patch"} -->'
            calls = []
            def run(args, **kwargs):
                calls.append(args)
                if args[1:3] == ["issue", "list"]:
                    return SimpleNamespace(returncode=0, stdout=json.dumps([{"number": 1, "title": "Needs you", "body": body, "author": {"is_bot": True}}]), stderr="")
                return SimpleNamespace(returncode=0, stdout="", stderr="")
            self.assertEqual(n.decide(comment, ledger, "o/r", run=run), "RECORDED")
            self.assertEqual(json.loads(ledger.read_text()), prior)
            self.assertFalse(any(args[1:3] == ["workflow", "run"] for args in calls))

    def test_invalid_ledger_stops_decide_before_writing_history(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            comment = root / "comment.txt"
            ledger = root / "ledger.json"
            comment.write_text("take N-AAAAAA\n")
            ledger.write_text("not json")
            body = '<!-- needs-you-item:{"id":"N-AAAAAA","kind":"decide"} -->'
            def run(args, **kwargs):
                if args[1:3] == ["issue", "list"]:
                    return SimpleNamespace(returncode=0, stdout=json.dumps([{"number": 1, "title": "Needs you", "body": body, "author": {"is_bot": True}}]), stderr="")
                return SimpleNamespace(returncode=0, stdout="", stderr="")
            with self.assertRaises(ValueError):
                n.decide(comment, ledger, "o/r", run=run)
            self.assertEqual(ledger.read_text(), "not json")

    def test_effect_mapping_is_review_only(self):
        self.assertEqual(n._review_item({"kind": "review", "first_line": "review: x"}), True)
        self.assertEqual(n._review_item({"kind": "community", "first_line": "review: x"}), False)

    def test_take_held_name_dispatches_existing_patch_route(self):
        calls = []
        def run(args, **kwargs):
            calls.append(args)
            return SimpleNamespace(returncode=0, stdout='', stderr='')
        result = n.apply_effect('take', {'action': 'patch', 'target': 'amazonmusic', 'patches': 'Skip account'}, 'o/r', run)
        self.assertEqual(result, 'patch dispatched: next packet will add it')
        self.assertEqual(calls[0][1:3], ['workflow', 'run'])
        self.assertIn('action=patch', calls[0])
        self.assertIn('id=amazonmusic', calls[0])
        self.assertIn('patches=Skip account', calls[0])


class ProviderItems(unittest.TestCase):
    def setUp(self):
        self.index = {
            "compatibilities": [
                {"com.example.app": ["1.9", "2.0"]},
                [{"packageName": "com.example.app", "targets": [{"version": "3.1"}]}],
            ],
            "bundles": [
                {"source": "github", "repo": "Us/ours", "targetApps": ["com.example.app"],
                 "patches": [{"compatiblePackagesKey": 0}, {"compatiblePackagesKey": 0}]},
                {"source": "github", "repo": "a/one", "targetApps": ["com.example.app"],
                 "patches": [{"compatiblePackagesKey": 0}, {"compatiblePackagesKey": 1}]},
                {"source": "github", "repo": "b/two", "targetApps": ["com.example.app"],
                 "patches": [{"compatiblePackagesKey": 1}]},
                {"source": "github", "repo": "c/three", "targetApps": ["com.example.app"],
                 "patches": [{"compatiblePackagesKey": 0}]},
                {"source": "github", "repo": "d/four", "targetApps": ["com.example.app"],
                 "patches": [{"compatiblePackagesKey": 0}]},
            ],
        }
        self.targets = [{"id": "example", "label": "Example", "enabled": True,
                         "package": "com.example.app", "max_app_version": "1.9",
                         "candidates": [{"owner": "us", "repo": "ours"}]}]

    def test_per_app_counts_shapes_excludes_configured_caps_and_stable_ids(self):
        rows = n.provider_items(self.index, self.targets)
        self.assertEqual([row["first_line"].split(":", 1)[0] for row in rows], ["Example"] * 3)
        self.assertEqual([row["first_line"].split(":", 2)[1].split()[0] for row in rows], ["a/one", "b/two", "c/three"])
        self.assertIn("offers 2 patches", rows[0]["first_line"])
        self.assertIn("newest listed app version 3.1", rows[0]["first_line"])
        self.assertIn("we use: us/ours with 2", rows[0]["first_line"])
        self.assertIn("take = run Explore", rows[0]["description"])
        # W16h: the id names the app and provider only, so a new version or a
        # primary switch keeps the owner's earlier drop or hold.
        self.assertEqual(rows[0]["id"], n.item_id("decide", "provider|com.example.app|a/one"))
        moved = [dict(self.targets[0], max_app_version="2.5", extra_bundles=[{"owner": "x", "repo": "extra"}])]
        again = n.provider_items(self.index, moved)
        self.assertEqual([r["id"] for r in rows], [r["id"] for r in again])
        self.assertNotEqual(rows[0]["first_line"], again[0]["first_line"])
        self.assertIn("plus extras x/extra", again[0]["first_line"])
        self.assertEqual(rows[-1]["provider_more"], 1)

    def test_no_version_provider_counts_as_any_version(self):
        index = {"compatibilities": [[{"packageName": "com.example.app", "targets": [{}]}]],
                 "bundles": [{"source": "github", "repo": "any/provider",
                              "targetApps": ["com.example.app"],
                              "patches": [{"compatiblePackagesKey": 0}, {"compatiblePackagesKey": 0},
                                          {"compatiblePackagesKey": 0}]}]}
        rows = n.provider_items(index, self.targets)
        self.assertEqual(len(rows), 1)
        self.assertIn("offers 3 patches", rows[0]["first_line"])
        self.assertIn("newest listed app version any version", rows[0]["first_line"])

    def test_take_dispatches_explore_and_refuses_bad_inputs(self):
        calls = []
        def run(args, **kwargs):
            calls.append(args)
            return SimpleNamespace(returncode=0, stdout="", stderr="")
        item = {"action": "explore", "host": "github", "ident": "a/one", "package": "com.example.app"}
        self.assertEqual(n.apply_effect("take", item, "o/r", run), "Explore dispatched: patches issue will open")
        self.assertEqual(calls[0][1:3], ["workflow", "run"])
        self.assertIn("-f", calls[0])
        self.assertIn("host=github", calls[0])
        self.assertIn("ident=a/one", calls[0])
        self.assertIn("package=com.example.app", calls[0])
        self.assertEqual(n.apply_effect("take", dict(item, ident="bad ident"), "o/r", run),
                         "Explore refused: malformed provider or package")
        self.assertEqual(len(calls), 1)

    def test_render_has_one_provider_line_and_one_fyi_line_per_report(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d)
            reports = {}
            for name in n.ISSUES:
                q = p / (name + ".md")
                q.write_text("# report\nRun: https://github.com/o/r/actions/runs/123\n")
                reports[name] = q
            body = n.render(reports, bundles=self.index, targets=self.targets)
        line = "Example: a/one offers 2 patches for it"
        self.assertEqual(body.count(line), 1)
        self.assertIn("- Example: and 1 more in the index", body)
        self.assertEqual(body.count("https://github.com/o/r/actions/runs/123"), len(n.ISSUES))
        self.assertNotIn("# report", body)
        self.assertNotIn("needs-you-item", body.split("FYI (", 1)[1].split("</details>", 1)[0])


class Contracts(unittest.TestCase):
    # These sets come from the GitHub CLI manuals:
    # https://cli.github.com/manual/gh_issue_list and https://cli.github.com/manual/gh_pr_list.
    ISSUE_JSON_FIELDS = {
        "assignees", "author", "body", "closed", "closedAt", "closedByPullRequestsReferences",
        "comments", "createdAt", "id", "isPinned", "labels", "milestone", "number",
        "projectCards", "projectItems", "reactionGroups", "state", "stateReason", "title", "updatedAt", "url",
    }
    PR_JSON_FIELDS = {
        "additions", "assignees", "author", "baseRefName", "baseRefOid", "body", "changedFiles",
        "closed", "closedAt", "closingIssuesReferences", "commits", "createdAt", "deletions", "files",
        "fullDatabaseId", "headRefName", "headRefOid", "id", "isCrossRepository", "isDraft", "labels",
        "latestReviews", "maintainerCanModify", "mergeCommit", "mergeStateStatus", "mergeable", "mergedAt",
        "mergedBy", "milestone", "number", "projectCards", "projectItems", "reactionGroups", "reviewDecision",
        "reviewRequests", "reviews", "state", "statusCheckRollup", "title", "updatedAt", "url",
    }
    def test_every_gh_list_json_field_is_documented(self):
        # Allow-lists copied from the gh issue/pr list manuals linked in needs_you.py.
        patterns = re.compile(r"gh\s+(issue|pr)\s+list\b[^\n]*?--json\s+['\"]?([A-Za-z0-9_,]+)")
        for root in (ROOT / "src", ROOT / ".github"):
            for path in root.rglob("*"):
                if not path.is_file() or path.suffix not in {".py", ".sh", ".yml", ".yaml"}:
                    continue
                text = path.read_text(encoding="utf-8", errors="replace")
                for match in patterns.finditer(text):
                    fields = set(match.group(2).split(","))
                    allowed = self.ISSUE_JSON_FIELDS if match.group(1) == "issue" else self.PR_JSON_FIELDS
                    self.assertTrue(fields <= allowed, "%s has undocumented %s fields: %s" % (path, match.group(1), fields - allowed))

    def test_workflow_has_separate_guarded_comment_job_and_safe_body_transport(self):
        text = (ROOT / ".github/workflows/needs-you.yml").read_text()
        self.assertIn("issue_comment:", text)
        self.assertIn("types: [created]", text)
        self.assertIn("github.event.issue.title == 'Needs you'", text)
        self.assertIn("github.event.comment.user.login == github.repository_owner", text)
        self.assertIn("github.event.comment.author_association == 'OWNER'", text)
        self.assertIn("github.event.comment.user.type != 'Bot'", text)
        self.assertIn("if: github.event_name != 'issue_comment'", text)
        self.assertIn("NEEDS_YOU_COMMENT_BODY: ${{ github.event.comment.body }}", text)
        run_blocks = re.findall(r"(?ms)^\s+run:\s*(?:\|\n)?(.*?)(?=^\s+-?\s*name:|^\s+-?\s*uses:|\Z)", text)
        self.assertTrue(all("github.event.comment.body" not in block for block in run_blocks))
        self.assertIn("issues: write\n      contents: write", text)


class Ranker(unittest.TestCase):
    def test_official_first_and_better_flag_only_for_a_real_alternative(self):
        index = {"bundles": [
            {"source":"github", "repo":"community/patches", "patches":[{"name":"a", "compatiblePackagesKey":0}, {"name":"b", "compatiblePackagesKey":0}, {"name":"c", "compatiblePackagesKey":0}], "targetApps":["com.x"]},
            {"source":"github", "repo":"MorpheApp/morphe-patches", "patches":[{"name":"official", "compatiblePackagesKey":1}], "targetApps":["com.x"]},
        ], "compatibilities": [
            [{"packageName":"com.x", "targets":[{"version":"1"}]}],
            [{"packageName":"com.x", "targets":[{"version":"2"}]}],
        ]}
        target = [{"id":"x", "enabled":True, "package":"com.x", "current_version":"2", "candidates":[{"owner":"community", "repo":"patches"}]}]
        row = model.rank_providers(index, target)[0]
        self.assertEqual(row["providers"][0]["repo"], "MorpheApp/morphe-patches")
        self.assertTrue(row["better_exists"])
        self.assertTrue(row["better"][0]["supports_current"])

    def test_configured_official_provider_does_not_flag_a_weaker_other(self):
        index = {"bundles": [
            {"source":"github", "repo":"MorpheApp/morphe-patches", "patches":[{"name":"official", "compatiblePackagesKey":0}], "targetApps":["com.x"]},
            {"source":"github", "repo":"community/patches", "patches":[{"name":"a", "compatiblePackagesKey":0}], "targetApps":["com.x"]},
        ], "compatibilities": [[{"packageName":"com.x", "targets":[{"version":"2"}]}]]}
        target = [{"id":"x", "enabled":True, "package":"com.x", "current_version":"2", "candidates":[{"owner":"MorpheApp", "repo":"morphe-patches"}]}]
        self.assertFalse(model.rank_providers(index, target)[0]["better_exists"])


if __name__ == '__main__':
    unittest.main()


class GroupCommands(unittest.TestCase):
    """W16j (owner, 25 Oct 2026): answer a group, every item or every 'My call' in one line."""
    CAT = {'N-AAAAAA': {'id': 'N-AAAAAA', 'group': 'G2', 'mycall': ''},
           'N-BBBBBB': {'id': 'N-BBBBBB', 'group': 'G4', 'mycall': 'drop'},
           'N-CCCCCC': {'id': 'N-CCCCCC', 'group': 'G4', 'mycall': 'drop'},
           'N-DDDDDD': {'id': 'N-DDDDDD', 'group': 'G1', 'mycall': 'take'}}

    def test_yes_all_applies_only_my_calls_and_later_lines_win(self):
        got = dict((i, v) for v, i in n.parse_decisions('yes all\ntake N-cccccc\n', self.CAT))
        self.assertEqual(got, {'N-BBBBBB': 'drop', 'N-CCCCCC': 'take', 'N-DDDDDD': 'take'})

    def test_group_all_keep_and_prose(self):
        self.assertEqual(sorted(n.parse_decisions('keep G4\nplease do it\n', self.CAT)), [('take', 'N-BBBBBB'), ('take', 'N-CCCCCC')])
        self.assertEqual(len(n.parse_decisions('hold all', self.CAT)), 4)
        self.assertEqual(n.parse_decisions('take G9', self.CAT), [])

    def test_except_names(self):
        text = 'take N-dddddd except "Custom Morphe branding", "Official package name"'
        self.assertEqual(n.parse_decisions(text, self.CAT), [('take', 'N-DDDDDD')])
        self.assertEqual(n.parse_excepts(text), {'N-DDDDDD': ['Custom Morphe branding', 'Official package name']})

    def test_old_single_commands_still_work(self):
        self.assertEqual(n.parse_decisions('drop N-aaaaaa', ['N-AAAAAA']), [('drop', 'N-AAAAAA')])


class FalseFixItems(unittest.TestCase):
    def test_healthy_report_notes_are_not_fix_items(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d)
            (p / 'provider.md').write_text('# Provider watch: OK\n\nPatch names only: versions NOT compared; 2 missing from the index (documented)\n')
            (p / 'nightly.md').write_text('# Nightly watch: OK\n\ngg-photos Change package name: documented exception, missing on purpose\n')
            bucket = {k: [] for k in n.ORDER}
            n._source(p / 'provider.md', 'provider', bucket); n._source(p / 'nightly.md', 'nightly', bucket)
        self.assertEqual(bucket['fix'], [])

    def test_failed_headline_still_is(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / 'nightly.md'; p.write_text('# Nightly watch: FAILED\n\nreason: store unreachable\n')
            bucket = {k: [] for k in n.ORDER}
            n._source(p, 'nightly', bucket)
        self.assertEqual(len(bucket['fix']), 1)


class IndexShapes(unittest.TestCase):
    def test_patch_rows_read_both_compatibility_keys(self):
        # W16j double check: 715 index patches use compatibilityKey, not compatiblePackagesKey.
        comp = [{'a.b': ['1.0']}, {'x.y': ['2.0']}]
        bundle = {'targetApps': ['a.b', 'x.y'], 'patches': [
            {'name': 'Old', 'compatiblePackagesKey': 0}, {'name': 'New', 'compatibilityKey': 0},
            {'name': 'Other', 'compatibilityKey': 1}]}
        self.assertEqual([r[0] for r in n._patch_rows(bundle, 'a.b', comp, set())], ['Old', 'New'])
