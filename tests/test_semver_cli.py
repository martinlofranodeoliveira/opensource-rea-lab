"""Regression tests for the --strict-semver CLI flag."""

import contextlib
import io
import json
import tarfile
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from npm_tarball_audit import __main__ as cli

FIXED_MSG = "package.json version must be valid SemVer within the supported length budget"


def _make_tgz(directory, name, manifest):
    tgz = Path(directory) / name
    with tarfile.open(tgz, "w:gz") as tf:
        if manifest is not None:
            if isinstance(manifest, dict):
                raw = json.dumps(manifest).encode("utf-8")
            else:
                raw = manifest
            info = tarfile.TarInfo("package/package.json")
            info.size = len(raw)
            info.mode = 0o644
            tf.addfile(info, io.BytesIO(raw))
        payload = b"x = 1\n"
        info = tarfile.TarInfo("package/index.js")
        info.size = len(payload)
        info.mode = 0o644
        tf.addfile(info, io.BytesIO(payload))
        lic = b"MIT\n"
        info = tarfile.TarInfo("package/LICENSE")
        info.size = len(lic)
        info.mode = 0o644
        tf.addfile(info, io.BytesIO(lic))
    return str(tgz)


def _run(args):
    out = io.StringIO()
    err = io.StringIO()
    with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
        try:
            code = cli.main(args)
        except SystemExit as exc:
            code = exc.code
    return code, out.getvalue(), err.getvalue()


def _codes(report):
    return [f["code"] for f in report["findings"]]


def _by_code(report, code):
    return [f for f in report["findings"] if f["code"] == code]


