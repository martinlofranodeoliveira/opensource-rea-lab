import base64
import gzip
import hashlib
import io
import json
import subprocess
import sys
import tarfile
import tempfile
import unittest
from pathlib import Path

from npm_tarball_audit import Limits, audit


class AuditTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.path = Path(self.temp.name) / "fixture.tgz"

    def make(self, members=(), *, manifest=None):
        if manifest is None:
            manifest = {"name": "useful-example", "version": "1.0.0", "license": "MIT", "bin": {"useful": "bin.js"}}
        with tarfile.open(self.path, "w:gz", format=tarfile.PAX_FORMAT) as tf:
            for name, content in [("package/package.json", json.dumps(manifest).encode()),
                                  ("package/LICENSE", b"MIT test fixture"),
                                  ("package/bin.js", b"// fixture, never run\n"), *members]:
                if isinstance(content, tarfile.TarInfo):
                    tf.addfile(content)
                else:
                    entry = tarfile.TarInfo(name)
                    entry.size = len(content)
                    tf.addfile(entry, io.BytesIO(content))
        return self.path

    def codes(self, report):
        return {f["code"] for f in report["findings"]}

    def test_valid_package_is_hashed_and_never_extracted(self):
        self.make()
        result = audit(self.path, include_inventory=True)
        self.assertEqual(result["status"], "pass")
        self.assertEqual(result["member_count"], 3)
        self.assertEqual(result["sha256"], hashlib.sha256(self.path.read_bytes()).hexdigest())
        self.assertEqual(len(result["inventory"]), 3)
        self.assertFalse(result["package_executed"])
        self.assertFalse(result["files_extracted"])
        self.assertFalse((Path(self.temp.name) / "package").exists())

    def test_tar_traversal_absolute_windows_and_control_paths(self):
        for name in ("package/../../escape", "/etc/escape", "C:/escape", "package/C:/escape", "package/x:stream", "package\\escape", "package/a/../x", "package//x", "package/\x1b[31mx"):
            with self.subTest(name=name):
                result = audit(self.make([(name, b"bad")]))
                self.assertIn("unsafe_path", self.codes(result))
                self.assertEqual(result["status"], "fail")

    def test_symlink_hardlink_and_device_are_rejected(self):
        for kind, expected in ((tarfile.SYMTYPE, "link_member"), (tarfile.LNKTYPE, "link_member"), (tarfile.CHRTYPE, "special_member")):
            with self.subTest(kind=kind):
                info = tarfile.TarInfo("package/link")
                info.type, info.linkname = kind, "../../outside"
                self.assertIn(expected, self.codes(audit(self.make([("package/link", info)]))))

    def test_duplicate_member_and_privileged_mode(self):
        info = tarfile.TarInfo("package/bin.js")
        info.mode = 0o4755
        result = audit(self.make([("package/bin.js", info)]))
        self.assertTrue({"duplicate_member", "privileged_mode"} <= self.codes(result))

    def test_identity_and_integrity_must_match(self):
        self.make()
        sri = "sha512-" + base64.b64encode(hashlib.sha512(self.path.read_bytes()).digest()).decode()
        self.assertEqual(audit(self.path, integrity=sri, expected_name="useful-example", expected_version="1.0.0")["status"], "pass")
        mismatch = audit(self.path, integrity="sha512-" + base64.b64encode(bytes(64)).decode(), expected_version="2.0.0")
        self.assertTrue({"integrity_mismatch", "identity_mismatch"} <= self.codes(mismatch))
        self.assertIn("invalid_archive", self.codes(audit(self.path, integrity="sha512-INVALID")))

    def test_member_count_and_payload_limits(self):
        self.make([("package/big", b"x" * 2048)])
        for limits in (Limits(members=2), Limits(member_bytes=1024), Limits(total_file_bytes=100), Limits(manifest_bytes=8), Limits(archive_bytes=10)):
            with self.subTest(limits=limits):
                self.assertIn("budget_exceeded", self.codes(audit(self.path, limits=limits)))

    def test_gzip_bomb_after_tar_end_marker_is_still_bounded(self):
        self.make()
        tar_bytes = gzip.decompress(self.path.read_bytes())
        self.path.write_bytes(gzip.compress(tar_bytes + b"\0" * 200_000))
        self.assertIn("budget_exceeded", self.codes(audit(self.path, limits=Limits(stream_bytes=32_768))))

    def test_gzip_crc_is_checked_even_after_tar_end_marker(self):
        self.make()
        data = bytearray(self.path.read_bytes())
        data[-8] ^= 1
        self.path.write_bytes(data)
        self.assertIn("invalid_archive", self.codes(audit(self.path)))

    def test_missing_and_unsafe_entrypoints(self):
        for target, expected in (("missing.js", "entrypoint_missing"), ("../secret", "unsafe_entrypoint"), ("/absolute", "unsafe_entrypoint")):
            with self.subTest(target=target):
                self.make(manifest={"name": "x", "version": "1", "license": "MIT", "main": target})
                self.assertIn(expected, self.codes(audit(self.path)))

    def test_main_extension_resolution_exports_and_pattern_warning(self):
        self.make(manifest={"name": "x", "version": "1", "license": "MIT", "main": "bin", "exports": {".": "./bin.js", "./extra/*": "./extra/*.js"}})
        result = audit(self.path)
        self.assertEqual(result["status"], "warning")
        self.assertEqual(self.codes(result), {"entrypoint_pattern"})

    def test_duplicate_manifest_keys_fail(self):
        self.make([("package/package.json", b'{"name":"first","name":"second","version":"1"}')])
        self.assertIn("invalid_archive", self.codes(audit(self.path)))

    def test_non_json_numbers_in_manifest_fail(self):
        self.make([("package/package.json", b'{"name":"x","version":"1","license":NaN}')])
        self.assertIn("invalid_archive", self.codes(audit(self.path)))

    def test_lifecycle_scripts_are_only_reported(self):
        sentinel = Path(self.temp.name) / "SHOULD_NOT_EXIST"
        self.make(manifest={"name": "x", "version": "1", "license": "MIT", "scripts": {"postinstall": f"touch {sentinel}"}})
        self.assertIn("lifecycle_script", self.codes(audit(self.path)))
        self.assertFalse(sentinel.exists())

    def test_invalid_missing_and_truncated_input_report_failure(self):
        self.path.write_bytes(b"not a gzip archive")
        self.assertEqual(audit(self.path)["status"], "fail")
        self.make()
        self.path.write_bytes(self.path.read_bytes()[:40])
        self.assertEqual(audit(self.path)["status"], "fail")
        self.assertEqual(audit(self.path.parent / "absent")["status"], "fail")

    def test_cli_outputs_parseable_json_and_failure_exit(self):
        self.make([("package/../escape", b"x")])
        proc = subprocess.run([sys.executable, "-m", "npm_tarball_audit", str(self.path), "--json"], capture_output=True, text=True)
        self.assertEqual(proc.returncode, 1)
        self.assertEqual(json.loads(proc.stdout)["status"], "fail")

    def test_limits_must_be_positive(self):
        with self.assertRaises(ValueError):
            Limits(members=0)


if __name__ == "__main__":
    unittest.main()
