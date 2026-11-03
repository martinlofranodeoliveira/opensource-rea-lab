import unittest

try:
    from npm_tarball_audit.features.main_entry_declaration_scan import run_feature
except ImportError:
    from src.npm_tarball_audit.features.main_entry_declaration_scan import run_feature


class TestMainEntryDeclarationScan(unittest.TestCase):
    def test_absent_none(self):
        payload = {"main": None}
        out = run_feature(payload)
        self.assertEqual(list(out.keys()), ["present", "kind", "valid", "target", "reasons"])
        self.assertIs(out["present"], False)
        self.assertEqual(out["kind"], "absent")
        self.assertIs(type(out["kind"]), str)
        self.assertIs(out["valid"], True)
        self.assertIs(out["target"], None)
        self.assertEqual(out["reasons"], [])
        self.assertEqual(payload, {"main": None})

    def test_valid_index_js(self):
        out = run_feature({"main": "index.js"})
        self.assertEqual(list(out.keys()), ["present", "kind", "valid", "target", "reasons"])
        self.assertIs(out["present"], True)
        self.assertEqual(out["kind"], "declared")
        self.assertIs(out["valid"], True)
        self.assertEqual(out["target"], "index.js")
        self.assertEqual(out["reasons"], [])

    def test_valid_dot_slash(self):
        out = run_feature({"main": "./lib/index.js"})
        self.assertIs(out["present"], True)
        self.assertEqual(out["kind"], "declared")
        self.assertIs(out["valid"], True)
        self.assertEqual(out["target"], "./lib/index.js")
        self.assertEqual(out["reasons"], [])

    def test_dotdot_escape(self):
        out = run_feature({"main": "../escape.js"})
        self.assertIs(out["present"], True)
        self.assertEqual(out["kind"], "declared")
        self.assertIs(out["valid"], False)
        self.assertEqual(out["target"], "../escape.js")
        self.assertEqual(out["reasons"], ["value_syntax"])

    def test_absolute_path(self):
        out = run_feature({"main": "/abs/index.js"})
        self.assertIs(out["valid"], False)
        self.assertEqual(out["reasons"], ["value_syntax"])

    def test_syntax_variants(self):
        cases = [
            "a\\b.js",
            "a:b.js",
            "a/b/",
            "a//b.js",
            "a/./b.js",
            "a/../b.js",
            ".",
            "./",
            "./a/./b.js",
            "..",
            "../a.js",
            "/a.js",
            "a/..",
            "a/.",
        ]
        for v in cases:
            with self.subTest(value=v):
                out = run_feature({"main": v})
                self.assertEqual(out["kind"], "declared")
                self.assertIs(out["valid"], False)
                self.assertIn("value_syntax", out["reasons"])

    def test_control_and_del(self):
        out = run_feature({"main": "a\x01b.js"})
        self.assertEqual(out["reasons"], ["value_syntax"])
        out2 = run_feature({"main": "a\x7fb.js"})
        self.assertEqual(out2["reasons"], ["value_syntax"])

    def test_empty_string_both_reasons(self):
        out = run_feature({"main": ""})
        self.assertIs(out["valid"], False)
        self.assertEqual(out["reasons"], ["value_length", "value_syntax"])

    def test_over_length(self):
        ok = "a" * 256
        out = run_feature({"main": ok})
        self.assertIs(out["valid"], True)
        over = "a" * 257
        out2 = run_feature({"main": over})
        self.assertIs(out2["valid"], False)
        self.assertEqual(out2["reasons"], ["value_length"])

    def test_over_length_with_syntax_fixed_order(self):
        over = ("../" * 100)[:300]
        out = run_feature({"main": over, "max_length": 10})
        self.assertEqual(out["reasons"], ["value_length", "value_syntax"])

    def test_custom_budget(self):
        out = run_feature({"main": "12345", "max_length": 5})
        self.assertIs(out["valid"], True)
        out2 = run_feature({"main": "12345", "max_length": 4})
        self.assertEqual(out2["reasons"], ["value_length"])

    def test_non_dict_missing_extra_keys(self):
        for bad in [None, [], "x", 5, True]:
            with self.subTest(bad=bad):
                with self.assertRaises(ValueError) as cm:
                    run_feature(bad)
                self.assertEqual(str(cm.exception), "Invalid main payload or budget")
        with self.assertRaises(ValueError) as cm:
            run_feature({})
        self.assertEqual(str(cm.exception), "Invalid main payload or budget")
        with self.assertRaises(ValueError) as cm:
            run_feature({"main": "a.js", "extra": 1})
        self.assertEqual(str(cm.exception), "Invalid main payload or budget")

    def test_bad_budget(self):
        bads = [True, False, 0, 513, -1, 1.0, "5", None, [], {}]
        for b in bads:
            with self.subTest(budget=b):
                with self.assertRaises(ValueError) as cm:
                    run_feature({"main": "a.js", "max_length": b})
                self.assertEqual(str(cm.exception), "Invalid main payload or budget")

    def test_bad_main_type(self):
        for bad in [0, 1, True, 1.5, [], {}]:
            with self.subTest(bad=bad):
                with self.assertRaises(ValueError) as cm:
                    run_feature({"main": bad})
                self.assertEqual(str(cm.exception), "Invalid main declaration")

    def test_str_subclass_accepted_plain(self):
        class S(str):
            pass
        payload = {"main": S("index.js")}
        out = run_feature(payload)
        self.assertIs(out["valid"], True)
        self.assertEqual(out["target"], "index.js")
        self.assertIs(type(out["target"]), str)
        self.assertIs(type(out["kind"]), str)

    def test_inputs_never_mutated_and_fresh(self):
        payload = {"main": "index.js"}
        r1 = run_feature(payload)
        r2 = run_feature(payload)
        self.assertEqual(payload, {"main": "index.js"})
        self.assertIsNot(r1, r2)
        self.assertIsNot(r1["reasons"], r2["reasons"])
        r1["reasons"].append("value_syntax")
        self.assertEqual(r2["reasons"], [])
        self.assertEqual(list(r1.keys()), ["present", "kind", "valid", "target", "reasons"])
        self.assertIs(type(r1["target"]), str)
        for item in r1["reasons"]:
            self.assertIs(type(item), str)


if __name__ == "__main__":
    unittest.main()
