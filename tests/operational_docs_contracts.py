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
        for phrase in ('Six resource-reduction selections excluded','APK Junk Cleanup','Remove Duplicate',
                       'Remove Languages','esfile-ftl','mxplayer-ftl','APPVERSION-only',
                       'Remember live stream playback position','original semantic poller',
                       'Reddit recovery is not established','independent provenance',
                       'phone validation','PR53'):
            self.assertIn(phrase,text)

    def test_local_document_links_exist(self):
        for name in ('README.md','RECOVERY.md','SECURITY.md','docs/review/OPEN-WORK.md',
                     'docs/guide.md','docs/companions.md'):
            text=self.text(name)
            for link in re.findall(r'\[[^\]]+\]\(([^)]+)\)',text):
                if '://' in link or link.startswith('#'):continue
                with self.subTest(name=name,link=link):
                    self.assertTrue(((ROOT/name).parent/link.split('#')[0]).is_file())

    def test_no_mutating_copy_paste_commands_in_new_guidance(self):
        for name in ('README.md','RECOVERY.md','SECURITY.md','docs/review/OPEN-WORK.md',
                     'docs/guide.md','docs/companions.md'):
            text=self.text(name)
            for forbidden in ('gh workflow run ','gh release delete ','gh secret set ',
                              'git push --force','gh run rerun '):
                self.assertNotIn(forbidden,text)

    def test_companions_are_discoverable_and_separate_from_build_targets(self):
        self.assertIn('(docs/companions.md)',self.text('README.md'))
        self.assertIn('(companions.md)',self.text('docs/guide.md'))
        text=self.text('docs/companions.md')
        for phrase in ('There is no PotHelper one-click import in this PR',
                       'No native-code vendoring, bundling or re-signing',
                       'not a full implementation or',
                       'Leave VirusTotal disabled',
                       'Host metadata is not independent authenticity',
                       'same-version delivery'):
            self.assertIn(phrase,text)
        import json
        targets=json.loads(self.text('src/targets.json'))
        self.assertEqual(sum(t.get('enabled') is True for t in targets),14)
        self.assertNotIn('pothelper',{t['id'] for t in targets})
        self.assertNotIn('helper-for-morphe',{t['id'] for t in targets})

    def test_companion_source_revisions_and_unreviewed_queue_are_retained(self):
        text=self.text('docs/companions.md')
        for source in (
            'MorpheApp/PotHelper/blob/0d4d9b4b4b335b2732c28b8ccd3df9b4b4870410/README.md',
            'rushiranpise/helper-for-morphe/blob/8b0c487efdfbda24bb8fe4acb4693c7089b5522e/README.md',
            'deniscerri/ytdlnis','javiersantos/MLManager','Domilopment/apk-extractor',
            'alexcmgit/kanade','AuroraOSS/AuroraStore','AuroraOSS/auroradroid',
            'fdroid/fdroidclient','Droid-ify/client','sunilpaulmathew/izzyondroid',
            'NeoApplications/Neo-Store','accrescent/accrescent','komi-store/komi-store',
            'thedjchi/Shizuku','wxxsfxyzm/InstallerX-Revived',
            'pass-with-high-score/universal-installer','samolego/Canta',
            'aistra0528/Hail','YasserNull/shappky','adil192/no_more_background',
            'AhmetCanArslan/ShizuWall','MorpheApp/morphe-manager','MorpheApp/morphe-desktop'):
            self.assertIn(source,text)
        self.assertIn('not verified on a device',text)
        self.assertIn('no current release, license, package, signer or device behavior was',text)

    def test_credits_preserve_upstream_notice_and_no_copy_boundary(self):
        text=self.text('CREDITS.md')
        for phrase in ('FiorenMas/Revanced-And-Revanced-Extended-Non-Root',
                       '733e91b6fe90dace2295ac6a27ca66481c945e7d',
                       'PR168/churn','public signing material','broad CI permissions',
                       'Morphe NOTICE','Link third-party text/assets instead of copying them',
                       'AuroraStore','AGPL-3.0','markdown-badges'):
            self.assertIn(phrase,text)
        self.assertNotIn('totally safe',text.lower())

    def test_guide_matches_live_companion_controls(self):
        from html.parser import HTMLParser
        class Controls(HTMLParser):
            def __init__(self):
                super().__init__()
                self.ids=set()
                self.options={}
                self.select=None
            def handle_starttag(self,tag,attrs):
                a=dict(attrs)
                if 'id' in a:self.ids.add(a['id'])
                if tag=='select':self.select=a.get('id')
                if tag=='option' and self.select:
                    self.options.setdefault(self.select,set()).add(a.get('value'))
            def handle_endtag(self,tag):
                if tag=='select':self.select=None
        c=Controls();c.feed(self.text('docs/index.html'))
        self.assertIn('includeObtainium',c.ids)
        self.assertEqual(c.options['microgArch'],
                         {'universal','auto','arm64-v8a','armeabi-v7a'})
        text=self.text('docs/guide.md')
        for phrase in ('Include Obtainium self-update','Universal (recommended)',
                       'Auto architecture','ARM64','ARMv7','dev.imranr.obtainium.fdroid',
                       'you must also select its row','already patched'):
            self.assertIn(phrase,text)
        self.assertNotIn('using the standard universal APK.',text)

    def test_no_unreviewed_companion_import_added(self):
        import json
        paths=sorted(p.name for p in (ROOT/'docs').glob('obtainium*.json'))
        self.assertEqual(paths,['obtainium-microg.json','obtainium-self.json','obtainium.json'])
        main=json.loads(self.text('docs/obtainium.json'))['apps']
        self.assertEqual(len(main),14)
        extra=json.loads(self.text('docs/obtainium-self.json'))['apps']
        self.assertEqual([a['id'] for a in extra],['dev.imranr.obtainium'])
