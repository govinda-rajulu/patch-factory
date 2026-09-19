"""Regression checks for critical operating guidance; not proof every sentence is current."""
from pathlib import Path
import re
import unittest

ROOT=Path(__file__).resolve().parents[1]

class OperationalDocs(unittest.TestCase):
    def text(self,name):return (ROOT/name).read_text()

    def test_readme_identity_and_delivery_limits(self):
        text=self.text('README.md')
        for phrase in ('PREFIX-vAPPVERSION-bBUILDID','APPVERSION only','whole source workflow succeeds',
                       'shadow evidence','publish=false','Rebuild first, cleanup last'):
            self.assertIn(phrase,text)
        self.assertNotIn('PREFIX-vAPPVERSION-bYYYYMMDD',text)
        self.assertNotIn('Setting `"any_version": true`',text)

    def test_recovery_is_not_destructive_install_recipe(self):
        text=self.text('RECOVERY.md')
        for phrase in ('not permission to dispatch','No backup location or restore success',
                       'not a retrievable backup','Do not rotate the key','exact cleanup preview',
                       'truecaller-v26.10.6','whole source run'):
            self.assertIn(phrase,text)
        for phrase in ('turn Play Protect scanning off','Uninstall freely',
                       '3-4 phone verifications','ONE copy today','max_patch_age_days` is 60'):
            self.assertNotIn(phrase,text)

    def test_security_separates_trust(self):
        text=self.text('SECURITY.md')
        for phrase in ('decoded on the runner','not independent authenticity',
                       'CONFIRM warns','not a retrievable backup',
                       'individually private','not establish behavioral compatibility'):
            self.assertIn(phrase,text)
        self.assertNotIn('never leaves the owner.\n',text)

    def test_pending_decisions_not_lost(self):
        text=self.text('docs/review/OPEN-WORK.md')
        for phrase in ('Six unresolved CONFIRM','APK Junk Cleanup','Remove Duplicate',
                       'Remove Languages','esfile-ftl','mxplayer-ftl','APPVERSION-only',
                       'Remember live stream playback position','original semantic poller',
                       'Reddit recovery is not established','independent provenance',
                       'phone validation','PR53'):
            self.assertIn(phrase,text)

    def test_local_document_links_exist(self):
        for name in ('README.md','RECOVERY.md','SECURITY.md','docs/review/OPEN-WORK.md'):
            text=self.text(name)
            for link in re.findall(r'\[[^\]]+\]\(([^)]+)\)',text):
                if '://' in link or link.startswith('#'):continue
                with self.subTest(name=name,link=link):
                    self.assertTrue(((ROOT/name).parent/link.split('#')[0]).is_file())

    def test_no_mutating_copy_paste_commands_in_new_guidance(self):
        for name in ('README.md','RECOVERY.md','SECURITY.md','docs/review/OPEN-WORK.md'):
            text=self.text(name)
            for forbidden in ('gh workflow run ','gh release delete ','gh secret set ',
                              'git push --force','gh run rerun '):
                self.assertNotIn(forbidden,text)
