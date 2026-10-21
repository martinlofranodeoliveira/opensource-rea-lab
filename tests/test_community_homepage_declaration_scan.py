import ast
import copy
import pathlib
import unittest

try:
    from src.npm_tarball_audit.features.homepage_declaration_scan import run_feature
except ImportError:
    from npm_tarball_audit.features.homepage_declaration_scan import run_feature

_ERROR = "Invalid homepage scan payload or budget"


class HomepageDeclarationScanTest(unittest.TestCase):
    def test_absent_none(self):
        out = run_feature({"homepage": None})
        self.assertEqual(out, {"homepage": None, "declared": False})
        self.assertIsNone(out["homepage"])
        self.assertIs(out["declared"], False)
        self.assertEqual(set(out.keys()), {"homepage", "declared"})

    def test_present_basic(self):
        out = run_feature({"homepage": "https://example.com/project"})
        self.assertEqual(out, {"homepage": "https://example.com/project", "declared": True})
        self.assertIs(out["declared"], True)

    def test_contract_examples(self):
        self.assertEqual(
            run_feature({"homepage": "https://example.com/project"}),
            {"homepage": "https://example.com/project", "declared": True},
        )
        self.assertEqual(
            run_feature({"homepage": None}),
            {"homepage": None, "declared": False},
        )
        self.assertEqual(
            run_feature({"homepage": "https://example.com/docs", "max_length": 512}),
            {"homepage": "https://example.com/docs", "declared": True},
        )

    def test_preserves_spelling_case_whitespace(self):
        raw = "  HTTPS://Example.COM/Docs Page\t"
        out = run_feature({"homepage": raw})
        self.assertEqual(out["homepage"], raw)
        self.assertEqual(out["declared"], True)
        self.assertIsNot(out, {"homepage": raw, "declared": True})

    def test_no_trimming_or_repair(self):
        raw = "   "
        out = run_feature({"homepage": raw})
        self.assertEqual(out["homepage"], raw)
        self.assertTrue(out["declared"])

    def test_no_normalization(self):
        raw = "e\u0301"
        self.assertEqual(len(raw), 2)
        out = run_feature({"homepage": raw})
        self.assertEqual(out["homepage"], raw)
        self.assertEqual(len(out["homepage"]), 2)

    def test_codepoint_length(self):
        smile = "\U0001F600"
        self.assertEqual(len(smile), 1)
        out = run_feature({"homepage": smile})
        self.assertEqual(out["homepage"], smile)
        self.assertTrue(out["declared"])

    def test_str_subclass_allowed(self):
        class MyStr(str):
            pass
        val = MyStr("https://example.com/a")
        out = run_feature({"homepage": val})
        self.assertEqual(out["homepage"], "https://example.com/a")
        self.assertTrue(out["declared"])
        self.assertIsInstance(out["homepage"], str)

    def test_rejects_missing_extra_non_dict(self):
        with self.assertRaises(ValueError) as cm:
            run_feature({})
        self.assertEqual(str(cm.exception), _ERROR)
        with self.assertRaises(ValueError) as cm:
            run_feature({"max_length": 10})
        self.assertEqual(str(cm.exception), _ERROR)
        with self.assertRaises(ValueError) as cm:
            run_feature({"homepage": None, "extra": 1})
        self.assertEqual(str(cm.exception), _ERROR)
        with self.assertRaises(ValueError) as cm:
            run_feature({"homepage": "x", "max_length": 5, "other": 1})
        self.assertEqual(str(cm.exception), _ERROR)
        for bad in [None, [], "x", 123, 1.5, True]:
            with self.assertRaises(ValueError) as cm:
                run_feature(bad)
            self.assertEqual(str(cm.exception), _ERROR)

    def test_rejects_bad_budget(self):
        for bad_budget in [True, False, 0, -1, -512, 1.5, "512", None, [], {}]:
            with self.assertRaises(ValueError) as cm:
                run_feature({"homepage": None, "max_length": bad_budget})
            self.assertEqual(str(cm.exception), _ERROR)
            self.assertNotIn(str(bad_budget), str(cm.exception))

    def test_rejects_bad_homepage(self):
        for bad in [123, 1.5, True, False, [], {}, b"x"]:
            with self.assertRaises(ValueError) as cm:
                run_feature({"homepage": bad})
            self.assertEqual(str(cm.exception), _ERROR)
        with self.assertRaises(ValueError) as cm:
            run_feature({"homepage": ""})
        self.assertEqual(str(cm.exception), _ERROR)
        with self.assertRaises(ValueError) as cm:
            run_feature({"homepage": "abc", "max_length": 2})
        self.assertEqual(str(cm.exception), _ERROR)
        long_home = "x" * 513
        with self.assertRaises(ValueError) as cm:
            run_feature({"homepage": long_home})
        self.assertEqual(str(cm.exception), _ERROR)
        self.assertNotIn(long_home, str(cm.exception))

    def test_error_does_not_echo(self):
        secret = "https://secret.example/" + "y" * 600
        try:
            run_feature({"homepage": secret})
            self.fail("expected ValueError")
        except ValueError as exc:
            self.assertEqual(str(exc), _ERROR)
            self.assertNotIn(secret, str(exc))

    def test_custom_max_length_inclusive(self):
        ok = "12345"
        out = run_feature({"homepage": ok, "max_length": 5})
        self.assertEqual(out["homepage"], ok)
        self.assertTrue(out["declared"])
        with self.assertRaises(ValueError):
            run_feature({"homepage": "123456", "max_length": 5})
        with self.assertRaises(ValueError):
            run_feature({"homepage": "", "max_length": 5})
        single = run_feature({"homepage": "z", "max_length": 1})
        self.assertEqual(single["homepage"], "z")

    def test_never_mutates_and_fresh(self):
        payload = {"homepage": "https://example.com/x"}
        before = copy.deepcopy(payload)
        r1 = run_feature(payload)
        r2 = run_feature(payload)
        self.assertEqual(payload, before)
        self.assertIsNot(r1, r2)
        self.assertEqual(r1, r2)
        r1["homepage"] = "mutated"
        r1["declared"] = False
        r1["newkey"] = 1
        self.assertEqual(payload, before)
        r3 = run_feature(payload)
        self.assertEqual(r3, {"homepage": "https://example.com/x", "declared": True})
        payload2 = {"homepage": None}
        before2 = copy.deepcopy(payload2)
        s1 = run_feature(payload2)
        s2 = run_feature(payload2)
        self.assertEqual(payload2, before2)
        self.assertIsNot(s1, s2)
        self.assertEqual(s1, s2)

    def test_deterministic(self):
        payload = {"homepage": "https://example.com/d", "max_length": 100}
        self.assertEqual(run_feature(payload), run_feature(dict(payload)))

    def test_only_allowed_imports_and_plain_functions(self):
        candidates = [
            pathlib.Path(__file__).resolve().parent.parent / "src" / "npm_tarball_audit" / "features" / "homepage_declaration_scan.py",
            pathlib.Path(__file__).resolve().parent / "src" / "npm_tarball_audit" / "features" / "homepage_declaration_scan.py",
            pathlib.Path("src/npm_tarball_audit/features/homepage_declaration_scan.py"),
        ]
        src_path = None
        for cand in candidates:
            if cand.is_file():
                src_path = cand
                break
        self.assertIsNotNone(src_path, "module source not found")
        tree = ast.parse(src_path.read_text(encoding="utf-8"))
        allowed = {"math", "re", "json", "unicodedata"}
        for node in tree.body:
            if isinstance(node, ast.Import):
                for alias in node.names:
                    self.assertIn(alias.name.split(".")[0], allowed)
            elif isinstance(node, ast.ImportFrom):
                self.assertIsNotNone(node.module)
                self.assertIn(node.module.split(".")[0], allowed)
        for node in ast.walk(tree):
            self.assertNotIsInstance(node, ast.ClassDef)
            self.assertNotIsInstance(node, ast.AsyncFunctionDef)
            self.assertNotIsInstance(node, ast.Global)
            self.assertNotIsInstance(node, ast.Nonlocal)
            if isinstance(node, ast.FunctionDef):
                self.assertEqual(node.decorator_list, [])
                for d in node.args.defaults:
                    self.assertNotIsInstance(d, (ast.List, ast.Dict, ast.Set))
        texts = src_path.read_text(encoding="utf-8")
        self.assertIn("def run_feature", texts)


if __name__ == "__main__":
    unittest.main()
