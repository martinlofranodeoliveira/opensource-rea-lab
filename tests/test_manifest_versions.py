"""Synthetic regression tests for strict_semver opt-in manifest checks."""

import io
import json
import tarfile
import tempfile
import unittest
from pathlib import Path

try:
    from npm_tarball_audit.audit import audit
except ImportError:  # src-layout checkout
    from src.npm_tarball_audit.audit import audit

FIXED_MSG = "package.json version must be valid SemVer within the supported length budget"
BASE = {"name": "pkg", "license": "MIT"}
EXPECTED_KEYS = {
    "schema",
    "status",
    "sha256",
    "archive_bytes",
    "decompressed_bytes_read",
    "member_count",
    "regular_file_bytes",
    "package",
    "findings",
    "scope",
    "package_executed",
    "files_extracted",
}


def _write_tgz(tmpdir, manifest):
    tgz_path = Path(tmpdir) / "pkg.tgz"
    with tarfile.open(tgz_path, "w:gz") as tf:
        if manifest is None:
            payload = b"placeholder"
            info = tarfile.TarInfo("package/index.js")
            info.size = len(payload)
            info.mode = 0o644
            tf.addfile(info, io.BytesIO(payload))
        else:
            if isinstance(manifest, dict):
                raw = json.dumps(manifest).encode("utf-8")
            elif isinstance(manifest, bytes):
                raw = manifest
            else:
                raise AssertionError("helper expects dict/bytes/None")
            info = tarfile.TarInfo("package/package.json")
            info.size = len(raw)
            info.mode = 0o644
            tf.addfile(info, io.BytesIO(raw))
        lic = b"MIT"
        info = tarfile.TarInfo("package/LICENSE")
        info.size = len(lic)
        info.mode = 0o644
        tf.addfile(info, io.BytesIO(lic))
    return tgz_path


def _codes(report):
    return [f["code"] for f in report["findings"]]


def _by_code(report, code):
    return [f for f in report["findings"] if f["code"] == code]


def _long_version(total):
    need = total - len("1.2.3+")
    return "1.2.3+" + "a" * need


