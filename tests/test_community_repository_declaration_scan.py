import unittest
try:
    from npm_tarball_audit.features.repository_declaration_scan import run_feature
except ImportError:
    from src.npm_tarball_audit.features.repository_declaration_scan import run_feature
FIXED = "Invalid repository scan payload or budget"
class RepositoryDeclarationScanTest(unittest.TestCase):
    def assertInvalid(self, payload):
        with self.assertRaises(ValueError) as ctx:
            run_feature(payload)
        self.assertEqual(str(ctx.exception), FIXED)
    def test_none(self):
        payload = {"repository": None}
        out = run_feature(payload)
        self.assertEqual(out, {"repository": None, "count": 0})
        self.assertEqual(payload, {"repository": None})
        self.assertIsNot(out, payload)
        again = run_feature({"repository": None})
        self.assertEqual(out, again)
        self.assertIsNot(out, again)
    def test_string_verbatim(self):
        payload = {"repository": "github:user/repo"}
        out = run_feature(payload)
        self.assertEqual(out, {"repository": {"type": None, "url": "github:user/repo", "directory": None}, "count": 1})
        self.assertEqual(set(out.keys()), {"repository", "count"})
        self.assertEqual(set(out["repository"].keys()), {"type", "url", "directory"})
        self.assertEqual(payload, {"repository": "github:user/repo"})
    def test_dict_minimal(self):
        payload = {"repository": {"type": "git", "url": "https://github.com/user/repo.git"}}
        out = run_feature(payload)
        self.assertEqual(out["count"], 1)
        self.assertEqual(out["repository"], {"type": "git", "url": "https://github.com/user/repo.git", "directory": None})
        self.assertEqual(payload, {"repository": {"type": "git", "url": "https://github.com/user/repo.git"}})
    def test_dict_full_preserves_case(self):
        payload = {"repository": {"type": "Git", "url": "HTTPS://Example.COM/Repo.Git", "directory": "Packages/Sub Dir"}}
        out = run_feature(payload)
        self.assertEqual(out["repository"]["type"], "Git")
        self.assertEqual(out["repository"]["url"], "HTTPS://Example.COM/Repo.Git")
        self.assertEqual(out["repository"]["directory"], "Packages/Sub Dir")
        self.assertEqual(out["count"], 1)
    def test_str_subclass(self):
        class S(str):
            pass
        payload = {"repository": S("github:user/repo")}
        out = run_feature(payload)
        self.assertEqual(out["count"], 1)
        self.assertEqual(out["repository"]["url"], "github:user/repo")
    def test_missing_url(self):
        self.assertInvalid({"repository": {"type": "git"}})
        self.assertInvalid({"repository": {}})
    def test_extra_dict_key(self):
        self.assertInvalid({"repository": {"url": "a", "bogus": "b"}})
        self.assertInvalid({"repository": {"type": "git", "url": "a", "directory": "d", "extra": "e"}})
    def test_empty_string(self):
        self.assertInvalid({"repository": ""})
        self.assertInvalid({"repository": {"url": ""}})
        self.assertInvalid({"repository": {"url": "a", "type": ""}})
        self.assertInvalid({"repository": {"url": "a", "directory": ""}})
    def test_over_length_default(self):
        self.assertInvalid({"repository": "x" * 513})
        self.assertInvalid({"repository": {"url": "x" * 513}})
        ok = run_feature({"repository": "x" * 512})
        self.assertEqual(ok["count"], 1)
    def test_custom_budget(self):
        out = run_feature({"repository": "ab", "max_length": 2})
        self.assertEqual(out["count"], 1)
        self.assertInvalid({"repository": "abc", "max_length": 2})
        self.assertInvalid({"repository": "a", "max_length": 0})
        self.assertInvalid({"repository": "a", "max_length": -1})
    def test_wrong_payload_key(self):
        self.assertInvalid({"repo": None})
        self.assertInvalid({"repository": None, "extra": 1})
        self.assertInvalid({})
        self.assertInvalid({"repository": None, "max_length": 512, "extra": 1})
    def test_non_int_budget(self):
        self.assertInvalid({"repository": "a", "max_length": "2"})
        self.assertInvalid({"repository": "a", "max_length": 2.0})
        self.assertInvalid({"repository": "a", "max_length": None})
    def test_bool_budget_rejected(self):
        self.assertInvalid({"repository": "a", "max_length": True})
        self.assertInvalid({"repository": "a", "max_length": False})
    def test_no_echo(self):
        marker = "UNIQUE_MARKER_XYZ_123"
        with self.assertRaises(ValueError) as ctx:
            run_feature({"repository": {"url": "a", "type": marker, "bogus": "z"}})
        self.assertEqual(str(ctx.exception), FIXED)
        self.assertNotIn(marker, str(ctx.exception))
    def test_no_mutation_and_fresh(self):
        inner = {"type": "git", "url": "https://example.com/r.git", "directory": "sub"}
        payload = {"repository": inner}
        first = run_feature(payload)
        second = run_feature(payload)
        self.assertEqual(inner, {"type": "git", "url": "https://example.com/r.git", "directory": "sub"})
        self.assertEqual(payload["repository"], {"type": "git", "url": "https://example.com/r.git", "directory": "sub"})
        self.assertEqual(first, second)
        self.assertIsNot(first, second)
        self.assertIsNot(first["repository"], second["repository"])
        self.assertIsNot(first["repository"], inner)
    def test_bad_repository_types(self):
        self.assertInvalid({"repository": 123})
        self.assertInvalid({"repository": ["a"]})
        self.assertInvalid({"repository": True})
        self.assertInvalid("string")
        self.assertInvalid(None)
        self.assertInvalid([])
    def test_none_optionals_rejected(self):
        self.assertInvalid({"repository": {"url": "a", "type": None}})
        self.assertInvalid({"repository": {"url": "a", "directory": None}})
        self.assertInvalid({"repository": {"url": None}})
    def test_deterministic(self):
        payload = {"repository": {"type": "git", "url": "https://github.com/user/repo.git"}}
        first = run_feature(payload)
        second = run_feature(payload)
        self.assertEqual(first, second)
if __name__ == "__main__":
    unittest.main()
