import copy
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

import test_identity as fixtures
import resolved_inputs as resolved
import shadow_inputs as shadow
import input_recipe


class ResolvedContracts(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix="pf-resolved-contract-")
        self.addCleanup(self.tmp.cleanup)
        self.r = Path(self.tmp.name)
        for d in ("src", "docs", ".github"):
            shutil.copytree(fixtures.ROOT / d, self.r / d)
        for args in (["git", "init", "-q"], ["git", "config", "user.name", "Fixture"],
                     ["git", "config", "user.email", "fixture@example.invalid"],
                     ["git", "add", "src", "docs", ".github"],
                     ["git", "commit", "-qm", "fixture"]):
            subprocess.run(args, cwd=self.r, check=True, capture_output=True)
        head = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=self.r).decode().strip()
        self.env = dict(os.environ, GITHUB_SHA=head, GITHUB_RUN_ID="12345",
                        GITHUB_RUN_ATTEMPT="2", GITHUB_REPOSITORY="fixture/repo",
                        KEYSTORE_PASS="DO_NOT_INHERIT", KEYSTORE_B64="SECRET",
                        JAVA_TOOL_OPTIONS="UNSAFE", COE="true")
        self.calls = []
        self.ident = "keymapper"

    def patcher(self, directory, env):
        self.calls.append("patcher")
        self.assertNotIn("KEYSTORE_PASS", env)
        self.assertNotIn("JAVA_TOOL_OPTIONS", env)
        name = "morphe-desktop-fixture-all.jar"
        (Path(directory) / name).write_bytes(b"fixture patcher bytes")
        return dict(resolved.regular(directory, name), name=name)

    def resolver(self, args, **kwargs):
        self.calls.append("resolver")
        self.assertEqual(args, ["bash", "src/build/resolve.sh", self.ident])
        self.assertNotIn("COE", kwargs["env"])
        t = shadow.target(self.r, self.ident)
        winner = t.get("pin") or t["candidates"][0]["name"]
        p = Path(kwargs["env"]["PF_RESOLVE_DIR"]) / "upstream" / "bundle-1.2.3.mpp"
        p.parent.mkdir(parents=True)
        p.write_bytes(b"exact primary bytes")
        digest = hashlib.sha256(p.read_bytes()).hexdigest()
        return subprocess.CompletedProcess(args, 0,
            f"WINNER={winner}\nVERSION=4.2.1\nMPP={p}\nMPP_SHA256={digest}\nBUNDLE_TAG=v1.2.3\n", "")

    def extra(self, host, upstream, channel, out, env):
        self.calls.append((host, upstream, channel))
        self.assertNotIn("KEYSTORE_B64", env)
        Path(out).write_bytes(("extra:" + upstream).encode())
        return dict(resolved.regular(Path(out).parent, Path(out).name),
                    upstream_digest_verified=host == "github")

    def prepare(self, ident="keymapper"):
        self.ident = ident
        return resolved.prepare(self.r, ident, self.env, self.patcher, self.resolver, self.extra)

    def lock(self):
        return json.loads((self.r / resolved.LOCK).read_text())

    def rewrite(self, doc, reseal=False):
        if reseal:
            doc["dependency_sha256"] = input_recipe.digest(doc["material"])
            doc["sha256"] = input_recipe.digest({k: v for k, v in doc.items() if k != "sha256"})
        (self.r / resolved.LOCK).write_text(json.dumps(doc))

    def test_prepare_verify_install_and_consumption_use_exact_files_without_network(self):
        doc = self.prepare()
        calls = copy.deepcopy(self.calls)
        with patch.object(resolved.github_patcher, "fetch", side_effect=AssertionError("second fetch")), \
             patch.object(resolved.extra_bundle, "fetch", side_effect=AssertionError("second fetch")), \
             patch.object(resolved.subprocess, "run", wraps=subprocess.run):
            self.assertEqual(resolved.verify(self.r, self.ident, self.env), doc)
            self.assertEqual(resolved.install(self.r, self.ident, self.env), doc)
        self.assertEqual(self.calls, calls)
        m = doc["material"]
        captured = {"target": self.ident, "winner": m["winner"],
                    "bundles": m["bundles"], "tools": [m["patcher"]]}
        self.assertEqual(resolved.verify_consumed(self.r, self.ident, captured, self.env)["status"], "MATCH")
        for r in [m["patcher"]] + m["bundles"]:
            self.assertEqual(resolved.regular(self.r, r["path"])["sha256"], r["sha256"])

    def test_all_fourteen_target_locks_preserve_configured_extras_and_roles(self):
        ts = json.loads((self.r / "src/targets.json").read_text())
        count = 0
        for t in ts:
            if not t["enabled"]:
                continue
            doc = self.prepare(t["id"])
            self.assertEqual(len(doc["material"]["bundles"]), 1 + len(t.get("extra_bundles", [])))
            self.assertEqual(resolved.verify(self.r, t["id"], self.env), doc)
            self.assertIn("source APK bytes", doc["unresolved"])
            self.assertNotEqual(doc["state"], "UNCHANGED")
            shutil.rmtree(self.r / "resolved-inputs")
            count += 1
        self.assertEqual(count, 14)
        self.assertTrue(any(isinstance(c, tuple) and c[0] == "gitlab" for c in self.calls))

    def test_run_attempt_source_and_repository_mismatch_refuse_without_writes(self):
        self.prepare()
        for k, value in (("GITHUB_SHA", "f" * 40), ("GITHUB_RUN_ID", "55"),
                         ("GITHUB_RUN_ATTEMPT", "3"), ("GITHUB_REPOSITORY", "other/repo")):
            with self.subTest(key=k), self.assertRaises(ValueError):
                resolved.install(self.r, self.ident, dict(self.env, **{k: value}))
        self.assertEqual(list(self.r.glob("*.jar")), [])

    def test_missing_identity_and_noncanonical_values_refuse(self):
        for k in ("GITHUB_SHA", "GITHUB_RUN_ID", "GITHUB_RUN_ATTEMPT", "GITHUB_REPOSITORY"):
            with self.subTest(key=k), self.assertRaises(ValueError):
                resolved.identity(self.r, dict(self.env, **{k: ""}))
        for value in ("0", "01", "-1", "1\n", "true", "1/2"):
            with self.subTest(value=value), self.assertRaises(ValueError):
                resolved.identity(self.r, dict(self.env, GITHUB_RUN_ID=value))

    def test_duplicate_missing_or_invalid_resolver_output_refuses(self):
        text = "WINNER=x\nVERSION=1.2\nMPP=/a\nMPP_SHA256=" + "a" * 64 + "\nBUNDLE_TAG=v1\n"
        for value in (text + "WINNER=x\n", text.replace("VERSION=1.2\n", ""),
                      text.replace("VERSION=1.2", "VERSION=oops"),
                      text.replace("BUNDLE_TAG=v1", "BUNDLE_TAG=v1\x00")):
            with self.subTest(value=value), self.assertRaises(ValueError):
                resolved.fields(value)

    def test_prepare_failure_never_exposes_partial_packet_or_secrets(self):
        def failed(*args, **kwargs):
            return subprocess.CompletedProcess(args, 2, "SECRET", "SECRET")
        with self.assertRaises(ValueError):
            resolved.prepare(self.r, self.ident, self.env, self.patcher, failed, self.extra)
        self.assertFalse((self.r / "resolved-inputs").exists())

    def test_duplicate_prepare_preserves_existing_packet(self):
        self.prepare()
        old = (self.r / resolved.LOCK).read_bytes()
        with self.assertRaises(ValueError):
            self.prepare()
        self.assertEqual(old, (self.r / resolved.LOCK).read_bytes())

    def test_same_size_payload_mutation_and_missing_payload_refuse(self):
        doc = self.prepare()
        p = self.r / "resolved-inputs" / doc["material"]["patcher"]["path"]
        old = p.read_bytes()
        p.write_bytes(bytes([old[0] ^ 1]) + old[1:])
        with self.assertRaises(ValueError):
            resolved.install(self.r, self.ident, self.env)
        p.unlink()
        with self.assertRaises(ValueError):
            resolved.verify(self.r, self.ident, self.env)
        self.assertEqual(list(self.r.glob("*.jar")), [])

    def test_unlisted_payload_and_directory_refuse(self):
        self.prepare()
        p = self.r / "resolved-inputs" / "extra-secret"
        p.write_bytes(b"not allowed")
        with self.assertRaises(ValueError):
            resolved.verify(self.r, self.ident, self.env)
        p.unlink();p.mkdir()
        with self.assertRaises(ValueError):
            resolved.verify(self.r, self.ident, self.env)

    def test_symlink_payload_and_parent_refuse(self):
        doc = self.prepare()
        p = self.r / "resolved-inputs" / doc["material"]["patcher"]["path"]
        old = p.read_bytes();p.unlink()
        (self.r / "outside").write_bytes(old);p.symlink_to(self.r / "outside")
        with self.assertRaises(ValueError):
            resolved.verify(self.r, self.ident, self.env)
        p.unlink();p.write_bytes(old)
        (self.r / "resolved-inputs").rename(self.r / "saved-payload")
        (self.r / "resolved-inputs").symlink_to(self.r / "saved-payload", target_is_directory=True)
        with self.assertRaises(ValueError):
            resolved.verify(self.r, self.ident, self.env)

    def test_lock_digest_and_resealed_wrong_roles_target_paths_refuse(self):
        doc = self.prepare()
        bad = copy.deepcopy(doc);bad["material"]["winner"] = "wrong"
        self.rewrite(bad)
        with self.assertRaises(ValueError):
            resolved.verify(self.r, self.ident, self.env)
        for mutate in (
            lambda d: d["material"].update(target="reddit"),
            lambda d: d["material"]["bundles"][0].update(role="extra"),
            lambda d: d["material"]["bundles"][0].update(path="../outside"),
            lambda d: d.update(state="UNCHANGED"),
            lambda d: d.update(patch_version="1\nWINNER=evil"),
            lambda d: d["material"]["bundles"].append(d["material"]["bundles"][0]),
        ):
            bad = copy.deepcopy(doc);mutate(bad);self.rewrite(bad, True)
            with self.assertRaises(ValueError):
                resolved.verify(self.r, self.ident, self.env)

    def test_target_resource_recipe_drift_refuses_but_note_only_does_not(self):
        doc = self.prepare()
        path = self.r / "src/targets.json";old = path.read_bytes()
        ts = json.loads(old);next(t for t in ts if t["id"] == self.ident)["note"] = "new note"
        path.write_text(json.dumps(ts))
        self.assertEqual(resolved.verify(self.r, self.ident, self.env), doc)
        next(t for t in ts if t["id"] == self.ident)["min_sdk_ceiling"] = 28
        path.write_text(json.dumps(ts))
        with self.assertRaises(ValueError):
            resolved.install(self.r, self.ident, self.env)
        path.write_bytes(old)
        code = self.r / "src/build/resolved_inputs.py"
        code.write_bytes(code.read_bytes() + b"\n# source change")
        with self.assertRaises(ValueError):
            resolved.verify(self.r, self.ident, self.env)

    def test_install_collision_preserves_dirt_and_does_not_copy_other_files(self):
        self.prepare()
        p = self.r / "morphe-desktop-existing.jar";p.write_bytes(b"keep me")
        with self.assertRaises(ValueError):
            resolved.install(self.r, self.ident, self.env)
        self.assertEqual(p.read_bytes(), b"keep me")
        self.assertEqual(list(self.r.glob("*.mpp")), [])

    def test_consumed_bundle_and_patcher_drift_refuse(self):
        doc = self.prepare();m = doc["material"]
        good = {"target": self.ident, "winner": m["winner"],
                "bundles": m["bundles"], "tools": [m["patcher"]]}
        for kind in ("bundles", "tools"):
            bad = copy.deepcopy(good);bad[kind][0]["sha256"] = "f" * 64
            with self.assertRaises(ValueError):
                resolved.verify_consumed(self.r, self.ident, bad, self.env)

    def test_cli_verify_and_install_are_real_entrypoints(self):
        self.prepare()
        env = dict(self.env);env.pop("JAVA_TOOL_OPTIONS", None)
        for command in ("verify", "install"):
            result = subprocess.run([sys.executable, "src/build/resolved_inputs.py", command, self.ident],
                                    cwd=self.r, env=env, capture_output=True, text=True, timeout=30)
            self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("WINNER=lain", result.stdout)
        again = subprocess.run([sys.executable, "src/build/resolved_inputs.py", "install", self.ident],
                               cwd=self.r, env=env, capture_output=True, text=True)
        self.assertNotEqual(again.returncode, 0)
        self.assertNotIn("SECRET", again.stderr)

    def test_shadow_matrix_covers_legacy_omitted_targets_without_build_authority(self):
        out = self.r / "output";out.write_text("matrix={\"target\":[]}\n")
        shadow.plan(self.r, dict(self.env, GITHUB_OUTPUT=str(out)))
        lines = out.read_text().splitlines()
        self.assertEqual(lines[0], 'matrix={"target":[]}')
        observation = json.loads(next(x.split("=", 1)[1] for x in lines if x.startswith("resolution_matrix=")))
        self.assertEqual(len(observation["target"]), 14)
        self.assertNotIn("UNCHANGED", (self.r / "shadow-evidence/plan.json").read_text())

    def test_workflow_read_only_resolution_no_secrets_and_pre_secret_verify(self):
        ci = (self.r / ".github/workflows/ci.yml").read_text()
        job = ci.split("\n  resolve:\n", 1)[1].split("\n  build:\n", 1)[0]
        self.assertIn("permissions:\n      contents: read\n", job)
        self.assertIn("continue-on-error: true", job)
        self.assertIn("max-parallel: 6", job)
        self.assertNotIn("secrets.", job)
        self.assertIn("matrix: ${{ fromJson(needs.plan.outputs.matrix) }}", ci)
        manual = (self.r / ".github/workflows/manual-patch.yml").read_text()
        self.assertLess(manual.index("Verify dependency packet before signing secrets"), manual.index("Decode keystore"))
        download = manual.split("id: resolved_download", 1)[1].split("      - name:", 1)[0]
        self.assertIn("actions/download-artifact@d3f86a106a0bac45b974a628896c90dbdf5c8093", download)
        self.assertNotIn("github-token", download)
        self.assertIn("github.run_attempt", download)
        self.assertIn("Cache the patcher jar\n        if: steps.resolved_verify.outcome != 'success'", manual)

    def test_real_build_shell_consumes_locked_bytes_without_second_resolution(self):
        # Stop at the store-download boundary. No Java patching, signing or network.
        # Exercise actual build.sh + actual selections.sh + actual lock installer.
        (self.r / "src/build/utils.sh").write_text(
            "mkdir -p release download\n"
            "green_log(){ printf '%s\\n' \"$1\"; }\n"
            "red_log(){ printf '%s\\n' \"$1\"; }\n"
            "yellow_log(){ printf '%s\\n' \"$1\"; }\n"
            "get_patches_key(){ :; }\n"
            "get_apk(){ echo STORE_BOUNDARY_REACHED; return 77; }\n"
            "get_apkpure(){ echo STORE_BOUNDARY_REACHED; return 77; }\n")
        doc = self.prepare("truecaller-combo")
        bin_dir = self.r / "bin";bin_dir.mkdir()
        launcher = bin_dir / "python3"
        launcher.write_text(
            "#!/bin/bash\n"
            "case \"$1 $2\" in\n"
            "  'src/build/artifact_identity.py capture-signer') exit 0 ;;\n"
            "  'src/build/github_patcher.py '*|'src/build/github_bundle.py '*|'src/build/extra_bundle.py '*) echo SECOND_FETCH_FORBIDDEN; exit 91 ;;\n"
            "esac\n"
            "exec " + sys.executable + " \"$@\"\n")
        launcher.chmod(0o755)
        env = dict(self.env, PATH=str(bin_dir) + ":" + os.environ["PATH"],
                   PF_RESOLVED_REQUESTED="true", PF_RESOLVED_READY="true")
        env.pop("JAVA_TOOL_OPTIONS", None);env.pop("COE", None)
        result = subprocess.run(["bash", "src/build/build.sh", "truecaller-combo"], cwd=self.r,
                                env=env, capture_output=True, text=True, timeout=30)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("STORE_BOUNDARY_REACHED", result.stdout)
        self.assertIn("using checked Plan patcher and bundle bytes", result.stdout)
        self.assertNotIn("SECOND_FETCH_FORBIDDEN", result.stdout + result.stderr)
        files = list(self.r.glob("*.mpp")) + list((self.r / "extra").glob("*.mpp"))
        self.assertEqual({p.name for p in files}, {r["slot"] for r in doc["material"]["bundles"]})
        self.assertEqual(sorted(p.name for p in self.r.glob("*.mpp")), ["01-paresh.mpp"])
        for p in files:
            row = next(r for r in doc["material"]["bundles"] if r["slot"] == p.name)
            self.assertEqual(hashlib.sha256(p.read_bytes()).hexdigest(), row["sha256"])

    def test_actual_input_capture_binds_resolved_bytes_before_patching(self):
        doc = self.prepare()
        resolved.install(self.r, self.ident, self.env)
        cert = "a" * 64
        for name, data in (("APKEditor.jar", b"editor"), ("pup", b"pup"),
                           ("download/key-mapper.apk", b"apk"),
                           (".requested", b"lain\tUnlock Premium\n")):
            p = self.r / name;p.parent.mkdir(parents=True, exist_ok=True);p.write_bytes(data)
        (self.r / ".signer-before-build.json").write_text(json.dumps({"certificate_sha256": cert}))
        env = dict(self.env, PF_RESOLVED_REQUESTED="true", PF_RESOLVED_READY="true")
        fixtures.identity.capture_inputs(self.r, self.ident, doc["material"]["winner"], env)
        captured = json.loads((self.r / ".build-inputs.json").read_text())
        self.assertEqual(captured["resolution"]["status"], "MATCH")
        (self.r / doc["material"]["bundles"][0]["slot"]).write_bytes(b"changed")
        with self.assertRaises(ValueError):
            fixtures.identity.capture_inputs(self.r, self.ident, doc["material"]["winner"], env)

    def test_requested_missing_resolution_never_looks_unchanged(self):
        from shadow_contracts import ShadowContracts
        f = ShadowContracts();f.setUp()
        try:
            captured = f.capture()
            doc = shadow.realized(f.r, captured, dict(f.env, PF_RESOLVED_REQUESTED="true"))
            baseline = {"target": "keymapper", "effective_sha256": doc["effective_sha256"]}
            result = shadow.compare(doc, baseline, "VERIFIED")
            self.assertEqual(result["state"], "UNKNOWN")
            self.assertEqual(result["reason"], "PREPARED_DEPENDENCIES_UNAVAILABLE_OR_INVALID")
        finally:
            f.doCleanups()

    def test_real_prepare_cli_failure_leaves_explicit_unknown_not_empty_success(self):
        env = dict(self.env, GITHUB_SHA="f" * 40)
        result = subprocess.run([sys.executable, "src/build/resolved_inputs.py", "prepare", self.ident],
                                cwd=self.r, env=env, capture_output=True, text=True, timeout=30)
        self.assertNotEqual(result.returncode, 0)
        report = json.loads((self.r / "resolved-observation/keymapper.json").read_text())
        self.assertEqual(report["state"], "UNKNOWN")
        self.assertFalse((self.r / "resolved-inputs").exists())
        self.assertNotIn("DO_NOT_INHERIT", result.stdout + result.stderr)


if __name__ == "__main__":
    unittest.main()
