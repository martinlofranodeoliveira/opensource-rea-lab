"""Synthetic regression tests for strict_package_name opt-in checks."""

import json
import tempfile
import unittest
from unittest import mock

try:
    from npm_tarball_audit.audit import audit
except ImportError:
    from src.npm_tarball_audit.audit import audit

try:
    from npm_tarball_audit import __main__ as cli
except ImportError:
    from src.npm_tarball_audit import __main__ as cli

try:
    from test_semver_cli import _make_tgz, _run
except ImportError:
    from tests.test_semver_cli import _make_tgz, _run

FIXED = "package.json name must follow the supported local ASCII package-name syntax"


def _codes(report):
    return [f["code"] for f in report["findings"]]


def _by_code(report, code):
    return [f for f in report["findings"] if f["code"] == code]


class ManifestPackageNamesTest(unittest.TestCase):
    def test_default_ignores_invalid(self):
        with tempfile.TemporaryDirectory() as td:
            p = _make_tgz(td, "pkg.tgz", {"name": "Bad Name!", "version": "1.2.3", "license": "MIT"})
            rep = audit(p)
            self.assertNotIn("manifest_name", _codes(rep))
            self.assertEqual(rep["status"], "pass")

    def test_explicit_false_ignores_invalid(self):
        with tempfile.TemporaryDirectory() as td:
            p = _make_tgz(td, "pkg.tgz", {"name": "Bad Name!", "version": "1.2.3", "license": "MIT"})
            rep = audit(p, strict_package_name=False)
            self.assertNotIn("manifest_name", _codes(rep))
            self.assertEqual(rep["status"], "pass")

    def test_bool_rejected_before_io(self):
        bad = [0, 1, None, "true", "false", b"true", 1.0, [], {}]
        with tempfile.TemporaryDirectory() as td:
            missing = td + "/missing.tgz"
            for flag in bad:
                with self.subTest(flag=repr(flag)):
                    with self.assertRaises(ValueError) as ctx:
                        audit(missing, strict_package_name=flag)
                    self.assertEqual(str(ctx.exception), "strict_package_name must be a boolean")
                    self.assertNotIn(repr(flag), str(ctx.exception))

    def test_bool_accepted(self):
        with tempfile.TemporaryDirectory() as td:
            p = _make_tgz(td, "pkg.tgz", {"name": "example", "version": "1.2.3", "license": "MIT"})
            self.assertNotIn("manifest_name", _codes(audit(p, strict_package_name=True)))
            self.assertNotIn("manifest_name", _codes(audit(p, strict_package_name=False)))

    def test_valid_unscoped(self):
        for name in ["a", "example", "my-name", "a.b_c-d9"]:
            with self.subTest(name=name):
                with tempfile.TemporaryDirectory() as td:
                    p = _make_tgz(td, "pkg.tgz", {"name": name, "version": "1.2.3", "license": "MIT"})
                    rep = audit(p, strict_package_name=True)
                    self.assertEqual(_by_code(rep, "manifest_name"), [])

    def test_valid_scoped(self):
        for name in ["@a/b", "@my-scope/my-name", "@scope123/name-1.2"]:
            with self.subTest(name=name):
                with tempfile.TemporaryDirectory() as td:
                    p = _make_tgz(td, "pkg.tgz", {"name": name, "version": "1.2.3", "license": "MIT"})
                    rep = audit(p, strict_package_name=True)
                    self.assertEqual(_by_code(rep, "manifest_name"), [])

    def test_inclusive_214_boundaries(self):
        valid_unscoped = "a" * 214
        invalid_unscoped = "a" * 215
        valid_scoped = "@" + "a" * 106 + "/" + "b" * 106
        invalid_scoped = "@" + "a" * 106 + "/" + "b" * 107
        self.assertEqual(len(valid_unscoped), 214)
        self.assertEqual(len(invalid_unscoped), 215)
        self.assertEqual(len(valid_scoped), 214)
        self.assertEqual(len(invalid_scoped), 215)
        with tempfile.TemporaryDirectory() as td:
            p = _make_tgz(td, "a.tgz", {"name": valid_unscoped, "version": "1.2.3", "license": "MIT"})
            self.assertEqual(_by_code(audit(p, strict_package_name=True), "manifest_name"), [])
            p = _make_tgz(td, "b.tgz", {"name": valid_scoped, "version": "1.2.3", "license": "MIT"})
            self.assertEqual(_by_code(audit(p, strict_package_name=True), "manifest_name"), [])
            p = _make_tgz(td, "c.tgz", {"name": invalid_unscoped, "version": "1.2.3", "license": "MIT"})
            self.assertEqual(len(_by_code(audit(p, strict_package_name=True), "manifest_name")), 1)
            p = _make_tgz(td, "d.tgz", {"name": invalid_scoped, "version": "1.2.3", "license": "MIT"})
            self.assertEqual(len(_by_code(audit(p, strict_package_name=True), "manifest_name")), 1)

    def test_invalid_syntax_table(self):
        bad = ["Example", "_lead", "-lead", ".lead", "foo/bar", "@scope", "@scope/", "@/name", "@a/b/c", "foo@bar", "UPPER/name"]
        for name in bad:
            with self.subTest(name=name):
                with tempfile.TemporaryDirectory() as td:
                    p = _make_tgz(td, "pkg.tgz", {"name": name, "version": "1.2.3", "license": "MIT"})
                    rep = audit(p, strict_package_name=True)
                    self.assertEqual(len(_by_code(rep, "manifest_name")), 1)
                    self.assertNotIn("manifest_name", _codes(audit(p)))

    def test_raw_whitespace_rejected(self):
        for name in [" example", "example ", "  example  ", "\texample", "example\n"]:
            with self.subTest(name=repr(name)):
                with tempfile.TemporaryDirectory() as td:
                    p = _make_tgz(td, "pkg.tgz", {"name": name, "version": "1.2.3", "license": "MIT"})
                    rep = audit(p, strict_package_name=True)
                    self.assertEqual(len(_by_code(rep, "manifest_name")), 1)

    def test_unicode_rejected(self):
        for name in ["caf\u00e9", "\u65e5example", "example\U0001f600"]:
            with self.subTest(name=repr(name)):
                with tempfile.TemporaryDirectory() as td:
                    p = _make_tgz(td, "pkg.tgz", {"name": name, "version": "1.2.3", "license": "MIT"})
                    self.assertEqual(len(_by_code(audit(p, strict_package_name=True), "manifest_name")), 1)

    def test_identity_only_missing(self):
        with tempfile.TemporaryDirectory() as td:
            p = _make_tgz(td, "pkg.tgz", {"version": "1.2.3", "license": "MIT"})
            rep = audit(p, strict_package_name=True)
            self.assertIn("manifest_identity", _codes(rep))
            self.assertNotIn("manifest_name", _codes(rep))

    def test_identity_only_type(self):
        for name in [None, 123, 1.5, [], {}]:
            with self.subTest(name=repr(name)):
                with tempfile.TemporaryDirectory() as td:
                    p = _make_tgz(td, "pkg.tgz", {"name": name, "version": "1.2.3", "license": "MIT"})
                    rep = audit(p, strict_package_name=True)
                    self.assertIn("manifest_identity", _codes(rep))
                    self.assertNotIn("manifest_name", _codes(rep))

    def test_identity_only_blank(self):
        for name in ["", "   ", "\n\t "]:
            with self.subTest(name=repr(name)):
                with tempfile.TemporaryDirectory() as td:
                    p = _make_tgz(td, "pkg.tgz", {"name": name, "version": "1.2.3", "license": "MIT"})
                    rep = audit(p, strict_package_name=True)
                    self.assertIn("manifest_identity", _codes(rep))
                    self.assertNotIn("manifest_name", _codes(rep))

    def test_exact_finding_no_member(self):
        with tempfile.TemporaryDirectory() as td:
            p = _make_tgz(td, "pkg.tgz", {"name": "Bad Name!", "version": "1.2.3", "license": "MIT"})
            rep = audit(p, strict_package_name=True)
            found = _by_code(rep, "manifest_name")
            self.assertEqual(len(found), 1)
            self.assertEqual(found[0], {"level": "error", "code": "manifest_name", "message": FIXED})
            self.assertNotIn("member", found[0])
            self.assertEqual(rep["status"], "fail")
            self.assertEqual(rep["package"]["name"], "Bad Name!")

    def test_order_before_semver(self):
        with tempfile.TemporaryDirectory() as td:
            p = _make_tgz(td, "pkg.tgz", {"name": "Bad Name!", "version": "not-semver", "license": "MIT"})
            rep = audit(p, strict_package_name=True, strict_semver=True)
            codes = _codes(rep)
            self.assertEqual(codes[:2], ["manifest_name", "manifest_version"])
            self.assertEqual(codes.count("manifest_name"), 1)

    def test_expected_identity_independent(self):
        with tempfile.TemporaryDirectory() as td:
            p = _make_tgz(td, "pkg.tgz", {"name": "Bad Name!", "version": "1.2.3", "license": "MIT"})
            rep = audit(p, strict_package_name=True, expected_name="other")
            self.assertIn("manifest_name", _codes(rep))
            self.assertIn("identity_mismatch", _codes(rep))
            rep2 = audit(p, strict_package_name=True, expected_name="Bad Name!")
            self.assertIn("manifest_name", _codes(rep2))
            self.assertNotIn("identity_mismatch", _codes(rep2))

    def test_inventory_retained(self):
        with tempfile.TemporaryDirectory() as td:
            p = _make_tgz(td, "pkg.tgz", {"name": "Bad Name!", "version": "1.2.3", "license": "MIT"})
            rep = audit(p, strict_package_name=True, include_inventory=True)
            self.assertIn("manifest_name", _codes(rep))
            self.assertEqual(rep["status"], "fail")
            self.assertTrue(len(rep["inventory"]) > 0)
            for rec in rep["inventory"]:
                self.assertEqual(set(rec.keys()), {"path", "bytes", "sha256"})

    def test_cli_help(self):
        code, out, _ = _run(["--help"])
        self.assertEqual(code, 0)
        self.assertIn("--strict-package-name", out)

    def test_cli_human_json_sarif(self):
        with tempfile.TemporaryDirectory() as td:
            bad = _make_tgz(td, "bad.tgz", {"name": "Bad Name!", "version": "1.2.3", "license": "MIT"})
            good = _make_tgz(td, "good.tgz", {"name": "example", "version": "1.2.3", "license": "MIT"})
            code, out, _ = _run([bad, "--strict-package-name"])
            self.assertEqual(code, 1)
            self.assertIn("FAIL", out)
            self.assertIn("manifest_name", out)
            code, out, _ = _run([bad, "--strict-package-name", "--json"])
            self.assertEqual(code, 1)
            report = json.loads(out)
            self.assertEqual(report["status"], "fail")
            self.assertEqual(len(_by_code(report, "manifest_name")), 1)
            code, out, _ = _run([good, "--strict-package-name", "--json"])
            self.assertEqual(code, 0)
            self.assertNotIn("manifest_name", _codes(json.loads(out)))
            code, out, _ = _run([bad, "--strict-package-name", "--sarif"])
            self.assertEqual(code, 1)
            doc = json.loads(out)
            self.assertEqual(doc["version"], "2.1.0")
            self.assertIn("manifest_name", out)

    def test_cli_forwarding(self):
        with tempfile.TemporaryDirectory() as td:
            tgz = _make_tgz(td, "pkg.tgz", {"name": "example", "version": "1.2.3", "license": "MIT"})
            good = {"status": "pass", "package": {"name": "example", "version": "1.2.3"}, "sha256": "x", "member_count": 0, "regular_file_bytes": 0, "findings": []}
            with mock.patch.object(cli, "audit") as fake:
                fake.return_value = dict(good)
                code, _, _ = _run([tgz, "--strict-package-name", "--json"])
                self.assertEqual(code, 0)
                _, kwargs = fake.call_args
                self.assertEqual(kwargs.get("strict_package_name"), True)
            with mock.patch.object(cli, "audit") as fake:
                fake.return_value = dict(good)
                code, _, _ = _run([tgz, "--json"])
                self.assertEqual(code, 0)
                _, kwargs = fake.call_args
                self.assertEqual(kwargs.get("strict_package_name"), False)

    def _assert_compare_rejected(self, argv):
        with mock.patch.object(cli, "_compare_reports") as fake_compare:
            with mock.patch.object(cli, "audit") as fake_audit:
                code, out, err = _run(argv)
                self.assertEqual(code, 2)
                self.assertIn("--compare", err)
                self.assertEqual(out, "")
                fake_compare.assert_not_called()
                fake_audit.assert_not_called()

    def test_compare_conflict_first(self):
        with tempfile.TemporaryDirectory() as td:
            before = td + "/before.json"
            after = td + "/after.json"
            self._assert_compare_rejected(["--strict-package-name", "--compare", before, after])

    def test_compare_conflict_last(self):
        with tempfile.TemporaryDirectory() as td:
            before = td + "/before.json"
            after = td + "/after.json"
            self._assert_compare_rejected(["--compare", before, after, "--strict-package-name"])

    def test_compare_conflict_with_json(self):
        with tempfile.TemporaryDirectory() as td:
            before = td + "/before.json"
            after = td + "/after.json"
            self._assert_compare_rejected(["--compare", before, after, "--json", "--strict-package-name"])

    def test_cli_value_rejected(self):
        with tempfile.TemporaryDirectory() as td:
            tgz = _make_tgz(td, "pkg.tgz", {"name": "example", "version": "1.2.3", "license": "MIT"})
            code, _, err = _run([tgz, "--strict-package-name=true"])
            self.assertEqual(code, 2)
            self.assertNotEqual(err, "")


if __name__ == "__main__":
    unittest.main()
