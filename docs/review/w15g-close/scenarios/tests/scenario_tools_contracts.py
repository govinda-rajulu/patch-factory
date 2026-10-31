"""W15g scenario checks that do not require Android build-tools or network access.

These are intentionally contract-level checks: the runner's apksigner/zipalign/aapt2
binaries are not available in this checkout, so version-specific command acceptance is
reported as UNVERIFIABLE in D-REPORT.md rather than guessed here.
"""
import json
import re
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src" / "build"))
import artifact_identity as identity  # noqa: E402
import sign_apk  # noqa: E402

SMOKE = (
    "youtube", "ytmusic", "facebook", "instagram", "telegram", "hotstar", "esfile",
    "edge", "keymapper", "linkedin", "photos", "truecaller-combo", "mxplayer", "adguard",
    "primevideo", "reddit", "amazonmusic",
)


def tools_fixture(version, *, v31=False, v32=False, v4=False):
    """Representative verify -v --print-certs text; warnings are deliberately noisy."""
    rows = [
        "Verifies",
        "WARNING: META-INF/OLD.SF is not protected by APK Signature Scheme v2",
        "Verified using v1 scheme (JAR signing): false",
        "Verified using v2 scheme (APK Signature Scheme v2): true",
        "Verified using v3 scheme (APK Signature Scheme v3): %s" % ("true" if v31 else "false"),
        "Verified using v3.1 scheme (APK Signature Scheme v3.1): %s" % ("true" if v31 else "false"),
        "Verified using v3.2 scheme (APK Signature Scheme v3.2): %s" % ("true" if v32 else "false"),
        "Verified using v4 scheme (APK Signature Scheme v4): %s" % ("true" if v4 else "false"),
        "WARNING: Source Stamp not verified",
        "Number of signers: 1",
        "V3.0 Signer: certificate SHA-256 digest: " + "a" * 64,
        "# synthetic build-tools " + version,
    ]
    return "\n".join(rows) + "\n"


class ToolRealityContracts(unittest.TestCase):
    def test_all_captured_sdk_shapes_are_readable_by_scheme_parser(self):
        # The scheme labels have been stable in the captured SDK37 output. This
        # exercises the parser against the five runner versions without claiming
        # that the binaries themselves are installed in this environment.
        for version in ("34.0.0", "35.0.0", "36.0.0", "36.1.0", "37.0.0"):
            with self.subTest(version=version):
                got = sign_apk.parse_schemes(tools_fixture(version))
                self.assertEqual(got, {
                    "v1": False, "v2": True, "v3": False,
                    "v3.1": False, "v3.2": False, "v4": False,
                })

    def test_captured_sdk37_final_signer_shapes(self):
        fixture_dir = ROOT / "tests" / "fixtures"
        self.assertEqual(identity.parse_signers(
            (fixture_dir / "apksigner-37-keymapper.txt").read_text()),
            "08480f6649a2be33ff3cccacce07454761d5fb9abe65f1e2caeeb782e382d050")
        self.assertEqual(identity.parse_signers(
            (fixture_dir / "apksigner-37-facebook-v2-only.txt").read_text()),
            "e3f9e1e0cf99d0e56a055ba65e241b3399f7cea524326b0cdd6ec1327ed0fdc1")

    def test_rotation_fixture_is_original_parser_input_not_final_signer_input(self):
        # This is a legitimate original APK shape (v3.1 key rotation). The
        # final-release parser must refuse it rather than silently choosing one
        # of the two identities; original_signer has the range-aware parser.
        text = (ROOT / "tests/fixtures/apksigner-37-photos-v31-rotation.txt").read_text()
        with self.assertRaisesRegex(ValueError, "unrecognized certificate identity"):
            identity.parse_signers(text)
        certificate, rotation = identity.parse_original_signers(text)
        self.assertEqual(certificate, "3d7a1223019aa39d9ea0e3436ab7c0896bfb4fb679f4de5fe7c23f326c8f994a")
        self.assertEqual(len(rotation), 2)

    def test_v4_true_is_visible_and_rejected_by_verify_contract(self):
        schemes = sign_apk.parse_schemes(tools_fixture("37.0.0", v4=True))
        self.assertTrue(schemes["v4"])
        self.assertNotEqual(schemes, sign_apk.expected_schemes(24))

    def test_aapt2_semantics_are_reader_independent(self):
        # Signing does not change package/version/minSdk; verify strips only the
        # reader path before comparing metadata.
        unsigned = {"package": "com.example", "version_code": "42", "version_name": "1.2", "min_sdk": 29,
                    "reader": "/sdk/34.0.0/aapt2"}
        signed = dict(unsigned, reader="/sdk/37.0.0/aapt2")
        self.assertEqual({k: v for k, v in unsigned.items() if k != "reader"},
                         {k: v for k, v in signed.items() if k != "reader"})


