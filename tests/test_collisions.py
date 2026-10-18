import io
import json
import tarfile
import tempfile
import unittest
from pathlib import Path

from npm_tarball_audit import audit


class CollisionTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.path = Path(self.temp.name) / "fixture.tgz"

    def make(self, members):
        manifest = {"name": "useful-example", "version": "1.0.0", "license": "MIT"}
        with tarfile.open(self.path, "w:gz", format=tarfile.PAX_FORMAT) as tf:
            for name, content in [("package/package.json", json.dumps(manifest).encode()), ("package/LICENSE", b"MIT License\n"), *members]:
                entry = tarfile.TarInfo(name)
                if content is None:
                    entry.type = tarfile.DIRTYPE
                    entry.size = 0
                    tf.addfile(entry)
                else:
                    entry.size = len(content)
                    tf.addfile(entry, io.BytesIO(content))
        return self.path

    def codes(self, report):
        return {f["code"] for f in report["findings"]}

    def test_file_before_descendant_is_collision(self):
        result = audit(self.make([
            ("package/a", b"file"),
            ("package/a/b.js", b"descendant"),
        ]))
        self.assertIn("path_collision", self.codes(result))
        self.assertEqual(result["status"], "fail")

    def test_descendant_before_file_is_collision(self):
        result = audit(self.make([
            ("package/a/b.js", b"descendant"),
            ("package/a", b"file"),
        ]))
        self.assertIn("path_collision", self.codes(result))
        self.assertEqual(result["status"], "fail")

    def test_multi_level_ancestor_collision(self):
        result = audit(self.make([
            ("package/a", b"file"),
            ("package/a/b/c.js", b"descendant"),
        ]))
        self.assertIn("path_collision", self.codes(result))
        self.assertEqual(result["status"], "fail")

    def test_legitimate_directory_ancestry_is_not_collision(self):
        result = audit(self.make([
            ("package/a/", None),
            ("package/a/b.js", b"descendant"),
        ]))
        self.assertNotIn("path_collision", self.codes(result))
        self.assertEqual(result["status"], "pass")

    def test_normal_siblings_and_package_json_are_not_collision(self):
        result = audit(self.make([
            ("package/a.js", b"file"),
            ("package/b.js", b"file"),
            ("package/dir/c.js", b"file"),
        ]))
        self.assertNotIn("path_collision", self.codes(result))
        self.assertEqual(result["status"], "pass")


if __name__ == "__main__":
    unittest.main()
