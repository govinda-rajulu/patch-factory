"""Store helper startup is lazy per build and idempotent across attempts."""
import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class StoreServices(unittest.TestCase):
    def setUp(self):
        self.helper = (ROOT / 'src/build/store_services.sh').read_text()
        self.action = (ROOT / '.github/actions/preparing/action.yml').read_text()
        self.workflow = (ROOT / '.github/workflows/manual-patch.yml').read_text()
        self.attempts = (ROOT / 'src/build/build_attempts.py').read_text()

    def test_images_remain_digest_pinned_and_each_service_has_one_run_path(self):
        self.assertRegex(self.helper, r'ghcr\.io/flaresolverr/flaresolverr@sha256:[0-9a-f]{64}')
        self.assertRegex(self.helper, r'ghcr\.io/sarperavci/cloudflarebypassforscraping@sha256:[0-9a-f]{64}')
        self.assertEqual(self.helper.count('docker run -d --name'), 1)
        self.assertEqual(self.helper.count('ensure flaresolverr'), 1)
        self.assertEqual(self.helper.count('ensure cloudflarebypass'), 1)

    def test_health_check_is_reuse_gate_before_fresh_start(self):
        health = self.helper.index('if healthy "$name"; then')
        fresh = self.helper.index('docker rm -f "$name"')
        self.assertLess(health, fresh)
        self.assertIn('Reusing healthy', self.helper)
        self.assertIn('after a failed health check', self.helper)

    def test_build_does_not_start_helpers_for_prepared_apk(self):
        self.assertIn('start_store_services:', self.action)
        self.assertIn('start_store_services: false', self.workflow)
        self.assertIn("e.get('PF_SOURCE_READY', 'false') != 'true' or n > 1", self.attempts)
        self.assertIn('ensure_store_services(root, e)', self.attempts)

    def test_retry_reuses_running_helpers(self):
        # The ensure call is after attempt numbering, and the helper itself owns
        # health/restart policy. This prevents a fallback from unconditionally
        # issuing another docker run.
        gate = self.attempts.index("if e.get('PF_SOURCE_READY', 'false') != 'true' or n > 1:")
        call = self.attempts.index('ensure_store_services(root, e)', gate)
        build = self.attempts.index('rc, winner, reason = attempt(', call)
        self.assertLess(call, build)
        self.assertIn('check makes the latter reuse', self.attempts)


class StepDownStartsHelpers(unittest.TestCase):
    """W16g: a version step-down inside an attempt downloads again; its first Cloudflare fetch
    starts or reuses the helpers, once per shell."""

    def test_cf_get_starts_helpers_once_before_first_fetch(self):
        utils = (ROOT / 'src/build/utils.sh').read_text()
        body = utils.split('_cf_get() {', 1)[1].split('\n}', 1)[0]
        self.assertLess(body.index('bash src/build/store_services.sh'), body.index('_fs_get "$@"'))
        self.assertIn('_PF_STORE_SVC=1', body)
        self.assertIn('_PF_STORE_SVC=0\n', utils)


if __name__ == '__main__':
    unittest.main()
