"""Offline CLI coverage with synthetic npm tarballs only."""

from contextlib import redirect_stderr, redirect_stdout
import io
import json
from pathlib import Path
import subprocess
import sys
import tarfile
import tempfile
import unittest
from unittest.mock import patch

from npm_tarball_audit import __main__ as cli

REPO = Path(__file__).resolve().parents[1]


class SarifCLI(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)

    def archive(self, **changes):
        manifest = {"name": "synthetic-example", "version": "1.0.0", "license": "MIT", **changes}
        path = self.root / "fixture.tgz"
        with tarfile.open(path, "w:gz") as archive:
            for name, payload in (("package/package.json", json.dumps(manifest).encode()),
                                  ("package/LICENSE", b"Synthetic fixture; not a real distribution")):
                member = tarfile.TarInfo(name)
                member.size = len(payload)
                archive.addfile(member, io.BytesIO(payload))
        return path

    def run_cli(self, *args):
        env = {"PATH": "/usr/bin:/bin", "LANG": "C.UTF-8", "PYTHONPATH": str(REPO / "src"),
               "PYTHONDONTWRITEBYTECODE": "1", "PYTHONNOUSERSITE": "1"}
        return subprocess.run([sys.executable, "-m", "npm_tarball_audit", *map(str, args)],
                              cwd=REPO, env=env, capture_output=True, text=True, timeout=5)

    def test_pass_warning_and_failure_keep_audit_exit_codes(self):
        for changes, expected, codes in (({}, 0, []),
                                         ({"scripts": {"install": "never executed"}}, 0, ["lifecycle_script"]),
                                         ({"main": "absent.js"}, 1, ["entrypoint_missing"])):
            with self.subTest(changes=changes):
                result = self.run_cli(self.archive(**changes), "--sarif")
                self.assertEqual(result.returncode, expected, result.stderr)
                self.assertEqual(result.stderr, "")
                run = json.loads(result.stdout)["runs"][0]
                self.assertEqual([item["ruleId"] for item in run["results"]], ["NTA/" + code for code in codes])

    def test_malformed_and_missing_archives_export_redacted_audit_failures(self):
        invalid = self.root / "SYNTHETIC_PRIVATE_MARKER.tgz"
        for exists in (False, True):
            with self.subTest(exists=exists):
                if exists:
                    invalid.write_bytes(b"not a gzip archive")
                result = self.run_cli(invalid, "--sarif")
                self.assertEqual(result.returncode, 1, result.stderr)
                data = json.loads(result.stdout)
                self.assertEqual(data["runs"][0]["results"][0]["ruleId"], "NTA/invalid_archive")
                self.assertNotIn("SYNTHETIC_PRIVATE_MARKER", result.stdout)
                self.assertNotIn(str(self.root), result.stdout + result.stderr)

    def test_audit_options_still_apply_without_exporting_inventory_or_identity(self):
        archive = self.archive()
        valid = self.run_cli(archive, "--sarif", "--include-inventory", "--expected-name", "synthetic-example")
        self.assertEqual(valid.returncode, 0, valid.stderr)
        self.assertNotIn("synthetic-example", valid.stdout)
        self.assertNotIn("inventory", valid.stdout)
        mismatch = self.run_cli(archive, "--sarif", "--expected-version", "SYNTHETIC_PRIVATE_MARKER")
        self.assertEqual(mismatch.returncode, 1, mismatch.stderr)
        self.assertEqual(json.loads(mismatch.stdout)["runs"][0]["results"][0]["ruleId"], "NTA/identity_mismatch")
        self.assertNotIn("SYNTHETIC_PRIVATE_MARKER", mismatch.stdout)

    def test_sarif_conflicts_with_json_comparison_and_absent_archive(self):
        for args in (("--sarif", "--json", "fixture.tgz"),
                     ("--compare", "before.json", "after.json", "--sarif"),
                     ("--sarif",)):
            with self.subTest(args=args):
                result = self.run_cli(*args)
                self.assertEqual(result.returncode, 2)
                self.assertEqual(result.stdout, "")
                self.assertNotIn("Traceback", result.stderr)

    def test_exporter_rejection_is_generic_stderr_and_no_partial_output(self):
        data = {"schema": "npm-tarball-audit/v1", "status": "fail",
                "package_executed": False, "files_extracted": False,
                "findings": [{"code": "invalid_archive", "level": "error",
                              "message": "SYNTHETIC_PRIVATE_MARKER"}] * 20001}
        stdout, stderr = io.StringIO(), io.StringIO()
        with patch.object(cli, "audit", return_value=data), redirect_stdout(stdout), redirect_stderr(stderr):
            result = cli.main(["SYNTHETIC_PRIVATE_MARKER.tgz", "--sarif"])
        self.assertEqual(result, 2)
        self.assertEqual(stdout.getvalue(), "")
        self.assertEqual(stderr.getvalue(), "Cannot export SARIF: use a valid, bounded offline audit report.\n")

    def test_existing_default_and_json_audit_output_remain_available(self):
        archive = self.archive()
        human, machine = self.run_cli(archive), self.run_cli(archive, "--json")
        self.assertEqual(human.returncode, 0)
        self.assertIn("PASS:", human.stdout)
        self.assertEqual(machine.returncode, 0)
        self.assertEqual(json.loads(machine.stdout)["schema"], "npm-tarball-audit/v1")


if __name__ == "__main__":
    unittest.main()