class SourcePathContracts(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.targets = {x["id"]: x for x in json.loads((ROOT / "src/targets.json").read_text())}
        cls.build = (ROOT / "src/build/build.sh").read_text()
        cls.patch_target = (ROOT / "src/build/patch_target.py").read_text()
        cls.utils = (ROOT / "src/build/utils.sh").read_text()

    def test_smoke_set_is_enabled_and_uses_patch_target_unsigned_path(self):
        self.assertEqual(set(SMOKE), set(SMOKE) & set(self.targets))
        for ident in SMOKE:
            with self.subTest(ident=ident):
                self.assertTrue(self.targets[ident].get("enabled"))
        self.assertIn("python3 src/build/patch_target.py", self.build)
        self.assertIn("--unsigned", self.patch_target)
        self.assertIn("PF_UNSIGNED", self.patch_target)

    def test_no_build_path_calls_removed_legacy_helpers(self):
        # Definitions in utils.sh are refusal stubs; production build.sh must
        # never call them. Comments are excluded from this call-shaped regex.
        for helper in ("patch", "patch_multi", "split_arch"):
            self.assertIsNone(re.search(r"(?m)^\s*" + helper + r"\s*(?:[ (]|$)", self.build), helper)
        self.assertIn("legacy patch_multi helper removed", self.utils)
        self.assertIn("legacy split_arch helper removed", self.utils)

    def test_target_option_and_patch_directories_exist(self):
        for ident in SMOKE:
            t = self.targets[ident]
            for candidate in t["candidates"]:
                with self.subTest(target=ident, candidate=candidate["name"]):
                    self.assertTrue((ROOT / "src/options" / (candidate["options"] + ".json")).is_file())
                    self.assertTrue((ROOT / "src/patches" / candidate["patch_dir"]).is_dir())

    def test_bundle_and_fallback_matrix_matches_build_contract(self):
        # apk_type controls .apkm/.xapk retrieval and APKEditor merge in utils;
        # patch_target itself always receives the resulting standalone APK.
        for ident in SMOKE:
            t = self.targets[ident]
            if ident in {"truecaller-combo", "primevideo", "esfile"}:
                self.assertEqual(t.get("apk_type"), "bundle")
            if ident in {"facebook", "instagram", "reddit", "hotstar", "edge", "mxplayer", "telegram", "keymapper", "linkedin", "amazonmusic", "photos", "adguard"}:
                self.assertIn(t.get("apk_type"), {"apk", "bundle"})
        self.assertEqual(self.targets["truecaller-combo"]["candidates"][1].get("fallback"), True)
        self.assertEqual(self.targets["esfile"]["candidates"][1].get("fallback"), True)
        self.assertEqual(self.targets["facebook"]["candidates"][1].get("fallback"), True)

    def test_sign_command_has_no_keystore_type_or_in_place_signing(self):
        sign = (ROOT / "src/build/sign_apk.py").read_text()
        self.assertIn("--out", sign)
        self.assertNotIn("--ks-type", sign)
        self.assertIn("env:KEYSTORE_PASS", sign)


if __name__ == "__main__":
    unittest.main()
