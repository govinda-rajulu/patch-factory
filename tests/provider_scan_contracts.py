#!/usr/bin/env python3
"""Offline contracts for provider_scan.py and its opt-in workflow wiring."""
import http.server
import json
import os
import pathlib
import socketserver
import subprocess
import tempfile
import threading
import unittest
import zipfile

ROOT = pathlib.Path(__file__).resolve().parents[1]
SCAN = ROOT / "src/etc/provider_scan.py"


class _VT(http.server.BaseHTTPRequestHandler):
    seen = []
    response = {"data": {"attributes": {"last_analysis_stats": {"malicious": 0, "suspicious": 0}}}}

    status = 200

    def log_message(self, *args):
        pass

    def do_GET(self):
        self.__class__.seen.append((self.path, self.headers.get("x-apikey")))
        raw = json.dumps(self.response).encode()
        self.send_response(self.status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(raw)))
        self.end_headers()
        self.wfile.write(raw)

    def log_message(self, *_):
        pass


class ProviderScan(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix="pf-provider-scan-")
        self.r = pathlib.Path(self.tmp.name)
        _VT.status = 200
        _VT.response = {"data": {"attributes": {"last_analysis_stats": {"malicious": 0, "suspicious": 0}}}}
        self.bin = self.r / "bin"
        self.bin.mkdir()
        self.aapt = self.bin / "aapt2"
        self.aapt.write_text("""#!/bin/sh
case \"$3\" in
  *orig.apk) echo \"uses-permission: name='android.permission.INTERNET'\" ;;
  *) echo \"$PERMS\" ;;
esac
""")
        self.aapt.chmod(0o755)
        self.old_env = os.environ.copy()
        os.environ["PATH"] = str(self.bin) + os.pathsep + self.old_env["PATH"]
        self.orig = self.r / "orig.apk"
        self.patch = self.r / "patch.apk"
        self.mpp = self.r / "provider.mpp"
        self.mpp.write_bytes(b"provider bundle")

    def tearDown(self):
        os.environ.clear(); os.environ.update(self.old_env)
        self.tmp.cleanup()

    def apk(self, path, strings=(), libs=()):
        with zipfile.ZipFile(path, "w") as z:
            z.writestr("AndroidManifest.xml", b"fixture")
            z.writestr("classes.dex", b"\0".join(x.encode() for x in strings))
            for lib in libs:
                z.writestr(lib, b"fixture")

    def run_scan(self, env=None):
        out = self.r / "scan.json"
        e = os.environ.copy(); e.update(env or {})
        p = subprocess.run(["python3", str(SCAN), str(self.orig), str(self.patch), str(self.mpp),
                            "fixture", "provider", str(out)], cwd=ROOT, env=e,
                           text=True, capture_output=True, check=False)
        self.assertEqual(p.returncode, 0, p.stderr)
        return json.loads(out.read_text()), p.stdout

    def clean_clam(self):
        clam = self.bin / "clamscan"
        clam.write_text("#!/bin/sh\nexit 0\n"); clam.chmod(0o755)

    def with_vt(self, response=None, status=200):
        _VT.seen = []
        _VT.response = response if response is not None else {"data": {"attributes": {"last_analysis_stats": {"malicious": 0, "suspicious": 0}}}}
        _VT.status = status
        server = socketserver.TCPServer(("127.0.0.1", 0), _VT)
        thread = threading.Thread(target=server.serve_forever, daemon=True); thread.start()
        self.addCleanup(lambda: (server.shutdown(), server.server_close(), thread.join()))
        return {"VT_API_KEY": "k", "PF_VT_BASE": "http://127.0.0.1:%d/api/v3" % server.server_address[1]}

    def test_pass(self):
        # W16y-b review: PASS needs a clean ClamAV run and an answered VirusTotal lookup.
        self.clean_clam()
        self.apk(self.orig, ["https://github.com/provider/release"])
        self.apk(self.patch, ["https://github.com/provider/release"])
        result, line = self.run_scan(self.with_vt())
        self.assertEqual(result["verdict"], "PASS")
        self.assertIn("PROVIDER_SCAN target=fixture provider=provider verdict=PASS", line)

    def test_missing_clamav_or_vt_key_holds(self):
        self.apk(self.orig); self.apk(self.patch)
        result, _ = self.run_scan(self.with_vt())
        self.assertEqual((result["clamav"], result["verdict"]), ("UNKNOWN", "HOLD"))
        self.clean_clam()
        env = os.environ.copy(); env.pop("VT_API_KEY", None)
        result, _ = self.run_scan({"VT_API_KEY": ""})
        self.assertEqual((result["vt"], result["verdict"]), ("NOT_CONFIGURED", "HOLD"))

    def test_clamav_exit_2_holds(self):
        self.apk(self.orig); self.apk(self.patch)
        clam = self.bin / "clamscan"
        clam.write_text("#!/bin/sh\necho 'no database'\nexit 2\n"); clam.chmod(0o755)
        result, _ = self.run_scan(self.with_vt())
        self.assertEqual((result["clamav"], result["verdict"]), ("UNKNOWN", "HOLD"))

    def test_vt_rate_limit_and_bad_shape_hold(self):
        self.clean_clam(); self.apk(self.orig); self.apk(self.patch)
        result, _ = self.run_scan(self.with_vt(status=429))
        self.assertEqual((result["vt"], result["verdict"]), ("UNKNOWN", "HOLD"))
        result, _ = self.run_scan(self.with_vt(response={"data": []}))
        self.assertEqual((result["vt"], result["verdict"]), ("UNKNOWN", "HOLD"))
        result, _ = self.run_scan(self.with_vt(response={"data": {"attributes": {}}}))
        self.assertEqual((result["vt"], result["verdict"]), ("UNKNOWN", "HOLD"))

    def test_vt_unknown_hash_still_passes(self):
        self.clean_clam(); self.apk(self.orig); self.apk(self.patch)
        result, _ = self.run_scan(self.with_vt(status=404))
        self.assertEqual((result["vt"], result["verdict"]), ("unknown to VT", "PASS"))

    def test_changed_native_library_holds(self):
        self.clean_clam()
        self.apk(self.orig, libs=["lib/arm64-v8a/libx.so"])
        with zipfile.ZipFile(self.patch, "w") as z:
            z.writestr("AndroidManifest.xml", b"fixture"); z.writestr("classes.dex", b"")
            z.writestr("lib/arm64-v8a/libx.so", b"replaced")
        result, _ = self.run_scan(self.with_vt())
        self.assertEqual(result["verdict"], "HOLD")
        self.assertIn("changed lib/arm64-v8a/libx.so", result["flags"])

    def test_sensitive_permission_holds(self):
        self.apk(self.orig)
        self.apk(self.patch)
        result, _ = self.run_scan({"PERMS": "uses-permission: name='android.permission.SEND_SMS'"})
        self.assertEqual(result["verdict"], "HOLD")
        self.assertEqual(result["permissions_added"], ["SEND_SMS"])

    def test_new_host_holds(self):
        self.apk(self.orig, ["https://github.com/provider/release"])
        self.apk(self.patch, ["https://evil.example"])
        result, _ = self.run_scan()
        self.assertEqual(result["verdict"], "HOLD")
        self.assertEqual(result["new_hosts"], ["evil.example"])

    def test_new_dex_loader_holds(self):
        self.apk(self.orig, ["ordinary code"])
        self.apk(self.patch, ["DexClassLoader"])
        result, _ = self.run_scan()
        self.assertEqual(result["verdict"], "HOLD")
        self.assertIn("DexClassLoader", result["flags"])

    def test_clamav_found_blocks(self):
        self.apk(self.orig); self.apk(self.patch)
        clam = self.bin / "clamscan"
        clam.write_text("#!/bin/sh\necho 'fixture FOUND'\nexit 1\n"); clam.chmod(0o755)
        result, _ = self.run_scan()
        self.assertEqual(result["verdict"], "BLOCK")
        self.assertEqual(result["clamav"], "FOUND")

    def test_vt_stub_and_key_not_printed(self):
        self.apk(self.orig); self.apk(self.patch)
        _VT.seen = []
        with socketserver.TCPServer(("127.0.0.1", 0), _VT) as server:
            thread = threading.Thread(target=server.serve_forever, daemon=True); thread.start()
            result, line = self.run_scan({"VT_API_KEY": "do-not-print-this", "PF_VT_BASE": "http://127.0.0.1:%d/api/v3" % server.server_address[1]})
            server.shutdown(); thread.join()
        self.assertEqual(result["vt"], "clean")
        self.assertEqual(len(_VT.seen), 2)
        self.assertTrue(all(key == "do-not-print-this" for _, key in _VT.seen))
        self.assertNotIn("do-not-print-this", line)

    def test_workflow_contract(self):
        workflow = (ROOT / ".github/workflows/manual-patch.yml").read_text()
        self.assertGreaterEqual(workflow.count("scan:"), 2)
        self.assertGreaterEqual(workflow.count("default: false"), 3)
        self.assertIn("provider-scan-${{ inputs.target }}-${{ github.run_id }}", workflow)
        self.assertIn("retention-days: 30", workflow)
        self.assertIn("sudo apt-get install -y clamav", workflow)
        scan_step = workflow.split("- name: Run provider safety scan", 1)[1].split("- name: Upload provider scan evidence", 1)[0]
        self.assertIn("VT_API_KEY: ${{ secrets.VT_API_KEY }}", scan_step)
        job_before = workflow.split("jobs:", 1)[1].split("- name: Run provider safety scan", 1)[0]
        self.assertNotIn("VT_API_KEY:", job_before)


if __name__ == "__main__":
    unittest.main()
