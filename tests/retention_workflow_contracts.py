"""The weekly retention workflow is preview-first and owner-confirmed."""
import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
WF = ROOT / '.github/workflows/retention.yml'


class RetentionWorkflow(unittest.TestCase):
    text = WF.read_text(encoding='utf-8')

    def test_weekly_schedule_dispatch_inputs_and_nonoverlap(self):
        self.assertRegex(self.text, r'cron: "[^" ]+ [^" ]+ \* \* 1"')
        self.assertIn('workflow_dispatch:', self.text)
        self.assertIn('token:', self.text)
        self.assertIn('confirm:', self.text)
        self.assertIn('group: retention-preview', self.text)
        self.assertIn('cancel-in-progress: false', self.text)

    def test_preview_issue_contains_counts_bytes_list_and_token(self):
        self.assertIn("title='Retention preview'", self.text)
        self.assertIn('Open or update the one standing preview issue', self.text)
        self.assertIn('release_asset_bytes', self.text)
        self.assertIn("TOKEN {p[\'token\']}", self.text)
        self.assertIn('Delete list', self.text)
        self.assertIn('state=all', self.text)

    def test_schedule_path_is_preview_only_and_apply_is_owner_exact_confirmation(self):
        self.assertIn('Scheduled runs never apply deletes.', self.text)
        self.assertRegex(self.text, r"github\.event_name == 'workflow_dispatch'.*github\.actor == github\.repository_owner.*inputs\.confirm == 'apply'.*inputs\.token != ''")
        self.assertIn('test \"$GITHUB_ACTOR\" = \"$GITHUB_REPOSITORY_OWNER\"', self.text)
        self.assertIn('test "$CONFIRM" = apply', self.text)
        self.assertIn('cleanup.py apply --token "$TOKEN"', self.text)
        self.assertIn('cleanup.py preview --out cleanup-preview.json', self.text)

    def test_permissions_keep_contents_write_on_apply_job_only(self):
        preview = self.text.split('  apply:', 1)[0]
        apply = self.text.split('  apply:', 1)[1]
        self.assertIn('contents: read', preview)
        self.assertNotIn('contents: write', preview)
        self.assertIn('contents: write', apply)
        self.assertIn('issues: write', preview)
        self.assertIn('issues: read', apply)
        self.assertIn('Wait for the main Pages deployment to settle', self.text)
        self.assertIn('/deployments/$id/statuses', self.text)


if __name__ == '__main__':
    unittest.main()
