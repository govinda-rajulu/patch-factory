"""Contract for provider sources intentionally absent from bundles.json."""
import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src/etc"))
import extra_providers  # noqa: E402


class ExtraProviderContract(unittest.TestCase):
    def test_checked_in_sources_have_safe_schema_and_hush_rows(self):
        rows = extra_providers.load(ROOT / "src/etc/extra-providers.json")
        self.assertEqual({(r["owner"], r["repo"]) for r in rows}, {
            ("SysAdminDoc", "HushTelegram"), ("SysAdminDoc", "HushGram"),
            ("SysAdminDoc", "HushFacebook")})
        self.assertTrue(all(r["packages"] and r["why"] for r in rows))

    def test_duplicate_or_unknown_fields_fail_closed(self):
        with self.assertRaises(ValueError):
            extra_providers.validate([{"owner": "a", "repo": "b", "packages": ["bad"], "why": "x"}])
        with self.assertRaises(ValueError):
            extra_providers.validate([{"owner": "a", "repo": "b", "packages": ["com.example.app"],
                                       "why": "x", "unexpected": True}])
        with self.assertRaises(ValueError):
            extra_providers.validate([
                {"owner": "a", "repo": "b", "packages": ["com.example.app"], "why": "x"},
                {"owner": "A", "repo": "B", "packages": ["com.example.app"], "why": "x"},
            ])


if __name__ == "__main__":
    unittest.main()
