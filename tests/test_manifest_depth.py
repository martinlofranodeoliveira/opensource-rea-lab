import io
import json
import tarfile
import tempfile
import unittest
from pathlib import Path
from contextlib import redirect_stdout

from npm_tarball_audit import Limits, audit
from npm_tarball_audit.__main__ import main


class ManifestDepthTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.path = Path(self.temp.name) / "fixture.tgz"

    def make(self, manifest_data: bytes, *, manifest=None):
        if manifest is None:
            manifest = {"name": "useful-example", "version": "1.0.0", "license": "MIT"}
        with tarfile.open(self.path, "w:gz", format=tarfile.PAX_FORMAT) as tf:
            for name, content in [("package/package.json", manifest_data),
                                  ("package/LICENSE", b"MIT test fixture"),
                                  ("package/bin.js", b"// fixture, never run\n")]:
                entry = tarfile.TarInfo(name)
                entry.size = len(content)
                tf.addfile(entry, io.BytesIO(content))
        return self.path

    def codes(self, report):
        return {f["code"] for f in report["findings"]}

    def nested(self, depth, kind="object"):
        # Build valid raw JSON without recursion in either dumps or fixtures.
        opening, closing = (b'{"child":', b'}') if kind == "object" else (b'[', b']')
        return (b'{"name":"fixture","version":"1.0.0","license":"MIT","data":'
                + opening * (depth - 1) + b'0' + closing * (depth - 1) + b'}')

    def test_exact_depth_boundary_is_allowed(self):
        manifest_data = self.nested(64)
        result = audit(self.make(manifest_data))
        self.assertEqual(result["status"], "pass")
        self.assertNotIn("manifest_depth_exceeded", self.codes(result))
        self.assertFalse(result["package_executed"])
        self.assertFalse(result["files_extracted"])

    def test_over_depth_object_is_rejected(self):
        manifest_data = self.nested(65)
        result = audit(self.make(manifest_data))
        self.assertEqual(result["status"], "fail")
        self.assertIn("manifest_depth_exceeded", self.codes(result))
        self.assertFalse(result["package_executed"])
        self.assertFalse(result["files_extracted"])

    def test_over_depth_array_is_rejected(self):
        manifest_data = self.nested(65, "array")
        result = audit(self.make(manifest_data))
        self.assertEqual(result["status"], "fail")
        self.assertIn("manifest_depth_exceeded", self.codes(result))
        self.assertFalse(result["package_executed"])
        self.assertFalse(result["files_extracted"])

    def test_default_depth_boundary_is_exactly_64(self):
        self.assertEqual(Limits().manifest_depth, 64)
        allowed = self.nested(64)
        rejected = self.nested(65)
        self.assertEqual(audit(self.make(allowed))["status"], "pass")
        self.assertEqual(audit(self.make(rejected))["status"], "fail")
        self.assertIn("manifest_depth_exceeded", self.codes(audit(self.make(rejected))))

    def test_strings_with_braces_and_brackets_do_not_count(self):
        manifest_data = b'{"name":"x","version":"1","license":"MIT","data":"{{{{{{{{{{{{[[[[[[[[[[[["}'
        result = audit(self.make(manifest_data))
        self.assertEqual(result["status"], "pass")
        self.assertNotIn("manifest_depth_exceeded", self.codes(result))

    def test_escaped_quotes_and_backslashes_do_not_count(self):
        for text in ['escaped "quote" [{[{[{[{[{[{[{[{[{[{[{[{[{[{[{[{[{[{[{[{[{[{[{[{[{[{[{[{[{[{[{[{[{[{[{[{[{[{[{[{[{[{[{[{[{[{[{[{[{[{[{[{[{[{[{[{[{[{[{[{[{[{[{[{[{[{[{[{[{[{[{[{[{[{[{[{[{[{[{[{', '\\\\\\\\\\\\\\"}]}]}]}]}]}]}]}]}]}]}]}]}]}]}]}]}]}]}]}]}]}]}]}]}]}]}]}]}]}]}]}]}]}]}]}]}]}]}]}]}]}]}]}]}]}]}]}]}]}]}]}]}]}]}]}]}]}]}]}]}]}]}]}]}]}]}]}]}]}]}]}]}]}]}]}]}]}]}]}]', '\\\\\\\\\\\\\\\\"[{[{[{[{[{[{[{[{[{[{[{[{[{[{[{[{[{[{[{[{[{[{[{[{[{[{[{[{[{[{[{[{[{[{[{[{[{[{[{[{[{[{[{[{[{[{[{[{[{[{[{[{[{[{[{[{[{[{[{[{[{[{[{[{[{[{[{[{[{[{[{[{[{[{[{[{[{[{[{[{']:
            with self.subTest(text=text[:20]):
                manifest_data = json.dumps({"name": "x", "version": "1", "license": "MIT",
                                            "data": text}).encode()
                result = audit(self.make(manifest_data), limits=Limits(manifest_depth=1))
                self.assertEqual(result["status"], "pass")
                self.assertNotIn("manifest_depth_exceeded", self.codes(result))

    def test_raw_json_nested_2000_levels_is_refused_without_recursion_error(self):
        manifest_data = self.nested(2001)
        result = audit(self.make(manifest_data))
        self.assertEqual(result["status"], "fail")
        self.assertIn("manifest_depth_exceeded", self.codes(result))
        self.assertFalse(result["package_executed"])
        self.assertFalse(result["files_extracted"])

    def test_invalid_limit_values_are_rejected(self):
        for bad in (0, -1, 64.0, "64", None, True, False):
            with self.subTest(bad=bad):
                with self.assertRaises(ValueError):
                    Limits(manifest_depth=bad)

    def test_within_budget_nested_exports_are_still_resolved(self):
        manifest_data = b'{"name":"x","version":"1","license":"MIT","exports":{".":{"import":"./bin.js"}}}'
        result = audit(self.make(manifest_data))
        self.assertEqual(result["status"], "pass")
        self.assertNotIn("manifest_depth_exceeded", self.codes(result))

    def test_malformed_json_within_depth_is_still_invalid_archive(self):
        manifest_data = b'{"name":"x","version":"1","license":"MIT","data":{"bad":}}'
        result = audit(self.make(manifest_data))
        self.assertEqual(result["status"], "fail")
        self.assertIn("invalid_archive", self.codes(result))
        self.assertNotIn("manifest_depth_exceeded", self.codes(result))

    def test_duplicate_keys_within_depth_are_still_detected(self):
        manifest_data = b'{"name":"first","name":"second","version":"1","license":"MIT"}'
        result = audit(self.make(manifest_data))
        self.assertEqual(result["status"], "fail")
        self.assertIn("invalid_archive", self.codes(result))
        self.assertNotIn("manifest_depth_exceeded", self.codes(result))

    def test_cli_reports_manifest_depth_exceeded(self):
        manifest_data = self.nested(65)
        self.make(manifest_data)
        output = io.StringIO()
        with redirect_stdout(output):
            returncode = main([str(self.path), "--json"])
        self.assertEqual(returncode, 1)
        report = json.loads(output.getvalue())
        self.assertEqual(report["status"], "fail")
        self.assertIn("manifest_depth_exceeded", {f["code"] for f in report["findings"]})


if __name__ == "__main__":
    unittest.main()
