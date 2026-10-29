#!/usr/bin/env python3
"""Offline contracts for bounded runner time and diagnostic artifact retention."""
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]


class EfficiencyWorkflowContracts(unittest.TestCase):
    def test_build_jobs_have_bounded_time_without_touching_release_policy(self):
        manual = (ROOT / ".github/workflows/manual-patch.yml").read_text()
        batch = (ROOT / ".github/workflows/batch-patch.yml").read_text()
        self.assertIn("    timeout-minutes: 60\n", manual)
        self.assertIn("    timeout-minutes: 10\n", batch)
        # The publishing path and the existing test APK handoff remain unchanged.
        self.assertIn("inputs.publish && github.ref == 'refs/heads/main'", manual)
        self.assertIn("retention-days: 7", manual)
        self.assertIn("name: test-apk-${{ inputs.target }}-${{ github.run_id }}-${{ github.run_attempt }}", manual)

    def test_ci_and_manual_shadow_artifacts_are_short_lived_only(self):
        ci = (ROOT / ".github/workflows/ci.yml").read_text()
        manual = (ROOT / ".github/workflows/manual-patch.yml").read_text()
        # All five 30-day CI artifacts are bounded observations/reports; two-day exact
        # dependency/source inputs are deliberately not changed.
        self.assertEqual(ci.count("retention-days: 7"), 5)
        self.assertEqual(ci.count("retention-days: 30"), 0)
        self.assertEqual(ci.count("retention-days: 2"), 2)
        shadow = manual.split("name: shadow-inputs-", 1)[1].split("      - name:", 1)[0]
        self.assertIn("retention-days: 7", shadow)
        self.assertNotIn("retention-days: 30", shadow)


if __name__ == "__main__":
    unittest.main()