class ManifestVersionsTest(unittest.TestCase):
    def test_implicit_default_ignores_invalid_syntax(self):
        with tempfile.TemporaryDirectory() as td:
            p = _write_tgz(td, {**BASE, "version": "not-semver"})
            rep = audit(p)
            self.assertNotIn("manifest_version", _codes(rep))
            self.assertNotIn("manifest_identity", _codes(rep))
            self.assertEqual(rep["status"], "pass")

    def test_explicit_false_ignores_invalid_syntax(self):
        with tempfile.TemporaryDirectory() as td:
            p = _write_tgz(td, {**BASE, "version": "1.2"})
            rep = audit(p, strict_semver=False)
            self.assertNotIn("manifest_version", _codes(rep))
            self.assertEqual(rep["status"], "pass")

    def test_strict_valid_plain(self):
        with tempfile.TemporaryDirectory() as td:
            p = _write_tgz(td, {**BASE, "version": "1.2.3"})
            rep = audit(p, strict_semver=True)
            self.assertEqual(_by_code(rep, "manifest_version"), [])
            self.assertEqual(rep["status"], "pass")

    def test_strict_valid_prerelease_and_build(self):
        for v in ["1.0.0-alpha.1", "1.0.0-alpha-beta.2", "1.2.3-rc.1+build.007"]:
            with self.subTest(version=v):
                with tempfile.TemporaryDirectory() as td:
                    p = _write_tgz(td, {**BASE, "version": v})
                    rep = audit(p, strict_semver=True)
                    self.assertEqual(_by_code(rep, "manifest_version"), [])

    def test_strict_build_hyphens_and_leading_zeroes_valid(self):
        for v in ["1.2.3+build-foo-01", "1.2.3+001", "1.2.3-alpha.1+build-foo-01"]:
            with self.subTest(version=v):
                with tempfile.TemporaryDirectory() as td:
                    p = _write_tgz(td, {**BASE, "version": v})
                    rep = audit(p, strict_semver=True)
                    self.assertEqual(_by_code(rep, "manifest_version"), [])

    def test_strict_invalid_core_leading_zero(self):
        with tempfile.TemporaryDirectory() as td:
            p = _write_tgz(td, {**BASE, "version": "01.2.3"})
            rep = audit(p, strict_semver=True)
            found = _by_code(rep, "manifest_version")
            self.assertEqual(len(found), 1)
            self.assertEqual(found[0]["message"], FIXED_MSG)
            self.assertEqual(found[0]["level"], "error")

    def test_strict_invalid_prerelease_leading_zero(self):
        for v in ["1.2.3-01", "1.2.3-alpha.01"]:
            with self.subTest(version=v):
                with tempfile.TemporaryDirectory() as td:
                    p = _write_tgz(td, {**BASE, "version": v})
                    rep = audit(p, strict_semver=True)
                    self.assertEqual(len(_by_code(rep, "manifest_version")), 1)

    def test_strict_invalid_syntax_table(self):
        bad = ["1.2", "1.2.3.4", "v1.2.3", "^1.2.3", "~1.2.3", ">=1.2.3", "*", "1.2.3 ", " 1.2.3"]
        for v in bad:
            with self.subTest(version=v):
                with tempfile.TemporaryDirectory() as td:
                    p = _write_tgz(td, {**BASE, "version": v})
                    rep = audit(p, strict_semver=True)
                    found = _by_code(rep, "manifest_version")
                    self.assertEqual(len(found), 1)
                    self.assertEqual(found[0]["message"], FIXED_MSG)
                    # default must stay compatible
                    rep2 = audit(p)
                    self.assertNotIn("manifest_version", _codes(rep2))

    def test_strict_unicode_whitespace_range_invalid(self):
        for v in ["1.2.3\n", "1.2.3\t", "1.2.3+build bar", "1.2.3\u00e9", "\u00e91.2.3"]:
            with self.subTest(version=repr(v)):
                with tempfile.TemporaryDirectory() as td:
                    p = _write_tgz(td, {**BASE, "version": v})
                    rep = audit(p, strict_semver=True)
                    self.assertEqual(len(_by_code(rep, "manifest_version")), 1)

    def test_boundary_inclusive_4096_valid(self):
        v = _long_version(4096)
        self.assertEqual(len(v), 4096)
        with tempfile.TemporaryDirectory() as td:
            p = _write_tgz(td, {**BASE, "version": v})
            rep = audit(p, strict_semver=True)
            self.assertEqual(_by_code(rep, "manifest_version"), [])

    def test_boundary_over_4097_invalid(self):
        v = _long_version(4097)
        self.assertEqual(len(v), 4097)
        with tempfile.TemporaryDirectory() as td:
            p = _write_tgz(td, {**BASE, "version": v})
            rep = audit(p, strict_semver=True)
            self.assertEqual(len(_by_code(rep, "manifest_version")), 1)
            rep2 = audit(p)
            self.assertNotIn("manifest_version", _codes(rep2))

    def test_missing_version_identity_only(self):
        with tempfile.TemporaryDirectory() as td:
            p = _write_tgz(td, {"name": "pkg", "license": "MIT"})
            rep = audit(p, strict_semver=True)
            self.assertIn("manifest_identity", _codes(rep))
            self.assertNotIn("manifest_version", _codes(rep))

    def test_nonstring_version_identity_only(self):
        with tempfile.TemporaryDirectory() as td:
            p = _write_tgz(td, {**BASE, "version": 123})
            rep = audit(p, strict_semver=True)
            self.assertIn("manifest_identity", _codes(rep))
            self.assertNotIn("manifest_version", _codes(rep))

    def test_blank_version_identity_only(self):
        for v in ["", "   ", "\n\t "]:
            with self.subTest(version=repr(v)):
                with tempfile.TemporaryDirectory() as td:
                    p = _write_tgz(td, {**BASE, "version": v})
                    rep = audit(p, strict_semver=True)
                    self.assertIn("manifest_identity", _codes(rep))
                    self.assertNotIn("manifest_version", _codes(rep))

    def test_expected_version_match_no_mismatch(self):
        with tempfile.TemporaryDirectory() as td:
            p = _write_tgz(td, {**BASE, "version": "not-semver"})
            rep = audit(p, strict_semver=True, expected_version="not-semver")
            self.assertEqual(len(_by_code(rep, "manifest_version")), 1)
            self.assertNotIn("identity_mismatch", _codes(rep))

    def test_expected_version_mismatch_independent(self):
        with tempfile.TemporaryDirectory() as td:
            p = _write_tgz(td, {**BASE, "version": "not-semver"})
            rep = audit(p, strict_semver=True, expected_version="1.2.3")
            self.assertEqual(len(_by_code(rep, "manifest_version")), 1)
            self.assertIn("identity_mismatch", _codes(rep))
            self.assertEqual(rep["status"], "fail")

    def test_bool_only_flag_before_file_access(self):
        bad = [0, 1, None, "true", "false", b"true", 1.0, [], {}]
        with tempfile.TemporaryDirectory() as td:
            missing = Path(td) / "missing.tgz"
            self.assertFalse(missing.exists())
            for flag in bad:
                with self.subTest(flag=repr(flag)):
                    with self.assertRaises(ValueError) as ctx:
                        audit(missing, strict_semver=flag)
                    self.assertEqual(str(ctx.exception), "strict_semver must be a boolean")
                    self.assertNotIn(repr(flag), str(ctx.exception))

    def test_bool_flags_accepted(self):
        with tempfile.TemporaryDirectory() as td:
            p = _write_tgz(td, {**BASE, "version": "1.2.3"})
            self.assertNotIn("manifest_version", _codes(audit(p, strict_semver=True)))
            self.assertNotIn("manifest_version", _codes(audit(p, strict_semver=False)))

    def test_schema_action_flags_and_raw_package(self):
        with tempfile.TemporaryDirectory() as td:
            manifest = {"name": "@scope/pkg", "version": "not-semver", "license": "MIT"}
            p = _write_tgz(td, manifest)
            rep = audit(p, strict_semver=True)
            self.assertEqual(set(rep.keys()), EXPECTED_KEYS)
            self.assertEqual(rep["schema"], "npm-tarball-audit/v1")
            self.assertFalse(rep["package_executed"])
            self.assertFalse(rep["files_extracted"])
            self.assertEqual(rep["package"], manifest)
            self.assertEqual(rep["status"], "fail")
            found = _by_code(rep, "manifest_version")
            self.assertEqual(len(found), 1)
            self.assertEqual(found[0]["message"], FIXED_MSG)
            self.assertNotIn("member", found[0])
            self.assertNotIn("strict_semver", rep)
            # scoped name behavior unchanged
            self.assertNotIn("manifest_identity", _codes(rep))

    def test_malformed_json_has_no_manifest_version(self):
        with tempfile.TemporaryDirectory() as td:
            p = _write_tgz(td, b"{not json")
            rep = audit(p, strict_semver=True)
            self.assertIn("invalid_archive", _codes(rep))
            self.assertNotIn("manifest_version", _codes(rep))


if __name__ == "__main__":
    unittest.main()
