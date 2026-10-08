"""Selection-name check: exact provider bundles, never a URL reader; unreadable is UNVERIFIED."""
import importlib.util
import json
import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('selection_names', ROOT / 'src/etc/selection_names.py')
sn = importlib.util.module_from_spec(spec)
spec.loader.exec_module(sn)


class SelectionNames(unittest.TestCase):
    def run_check(self, observe):
        out = []
        result = sn.check(ROOT, observe, out.append)
        return result, '\n'.join(out)

    def offered(self, row):
        inc = sn.lines(ROOT / 'src/patches' / row['patch_dir'] / 'include-patches')
        return {'names': sorted(set(inc) | {'Change package name', 'Unused extra'})}

    def test_every_candidate_and_extra_is_checked_including_gitlab(self):
        rows = sn.provider_watch.inventory(json.loads((ROOT / 'src/targets.json').read_text()))
        self.assertTrue(any(r['host'] == 'gitlab' for r in rows))
        self.assertTrue(any(r['role'] == 'extra' for r in rows))
        (checked, missing, unverified), text = self.run_check(self.offered)
        self.assertEqual((checked, missing, unverified), (len(rows), 0, 0))
        self.assertIn('checked=%d dirs_with_missing_names=0 not_checked=0' % len(rows), text)
        self.assertIn('BAN  Change package name', text)

    def test_missing_include_name_fails_and_is_named(self):
        def observe(row):
            names = self.offered(row)['names']
            if row['patch_dir'] == 'facebook-derevanced':
                names = [n for n in names if n != 'Disable all ads']
            return {'names': names}
        (checked, missing, unverified), text = self.run_check(observe)
        self.assertEqual(missing, 1)
        self.assertIn('-- facebook/facebook-derevanced MISSING: Disable all ads', text)

    def test_unreadable_provider_is_unverified_never_ok(self):
        def observe(row):
            if row['target'] == 'edge':
                raise sn.provider_watch.WatchError('LIST_COMMAND_FAILED')
            if row['target'] == 'reddit':
                raise RuntimeError('raw provider text SECRET')
            return self.offered(row)
        (checked, missing, unverified), text = self.run_check(observe)
        self.assertEqual(unverified, 2)
        self.assertIn('?? edge/edge-quantavil: provider list unreadable - UNVERIFIED (LIST_COMMAND_FAILED)', text)
        self.assertIn('UNVERIFIED (RuntimeError)', text)
        self.assertNotIn('SECRET', text)
        self.assertNotIn('ok edge/', text)

    def test_stale_exclude_is_reported_not_failed(self):
        def observe(row):
            names = self.offered(row)['names']
            if row['patch_dir'] == 'facebook-derevanced':
                names = [n for n in names if n != 'Change package name']
            return {'names': names}
        (checked, missing, unverified), text = self.run_check(observe)
        self.assertEqual(missing, 0)
        self.assertIn('~~ facebook/facebook-derevanced exclude not offered by provider: Change package name', text)

    def test_clean_output_reads_as_partial_in_the_nightly_consumer(self):
        # The producer's own summary once said "unverified=0", which the Nightly consumer
        # (case-insensitive UNVERIFIED match) read as incomplete. Check producer to consumer.
        spec2 = importlib.util.spec_from_file_location('nightly_report', ROOT / 'src/etc/nightly_report.py')
        nr = importlib.util.module_from_spec(spec2)
        spec2.loader.exec_module(nr)
        env = {'GITHUB_REPOSITORY': 'govinda-rajulu/patch-factory', 'GITHUB_SHA': 'a' * 40,
               'GITHUB_RUN_ID': '1', 'GITHUB_RUN_ATTEMPT': '1'}
        targets = json.loads((ROOT / 'src/targets.json').read_text())
        _, text = self.run_check(self.offered)
        _, d = nr.analyze(text + '\nreport mode=full fail=0\n', 0, True, targets, env)
        self.assertEqual((d['status'], d['reasons']), ('PARTIAL', []))
        def broken(row):
            raise sn.provider_watch.WatchError('NO_PATCH_NAMES')
        _, text = self.run_check(broken)
        _, d = nr.analyze(text + '\nreport mode=full fail=0\n', 0, True, targets, env)
        self.assertEqual(d['status'], 'UNKNOWN')

    def test_name_check_lists_universal_patches_and_watch_argv_is_unchanged(self):
        # 29 Sep 2026: with "-x -u" the live check called ES "Remove Ads" missing, although
        # the 28 Sep ES release applied it. The watch keeps its recorded argv; the check drops them.
        watch = sn.provider_watch.Observer(ROOT, ROOT / 'unused')
        self.assertEqual(watch.listing_argv('p.jar', 'b.mpp', 'com.x'),
                         ['java', '-jar', 'p.jar', 'list-patches', '--patches=b.mpp', '-x', '-u',
                          '--with-packages', '--with-versions', '-f', 'com.x'])
        check = sn.provider_watch.Observer(ROOT, ROOT / 'unused', flags=())
        self.assertEqual(check.listing_argv('p.jar', 'b.mpp', 'com.x'),
                         ['java', '-jar', 'p.jar', 'list-patches', '--patches=b.mpp',
                          '--with-packages', '--with-versions', '-f', 'com.x'])
        self.assertIn('Observer(ROOT, Path(work), flags=())', (ROOT / 'src/etc/selection_names.py').read_text())

    def test_include_options_suffix_is_not_part_of_the_name(self):
        path = ROOT / 'src/patches/youtube-morphe/include-patches'
        self.assertEqual(sn.lines(path), [l.split('|', 1)[0] for l in path.read_text().splitlines() if l.strip()])

    def test_nightly_uses_exact_bundles_and_authenticated_release_read(self):
        report = (ROOT / 'src/etc/report.sh').read_text()
        self.assertIn('python3 src/etc/selection_names.py || FAIL=1', report)
        self.assertIn('curl -sfS "${RAUTH[@]}" "https://api.github.com/repos/govinda-rajulu/patch-factory/releases', report)
        for path in sorted((ROOT / 'src/etc').glob('*.sh')):
            self.assertNotRegex(path.read_text(), r'--patches="?https://', path.name)
        self.assertNotIn('--patches=https://', (ROOT / 'src/etc/selection_names.py').read_text())


if __name__ == '__main__':
    unittest.main()
