"""Validate's zizmor audit is advisory, pinned, and read-only."""
import re
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class ZizmorWorkflow(unittest.TestCase):
    TEXT = (ROOT / ".github/workflows/validate.yml").read_text(encoding="utf-8")


    def test_all_checkouts_disable_persisted_credentials_and_calls_pass_no_inherited_secrets(self):
        workflows = ROOT / ".github/workflows"
        for path in sorted(workflows.glob("*.yml")):
            text = path.read_text(encoding="utf-8")
            self.assertNotIn("secrets: inherit", text, path.name)
            lines = text.splitlines()
            for i, line in enumerate(lines):
                if "uses: actions/checkout@" not in line:
                    continue
                block = "\n".join(lines[i:i + 12])
                self.assertIn("persist-credentials: false", block, "%s:%d" % (path.name, i + 1))

    def test_advisory_zizmor_action_is_pinned_and_non_blocking(self):
        blocks = re.findall(
            r"(?ms)^      - name: Advisory zizmor workflow audit\n(.*?)(?=^      - name:|\Z)",
            self.TEXT,
        )
        self.assertEqual(len(blocks), 1)
        block = blocks[0]
        self.assertRegex(
            block,
            r"uses:\s*zizmorcore/zizmor-action@[0-9a-f]{40}\s+#\s*v[0-9]+\.[0-9]+\.[0-9]+",
        )
        self.assertIn("continue-on-error: true", block)
        self.assertIn("advanced-security: false", block)
        self.assertIn("online-audits: false", block)
        self.assertNotIn("security-events: write", block)


if __name__ == "__main__":
    unittest.main()
