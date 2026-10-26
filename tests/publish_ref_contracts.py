"""Publishing is fail-closed to the main ref while branch smokes remain allowed."""
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class PublishRef(unittest.TestCase):
    def test_manual_refuses_publish_before_secret_and_release_steps(self):
        text = (ROOT / '.github/workflows/manual-patch.yml').read_text()
        guard = text[text.index('- name: Refuse publishing from a non-main ref'):]
        self.assertIn("if: inputs.publish && github.ref != 'refs/heads/main'", guard)
        self.assertIn('use publish=false for a branch smoke', guard)
        self.assertLess(text.index('Refuse publishing from a non-main ref'), text.index('Decode keystore'))
        self.assertIn("inputs.publish && github.ref == 'refs/heads/main'", text)
        self.assertIn("if: steps.check-gh.outputs.internet_error == '0' && inputs.publish && github.ref == 'refs/heads/main'", text)

    def test_batch_refuses_publish_before_reusable_build(self):
        text = (ROOT / '.github/workflows/batch-patch.yml').read_text()
        self.assertIn("if: inputs.publish && github.ref != 'refs/heads/main'", text)
        self.assertIn('use publish=false for a branch smoke', text)
        self.assertLess(text.index('Refuse publishing from a non-main ref'), text.index('uses: ./.github/workflows/manual-patch.yml'))


if __name__ == '__main__':
    unittest.main()
