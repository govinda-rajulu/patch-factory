"""W15b: the APKMirror transfer names wget's exit code and retries once (Photos, run 38643057188).

Runs the shipped loop from src/build/utils.sh against a fake wget; never the network."""
import os
import re
import subprocess
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TEXT = (ROOT / 'src/build/utils.sh').read_text(encoding='utf-8')
MEANING = re.search(r'(?ms)^pf_wget_meaning\(\) \{.*?^\}\n', TEXT).group(0)
LOOP = re.search(r'(?ms)^\tlocal wrc=0 try.*?\n\tif \[\[ "\$wrc" -ne 0 \]\]; then\n.*?\n\tfi\n', TEXT).group(0)


def run(plan):
    with tempfile.TemporaryDirectory() as d:
        Path(d, 'download').mkdir()
        Path(d, 'bin').mkdir()
        Path(d, 'plan').write_text(plan)
        Path(d, 'bin/wget').write_text('#!/bin/bash\nn=$(head -c1 plan); tail -c +2 plan > p2; mv p2 plan\nfor a; do case "$prev" in -O) out=$a;; esac; prev=$a; done\nif [ "$n" = 0 ]; then echo apk > "$out"; exit 0; fi\necho partial > "$out"; exit "$n"\n')
        Path(d, 'bin/wget').chmod(0o755)
        Path(d, 'bin/sleep').write_text('#!/bin/bash\nexit 0\n')
        Path(d, 'bin/sleep').chmod(0o755)
        body = ('red_log(){ echo "$*"; }\n' + MEANING + 'f(){\nlocal base_apk=x.apk user_agent=u base_url=b dl_btn_href=/r final_href=/f\n'
                'local cookie_args=()\n' + LOOP + 'echo DONE\n}\nf\n')
        r = subprocess.run(['bash', '-c', body], cwd=d, capture_output=True, text=True,
                           env=dict(os.environ, PATH=d + '/bin:' + os.environ['PATH']), timeout=30)
        return r.returncode, r.stdout, Path(d, 'download/x.apk').exists()


class TransferRetry(unittest.TestCase):
    def test_first_failure_is_named_then_retried(self):
        code, out, kept = run('80')
        self.assertIn('TRANSFER_FAILED store=apkmirror try=1 wget_exit=8 meaning=server-error-response', out)
        self.assertIn('DONE', out)
        self.assertTrue(kept)

    def test_two_failures_refuse_and_leave_no_partial_file(self):
        code, out, kept = run('44')
        self.assertIn('try=2 wget_exit=4 meaning=network-failure', out)
        self.assertIn('APKMirror transfer failed; refusing partial or empty output', out)
        self.assertNotIn('DONE', out)
        self.assertFalse(kept)

    def test_success_prints_nothing_extra(self):
        code, out, kept = run('0')
        self.assertNotIn('TRANSFER_FAILED', out)
        self.assertTrue(kept)

    def test_apkpure_curl_failure_is_counted_and_partial_is_removed(self):
        start = TEXT.index('get_apkpure() {')
        branch_start = TEXT.rindex('\tif [[ "${PF_ENFORCE_EFFECTIVE_URL:-0}" == "1" ]]', start, TEXT.index('\n}', start))
        branch_end = TEXT.index('\n\telse\n', branch_start)
        branch = TEXT[branch_start:branch_end]
        with tempfile.TemporaryDirectory() as d:
            candidate = Path(d) / 'candidate.apk'
            body = """red_log(){ echo "$*"; }
PF_ENFORCE_EFFECTIVE_URL=1
pf_curl_store_transfer(){ printf partial > "$2"; return 28; }
f(){
local download_url=https://data.winudf.com/a.apk transfer_path=%s dl_page_url=https://apkpure.com/page user_agent=UA crc=0
%s
	fi
}
f
""" % (candidate, branch)
            result = subprocess.run(['bash', '-c', body], capture_output=True, text=True)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('TRANSFER_FAILED store=apkpure curl_exit=28', result.stdout)
        self.assertIn('APKPure transfer failed; refusing partial or empty output', result.stdout)
        self.assertFalse(candidate.exists())


if __name__ == '__main__':
    unittest.main()
