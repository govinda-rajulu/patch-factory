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


class Renderer(unittest.TestCase):
    def test_empty_day_is_one_plain_line(self):
        with tempfile.TemporaryDirectory() as d:
            paths = {}
            for name in n.ISSUES:
                p = Path(d) / (name + '.md'); p.write_text('# report: OK\n'); paths[name] = p
            body = n.render(paths)
        self.assertIn('## Keep building', body)
        self.assertIn('N-', body)
        self.assertIn('take N-xxxxxx', body)

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
        self.assertLess(body.index('## Decide'), body.index('## Install'))
        self.assertLess(body.index('## Install'), body.index('## Fix'))
        self.assertIn('## FYI', body)
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
        self.assertIn("## Decide", body)
        self.assertIn("## Install", body)
        self.assertIn("## Fix", body)
        self.assertIn("## FYI", body)
        self.assertIn("decide whether to add", body)
        self.assertIn("install any update", body)
        self.assertIn("Nightly reported", body)
        self.assertIn("Provider reported", body)

    def test_changed_issue_edits_then_comments_and_unchanged_is_quiet(self):
        calls = []
        def run(args, **kwargs):
            calls.append(args)
            if args[1:3] == ['issue', 'list']:
                return SimpleNamespace(returncode=0, stdout=json.dumps([{'number': 9, 'title': 'Needs you', 'body': 'old', 'author': {'is_bot': True, 'login': 'github-actions[bot]'}}]), stderr='')
            return SimpleNamespace(returncode=0, stdout='', stderr='')
        self.assertEqual(n.deliver('new\n', run=run), 'EDITED')
        self.assertEqual([x[1:3] for x in calls], [['issue', 'list'], ['issue', 'edit'], ['issue', 'comment']])
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

    def test_effect_mapping_is_review_only(self):
        self.assertEqual(n._review_item({"kind": "review", "first_line": "review: x"}), True)
        self.assertEqual(n._review_item({"kind": "community", "first_line": "review: x"}), False)


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
