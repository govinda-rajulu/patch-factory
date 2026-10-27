"""W16p carry contracts for bounded stores and packet controller identity."""
import os
import subprocess
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
UTILS = (ROOT / 'src/build/utils.sh').read_text(encoding='utf-8')
CONTROLLER = (ROOT / 'docs/review/controllers/packet.tmpl.py').read_text(encoding='utf-8')


def function(text, name):
    start = text.index(name + '() {')
    end = text.index('\n}\n', start) + 3
    return text[start:end]


def run_function(text, name, *args, env=None):
    script = function(text, name) + '\n' + name + ' "$@"\n'
    merged = dict(os.environ, **(env or {}))
    return subprocess.run(['bash', '-c', script, 'test', *args], capture_output=True,
                          text=True, env=merged)


class UtilsCarryContracts(unittest.TestCase):
    def test_flaresolverr_post_has_deadlines_above_request_timeout(self):
        block = UTILS[UTILS.index('_fs_get() {'):UTILS.index('\n_cfb_get() {')]
        self.assertIn("--connect-timeout 5 --max-time 180 -X POST 'http://localhost:8191/v1'", block)
        self.assertIn('maxTimeout:60000', block)
        self.assertIn('starts its browser before applying maxTimeout', block)
        self.assertIn('FlareSolverr/FlareSolverr/blob/v3.5.2/README.md', block)

    def test_store_size_units_match_curl_and_reject_t_and_p_clearly(self):
        for value, expected in (('1', '1'), ('1B', '1'), ('2k', str(2 * 1024)),
                                ('3M', str(3 * 1024 ** 2)), ('4g', str(4 * 1024 ** 3))):
            result = run_function(UTILS, 'pf_store_size_limit_bytes', env={'PF_STORE_MAX_BYTES': value})
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(result.stdout.strip(), expected)
        for value in ('1T', '1P', '1E', '1MB'):
            result = run_function(UTILS, 'pf_store_size_limit_bytes', env={'PF_STORE_MAX_BYTES': value})
            self.assertNotEqual(result.returncode, 0, value)
            self.assertIn('PF_STORE_MAX_BYTES', result.stderr)

    def test_apkpure_final_host_known_and_unknown_are_observed(self):
        known = run_function(UTILS, 'pf_curl_effective_host_ok',
                             'https://data.winudf.com/a.apk', 'apkpure')
        self.assertEqual(known.returncode, 0, known.stderr)
        self.assertIn('STORE_FINAL_HOST apkpure data.winudf.com', known.stdout)
        self.assertNotIn('::warning::', known.stdout)
        unknown = run_function(UTILS, 'pf_curl_effective_host_ok',
                               'https://cdn.example.test/a.apk', 'apkpure')
        self.assertEqual(unknown.returncode, 0, unknown.stderr)
        self.assertIn('::warning::', unknown.stdout)
        self.assertIn('cdn.example.test', unknown.stdout)

    def test_apkpure_curl_failure_is_not_reported_as_wget(self):
        start = UTILS.index('get_apkpure() {')
        branch_start = UTILS.rindex('\tif [[ "${PF_ENFORCE_EFFECTIVE_URL:-0}" == "1" ]]', start, UTILS.index('\n}', start))
        branch_end = UTILS.index('\n\telse\n', branch_start)
        branch = UTILS[branch_start:branch_end]
        self.assertIn('curl_exit=', branch)
        self.assertNotIn('wget_exit=', branch)
        self.assertNotIn('pf_wget_meaning', branch)


class ControllerCarryContracts(unittest.TestCase):
    def test_publish_lookup_matches_merge_sha_and_display_title(self):
        start = CONTROLLER.index('def publish_dispatch(')
        end = CONTROLLER.index('\ndef watch_dispatch(', start)
        body = CONTROLLER[start:end]
        self.assertIn("expected_title = 'Batch %s / publish=true' % ','.join(PUBLISH_DISPATCH)", body)
        self.assertIn("r.get('head_sha') == merge_sha", body)
        self.assertIn("r.get('display_title') == expected_title", body)
        self.assertNotIn('found = rows[-1]', body)

    def test_github_committer_exception_requires_two_parents(self):
        body = CONTROLLER[CONTROLLER.index('def drift_tree('):CONTROLLER.index('\ndef clone(', CONTROLLER.index('def drift_tree('))]
        self.assertIn('(r[2] == MERGER_MAIL and len(r) == 5)', body)


if __name__ == '__main__':
    unittest.main()