class StrictSemverCliTest(unittest.TestCase):
    def test_default_human_ignores_invalid(self):
        with tempfile.TemporaryDirectory() as td:
            tgz = _make_tgz(td, "pkg.tgz", {"name": "pkg", "version": "not-semver", "license": "MIT"})
            code, out, _ = _run([tgz])
            self.assertEqual(code, 0)
            self.assertIn("PASS", out)
            self.assertNotIn("manifest_version", out)

    def test_default_json_ignores_invalid(self):
        with tempfile.TemporaryDirectory() as td:
            tgz = _make_tgz(td, "pkg.tgz", {"name": "pkg", "version": "1.2", "license": "MIT"})
            code, out, _ = _run([tgz, "--json"])
            self.assertEqual(code, 0)
            report = json.loads(out)
            self.assertEqual(report["status"], "pass")
            self.assertNotIn("manifest_version", _codes(report))

    def test_strict_valid_human(self):
        with tempfile.TemporaryDirectory() as td:
            tgz = _make_tgz(td, "pkg.tgz", {"name": "pkg", "version": "1.2.3", "license": "MIT"})
            code, out, _ = _run([tgz, "--strict-semver"])
            self.assertEqual(code, 0)
            self.assertIn("PASS", out)
            self.assertNotIn("manifest_version", out)

    def test_strict_invalid_human(self):
        with tempfile.TemporaryDirectory() as td:
            tgz = _make_tgz(td, "pkg.tgz", {"name": "pkg", "version": "not-semver", "license": "MIT"})
            code, out, _ = _run([tgz, "--strict-semver"])
            self.assertEqual(code, 1)
            self.assertIn("FAIL", out)
            self.assertIn("manifest_version", out)
            self.assertIn(FIXED_MSG, out)

    def test_strict_valid_json(self):
        with tempfile.TemporaryDirectory() as td:
            tgz = _make_tgz(td, "pkg.tgz", {"name": "pkg", "version": "1.2.3", "license": "MIT"})
            code, out, _ = _run([tgz, "--strict-semver", "--json"])
            self.assertEqual(code, 0)
            report = json.loads(out)
            self.assertEqual(report["status"], "pass")
            self.assertEqual(_by_code(report, "manifest_version"), [])
            self.assertEqual(report["package"]["version"], "1.2.3")

    def test_strict_invalid_json(self):
        with tempfile.TemporaryDirectory() as td:
            tgz = _make_tgz(td, "pkg.tgz", {"name": "pkg", "version": "1.2", "license": "MIT"})
            code, out, _ = _run([tgz, "--strict-semver", "--json"])
            self.assertEqual(code, 1)
            report = json.loads(out)
            self.assertEqual(report["status"], "fail")
            found = _by_code(report, "manifest_version")
            self.assertEqual(len(found), 1)
            self.assertEqual(found[0]["message"], FIXED_MSG)
            self.assertEqual(found[0]["level"], "error")
            self.assertNotIn("member", found[0])

    def test_strict_valid_sarif(self):
        with tempfile.TemporaryDirectory() as td:
            tgz = _make_tgz(td, "pkg.tgz", {"name": "pkg", "version": "1.2.3", "license": "MIT"})
            code, out, _ = _run([tgz, "--strict-semver", "--sarif"])
            self.assertEqual(code, 0)
            doc = json.loads(out)
            self.assertEqual(doc["version"], "2.1.0")
            self.assertIn("runs", doc)
            self.assertNotIn("manifest_version", out)

    def test_strict_invalid_sarif(self):
        with tempfile.TemporaryDirectory() as td:
            tgz = _make_tgz(td, "pkg.tgz", {"name": "pkg", "version": "not-semver", "license": "MIT"})
            code, out, _ = _run([tgz, "--strict-semver", "--sarif"])
            self.assertEqual(code, 1)
            doc = json.loads(out)
            self.assertEqual(doc["version"], "2.1.0")
            self.assertIn("runs", doc)
            self.assertIn("manifest_version", out)

    def test_blank_version_identity_only(self):
        for blank in ["", "   "]:
            with self.subTest(blank=repr(blank)):
                with tempfile.TemporaryDirectory() as td:
                    tgz = _make_tgz(td, "pkg.tgz", {"name": "pkg", "version": blank, "license": "MIT"})
                    code, out, _ = _run([tgz, "--strict-semver", "--json"])
                    self.assertEqual(code, 1)
                    report = json.loads(out)
                    self.assertIn("manifest_identity", _codes(report))
                    self.assertNotIn("manifest_version", _codes(report))

    def test_missing_and_nonstring_identity_only(self):
        with tempfile.TemporaryDirectory() as td:
            tgz = _make_tgz(td, "a.tgz", {"name": "pkg", "license": "MIT"})
            code, out, _ = _run([tgz, "--strict-semver", "--json"])
            self.assertEqual(code, 1)
            report = json.loads(out)
            self.assertIn("manifest_identity", _codes(report))
            self.assertNotIn("manifest_version", _codes(report))
        with tempfile.TemporaryDirectory() as td:
            tgz = _make_tgz(td, "b.tgz", {"name": "pkg", "version": 123, "license": "MIT"})
            code, out, _ = _run([tgz, "--strict-semver", "--json"])
            self.assertEqual(code, 1)
            report = json.loads(out)
            self.assertIn("manifest_identity", _codes(report))
            self.assertNotIn("manifest_version", _codes(report))

    def test_warning_only_retains_zero_with_strict(self):
        with tempfile.TemporaryDirectory() as td:
            manifest = {"name": "pkg", "version": "1.2.3", "license": "MIT", "scripts": {"install": "echo hi"}}
            tgz = _make_tgz(td, "pkg.tgz", manifest)
            code, out, _ = _run([tgz, "--strict-semver", "--json"])
            self.assertEqual(code, 0)
            report = json.loads(out)
            self.assertEqual(report["status"], "warning")
            self.assertIn("lifecycle_script", _codes(report))
            self.assertNotIn("manifest_version", _codes(report))

    def _assert_compare_rejected(self, argv):
        with mock.patch.object(cli, "_compare_reports") as fake_compare:
            with mock.patch.object(cli, "audit") as fake_audit:
                out = io.StringIO()
                err = io.StringIO()
                with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
                    with self.assertRaises(SystemExit) as ctx:
                        cli.main(argv)
                self.assertEqual(ctx.exception.code, 2)
                self.assertIn("--compare", err.getvalue())
                fake_compare.assert_not_called()
                fake_audit.assert_not_called()

    def test_compare_conflict_strict_first(self):
        with tempfile.TemporaryDirectory() as td:
            before = str(Path(td) / "missing-before.json")
            after = str(Path(td) / "missing-after.json")
            self._assert_compare_rejected(["--strict-semver", "--compare", before, after])

    def test_compare_conflict_strict_last(self):
        with tempfile.TemporaryDirectory() as td:
            before = str(Path(td) / "missing-before.json")
            after = str(Path(td) / "missing-after.json")
            self._assert_compare_rejected(["--compare", before, after, "--strict-semver"])

    def test_compare_conflict_with_json_still_rejected(self):
        with tempfile.TemporaryDirectory() as td:
            before = str(Path(td) / "missing-before.json")
            after = str(Path(td) / "missing-after.json")
            self._assert_compare_rejected(["--compare", before, after, "--json", "--strict-semver"])

    def test_compare_preserved_without_flag(self):
        with tempfile.TemporaryDirectory() as td:
            tgz = _make_tgz(td, "pkg.tgz", {"name": "pkg", "version": "1.2.3", "license": "MIT"})
            code1, out1, _ = _run([tgz, "--json", "--include-inventory"])
            self.assertEqual(code1, 0)
            code2, out2, _ = _run([tgz, "--json", "--include-inventory"])
            self.assertEqual(code2, 0)
            before = Path(td) / "before.json"
            after = Path(td) / "after.json"
            before.write_text(out1, encoding="utf-8")
            after.write_text(out2, encoding="utf-8")
            code3, out3, _ = _run(["--compare", str(before), str(after)])
            self.assertEqual(code3, 0)
            self.assertIn("0 added", out3)

    def test_expected_version_forwarding(self):
        with tempfile.TemporaryDirectory() as td:
            tgz = _make_tgz(td, "pkg.tgz", {"name": "pkg", "version": "1.2.3", "license": "MIT"})
            code, out, _ = _run([tgz, "--strict-semver", "--expected-version", "1.2.3", "--json"])
            self.assertEqual(code, 0)
            self.assertNotIn("identity_mismatch", _codes(json.loads(out)))
            code, out, _ = _run([tgz, "--strict-semver", "--expected-version", "9.9.9", "--json"])
            self.assertEqual(code, 1)
            report = json.loads(out)
            self.assertIn("identity_mismatch", _codes(report))
            self.assertNotIn("manifest_version", _codes(report))

    def test_inventory_forwarding_with_strict(self):
        with tempfile.TemporaryDirectory() as td:
            tgz = _make_tgz(td, "pkg.tgz", {"name": "pkg", "version": "1.2.3", "license": "MIT"})
            code, out, _ = _run([tgz, "--strict-semver", "--include-inventory", "--json"])
            self.assertEqual(code, 0)
            report = json.loads(out)
            self.assertIn("inventory", report)
            self.assertTrue(len(report["inventory"]) > 0)
        with tempfile.TemporaryDirectory() as td:
            tgz = _make_tgz(td, "pkg.tgz", {"name": "pkg", "version": "bad", "license": "MIT"})
            code, out, _ = _run([tgz, "--strict-semver", "--include-inventory", "--json"])
            self.assertEqual(code, 1)
            report = json.loads(out)
            self.assertIn("inventory", report)
            self.assertIn("manifest_version", _codes(report))

    def test_help_lists_flag(self):
        code, out, _ = _run(["--help"])
        self.assertEqual(code, 0)
        self.assertIn("--strict-semver", out)

    def test_strict_value_rejected(self):
        with tempfile.TemporaryDirectory() as td:
            tgz = _make_tgz(td, "pkg.tgz", {"name": "pkg", "version": "1.2.3", "license": "MIT"})
            code, _, err = _run([tgz, "--strict-semver=true"])
            self.assertEqual(code, 2)
            self.assertNotEqual(err, "")

    def test_extra_positional_rejected(self):
        with tempfile.TemporaryDirectory() as td:
            tgz = _make_tgz(td, "pkg.tgz", {"name": "pkg", "version": "1.2.3", "license": "MIT"})
            code, _, err = _run([tgz, "extra"])
            self.assertEqual(code, 2)
            self.assertNotEqual(err, "")

    def test_missing_archive_rejected(self):
        code, _, err = _run([])
        self.assertEqual(code, 2)
        self.assertNotEqual(err, "")
        code, _, err = _run(["--strict-semver"])
        self.assertEqual(code, 2)
        self.assertNotEqual(err, "")

    def test_archive_named_true(self):
        with tempfile.TemporaryDirectory() as td:
            tgz = _make_tgz(td, "true", {"name": "pkg", "version": "1.2.3", "license": "MIT"})
            code, out, _ = _run([tgz])
            self.assertEqual(code, 0)
            self.assertIn("PASS", out)
            code, out, _ = _run([tgz, "--strict-semver"])
            self.assertEqual(code, 0)
            self.assertIn("PASS", out)
            code, out, _ = _run([tgz, "--strict-semver", "--json"])
            self.assertEqual(code, 0)
            self.assertNotIn("manifest_version", _codes(json.loads(out)))


if __name__ == "__main__":
    unittest.main()
