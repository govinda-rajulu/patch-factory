"""W16o shell lane contracts: environment, scratch, transport, and helper lifecycle."""
import re
import subprocess
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class W16oShellContracts(unittest.TestCase):
    def setUp(self):
        self.build = (ROOT / 'src/build/build.sh').read_text()
        self.patcher = (ROOT / 'src/build/patch_target.py').read_text()
        self.utils = (ROOT / 'src/build/utils.sh').read_text()
        self.services = (ROOT / 'src/build/store_services.sh').read_text()
        self.tooling = (ROOT / 'src/build/tooling.sh').read_text()
        self.repin = (ROOT / 'src/build/repin.sh').read_text()
        self.attempts = (ROOT / 'src/build/build_attempts.py').read_text()

    def test_patcher_has_a_non_secret_environment_allowlist(self):
        self.assertIn('subprocess.run(args, env=child_env, check=False)', self.patcher)
        for name in ('PATH', 'HOME', 'LANG', 'LC_ALL', 'TZ', 'TMPDIR', 'JAVA_HOME', 'COE'):
            self.assertIn("'%s'" % name, self.patcher)
        allow = self.patcher.split('allowed =', 1)[1].split('child_env', 1)[0]
        self.assertNotIn('KEYSTORE_PASS', allow)
        self.assertNotIn('GITHUB_TOKEN', allow)

    def test_build_and_controller_use_private_scratch(self):
        self.assertRegex(self.build, r'mktemp -d .*pf-build\.XXXXXX')
        self.assertIn('trap pf_build_cleanup EXIT', self.build)
        for old in ('/tmp/patch.log', '/tmp/applied.txt', '/tmp/requested.txt', '/tmp/missing.txt'):
            self.assertNotIn(old, self.build)
        self.assertIn('tempfile.mkdtemp(prefix=\'pf-attempts-\'', self.attempts)
        self.assertIn('atexit.register(shutil.rmtree', self.attempts)
        self.assertNotIn('/tmp/cfb_response_headers.txt', self.utils)
        self.assertIn('mktemp "$PF_TMP_DIR/cfb-headers.XXXXXX"', self.utils)

    def test_store_transport_is_https_bounded_and_host_checked(self):
        self.assertIn("--proto '=https'", self.utils)
        self.assertIn("--proto-redir '=https'", self.utils)
        self.assertIn('--max-redirs 10', self.utils)
        self.assertIn('--max-filesize', self.utils)
        self.assertIn('pf_store_url_check "$final_url"', self.utils)
        self.assertIn('pf_store_url_check "$download_url"', self.utils)
        self.assertIn('STORE_FINAL_HOST', self.utils)
        self.assertIn('effective_file=$(mktemp', self.utils)
        self.assertIn("--write-out '%{url_effective}'", self.utils)
        transfer = self.utils.split('pf_curl_store_transfer() {', 1)[1].split('\n}', 1)[0]
        self.assertNotIn('--max-time 120', transfer)
        self.assertIn('--connect-timeout 30', self.utils)
        self.assertIn('--speed-limit 1024', self.utils)
        self.assertIn('--speed-time 120', self.utils)
        self.assertIn('--retry 5', self.utils)
        self.assertIn('--retry-delay 5', self.utils)
        self.assertIn('--retry-connrefused', self.utils)
        self.assertIn('candidate_bytes=$(stat -c %s -- "$dest")', self.utils)
        self.assertIn('candidate_bytes" -gt "$max_bytes"', self.utils)

    def test_store_effective_url_has_no_preflight_request_or_final_host_allowlist(self):
        check = self.utils.split('pf_store_url_check() {', 1)[1].split('\n}', 1)[0]
        self.assertNotIn('curl', check)
        transfer = self.utils.split('pf_curl_store_transfer() {', 1)[1].split('\n}', 1)[0]
        self.assertNotIn('apkmirror.com', transfer)
        self.assertNotIn('apkpure.com', transfer)
        self.assertIn('pf_curl_effective_host_ok "$effective" "$store"', transfer)

    def test_store_cookie_follows_redirects_like_wget(self):
        # W16o round 3 (wrong call 82): curl drops a raw Cookie header on a cross-host
        # redirect; wget sent it on every request. --cookie NAME=VALUE data is passed on.
        transfer = self.utils.split('pf_curl_store_transfer() {', 1)[1].split('\n}', 1)[0]
        self.assertIn('[[ "${FS_COOKIES:-}" == *=* ]] && cookie_args=(--cookie "$FS_COOKIES")', transfer)
        self.assertNotIn('Cookie: ', transfer.replace('raw --header Cookie', ''))
        self.assertNotIn('--location-trusted', transfer)

    def run_fn(self, text, name, *args):
        # W16o round 4 (mutation test): run the real shell function, not a string match.
        body = name + '() {' + text.split(name + '() {', 1)[1].split('\n}\n', 1)[0] + '\n}\n'
        return subprocess.run(['bash', '-c', body + name + ' "$@"', 'x', *args],
                              capture_output=True, text=True).returncode

    def test_store_final_host_rejects_credentials_ports_and_http(self):
        ok = 'https://Downloads.Example.COM./a.apk'
        self.assertEqual(self.run_fn(self.utils, 'pf_curl_effective_host_ok', ok, 'apkmirror'), 0)
        self.assertEqual(self.run_fn(self.utils, 'pf_curl_effective_host_ok', 'https://cdn.example.com:443/a', 's'), 0)
        for bad in ('https://user:pass@cdn.example.com/a', 'https://cdn.example.com:8443/a',
                    'http://cdn.example.com/a', 'https:///a'):
            self.assertNotEqual(self.run_fn(self.utils, 'pf_curl_effective_host_ok', bad, 's'), 0, bad)

    def test_tool_redirect_hosts_reject_any_other_host(self):
        for text in (self.tooling, self.repin):
            for good in ('https://github.com/o/r/releases/download/v1/a.jar',
                         'https://release-assets.githubusercontent.com/x',
                         'https://objects.githubusercontent.com/x'):
                self.assertEqual(self.run_fn(text, 'github_effective_host_ok', good), 0, good)
            for bad in ('https://evil.example.com/x', 'https://github.com.evil.example/x',
                        'https://user@github.com/x', 'http://github.com/x'):
                self.assertNotEqual(self.run_fn(text, 'github_effective_host_ok', bad), 0, bad)

    def test_patcher_child_env_is_built_only_from_the_allowlist(self):
        self.assertIn('child_env = {key: os.environ[key] for key in allowed if key in os.environ}', self.patcher)
        for wide in ('os.environ.copy()', 'dict(os.environ', 'env=os.environ'):
            self.assertNotIn(wide, self.patcher)

    def test_store_transfer_rejects_an_empty_candidate(self):
        transfer = self.utils.split('pf_curl_store_transfer() {', 1)[1].split('\n}', 1)[0]
        self.assertIn('"$candidate_bytes" -eq 0 ||', transfer)

    def test_store_temp_rename_failure_is_a_failure(self):
        self.assertNotRegex(self.utils, r'mv -f -- "\$transfer_(tmp|path)" "\./download/\$output_base_apk"(;|\n)')

    def test_apkmirror_transfer_is_the_base_wget_request_with_local_checks(self):
        # W16o smoke run 40398219589 (wrong call 84): curl got 403 from APKMirror's download
        # endpoint on 8 of 14 apps; the base wget request built 17 of 17. Same request, local checks.
        import tempfile
        self.assertIn('pf_wget_store_transfer "$final_url" "$transfer_path" "$base_url$dl_btn_href" "$user_agent" || wrc=$?', self.utils)
        self.assertNotIn('"$user_agent" apkmirror', self.utils)
        fn = 'pf_wget_store_transfer() {' + self.utils.split('pf_wget_store_transfer() {', 1)[1].split('\n}\n', 1)[0] + '\n}\n'
        with tempfile.TemporaryDirectory() as d:
            d = Path(d); (d / 'bin').mkdir()
            (d / 'bin/wget').write_text('#!/bin/bash\nprintf "%s\\n" "$@" > "$ARGS_OUT"\nout=""; while [ $# -gt 0 ]; do [ "$1" = -O ] && out=$2; shift; done\n'
                                       'case "$MODE" in fail) exit 8;; empty) : > "$out";; *) printf apk > "$out";; esac\n')
            (d / 'bin/wget').chmod(0o755)
            def run(mode):
                env = dict(PATH=str(d / 'bin') + ':/usr/bin:/bin', MODE=mode, ARGS_OUT=str(d / 'args'), FS_COOKIES='cf=1; s=2')
                script = 'pf_store_size_limit_bytes() { echo 1000; }\n' + fn + 'pf_wget_store_transfer https://www.apkmirror.com/x "$1" https://www.apkmirror.com/r UA-1; echo "rc=$?"'
                out = subprocess.run(['bash', '-c', script, 'x', str(d / 'apk')], env=env, capture_output=True, text=True).stdout
                return out.strip().splitlines()[-1], (d / 'apk').exists()
            self.assertEqual(run('ok'), ('rc=0', True))
            args = (d / 'args').read_text().splitlines()
            for want in ('-q', '--header=User-Agent: UA-1', '--referer=https://www.apkmirror.com/r',
                         '--header', 'Cookie: cf=1; s=2', '--timeout=120', 'https://www.apkmirror.com/x'):
                self.assertIn(want, args)
            self.assertEqual(run('empty'), ('rc=1', False))
            self.assertEqual(run('fail'), ('rc=8', False))

    def test_docker_helpers_are_loopback_fail_closed_and_cleaned(self):
        self.assertIn('-p "127.0.0.1:$port:$port"', self.services)
        self.assertIn('return 1', self.services[self.services.index('docker run'):])
        self.assertIn('if ! wait_healthy "$name"', self.services)
        self.assertIn('docker rm -f flaresolverr cloudflarebypass', self.services)
        self.assertIn('c80ae007ce2ccdcd217a12426e4f039ef763ff90738c808d38810c3e59323767', self.services)

    def test_tooling_is_atomic_bounded_https_and_repin_is_confirmed(self):
        for text in (self.tooling, self.repin):
            self.assertIn("--proto '=https'", text)
            self.assertIn("--proto-redir '=https'", text)
            self.assertIn('--max-filesize', text)
        self.assertIn('mktemp "$OUT_DIR/.${OUT_BASE}.XXXXXX"', self.tooling)
        self.assertIn('mv -f -- "$TMP" "$OUT"', self.tooling)
        self.assertIn('[ "${1:-}" = "--confirm-repin" ]', self.repin)

    def test_enforced_store_curl_options_exist_in_installed_downloader(self):
        block = self.utils.split('pf_curl_store_transfer() {', 1)[1].split('\n}', 1)[0]
        options = sorted(set(re.findall(r'--[a-z][a-z-]*', block)))
        help_text = subprocess.check_output(['curl', '--help', 'all'], text=True)
        for option in options:
            self.assertRegex(help_text, r'(?m)(?:^|[ ,])' + re.escape(option) + r'(?:[\s,]|$)', option)

    def test_prepared_source_callers_inherit_default_transport_enforcement(self):
        self.assertIn(': "${PF_ENFORCE_EFFECTIVE_URL:=1}"', self.utils)
        for name in ('source_download.sh', 'source_alternate.sh'):
            text = (ROOT / 'src/build' / name).read_text()
            self.assertLess(text.index('source ./src/build/utils.sh'), text.index('get_apk "'))
        self.assertIn('pf_curl_store_transfer', self.utils)

    def test_tooling_redirect_hosts_are_allowlisted(self):
        for text in (self.tooling, self.repin):
            for host in ('github.com', 'objects.githubusercontent.com', 'release-assets.githubusercontent.com'):
                self.assertIn(host, text)
            self.assertIn('url_effective', text)

    def test_workflow_has_no_floating_apt_install(self):
        workflow = (ROOT / '.github/workflows/validate.yml').read_text()
        self.assertNotIn('apt-get install', workflow)
        self.assertIn('sec-wf-b', workflow)


if __name__ == '__main__':
    unittest.main()
