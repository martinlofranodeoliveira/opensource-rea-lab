import unittest

try:
    from npm_tarball_audit.features.man_declaration_scan import run_feature
except ImportError:
    from src.npm_tarball_audit.features.man_declaration_scan import run_feature

FIXED = "Invalid man scan payload or budget"

class CommunityManDeclarationScanTest(unittest.TestCase):
    def assertInvalid(self, payload):
        with self.assertRaises(ValueError) as ctx:
            run_feature(payload)
        self.assertEqual(str(ctx.exception), FIXED)

    def test_absent_none(self):
        payload = {"man": None}
        out = run_feature(payload)
        self.assertEqual(out, {"entries": None, "declared": False})
        self.assertIsNone(out["entries"])
        self.assertFalse(out["declared"])
        self.assertEqual(payload, {"man": None})

    def test_string_target(self):
        out = run_feature({"man": "man/foo.1"})
        self.assertEqual(out, {"entries": ["man/foo.1"], "declared": True})

    def test_string_preserves_verbatim(self):
        value = "  Man/Foo.1  "
        out = run_feature({"man": value})
        self.assertEqual(out["entries"], [value])
        self.assertTrue(out["declared"])

    def test_array_sorted(self):
        out = run_feature({"man": ["man/b.1", "man/a.1"]})
        self.assertEqual(out, {"entries": ["man/a.1", "man/b.1"], "declared": True})

    def test_empty_array(self):
        out = run_feature({"man": []})
        self.assertEqual(out, {"entries": [], "declared": True})

    def test_duplicate_raises(self):
        self.assertInvalid({"man": ["a.1", "a.1"]})

    def test_non_string_element_raises(self):
        self.assertInvalid({"man": ["a.1", 0]})
        self.assertInvalid({"man": ["a.1", 1]})
        self.assertInvalid({"man": ["a.1", True]})
        self.assertInvalid({"man": ["a.1", None]})
        self.assertInvalid({"man": ["a.1", {}]})
        self.assertInvalid({"man": [""]})

    def test_out_of_budget_lengths_raise(self):
        self.assertInvalid({"man": ""})
        self.assertInvalid({"man": "abc", "max_length": 2})
        self.assertInvalid({"man": ["abc"], "max_length": 2})
        self.assertInvalid({"man": ["a" * 513]})

    def test_out_of_budget_counts_raise(self):
        self.assertInvalid({"man": ["a", "b"], "max_entries": 1})
        self.assertInvalid({"man": ["x"] * 33})

    def test_man_wrong_types_raise(self):
        self.assertInvalid({"man": 0})
        self.assertInvalid({"man": 1})
        self.assertInvalid({"man": 42})
        self.assertInvalid({"man": True})
        self.assertInvalid({"man": False})
        self.assertInvalid({"man": {}})
        self.assertInvalid({"man": {"a": "b"}})
        self.assertInvalid({"man": ("a.1",)})

    def test_non_dict_missing_extra_raise(self):
        self.assertInvalid(None)
        self.assertInvalid([])
        self.assertInvalid("man/foo.1")
        self.assertInvalid(0)
        self.assertInvalid({})
        self.assertInvalid({"max_entries": 32})
        self.assertInvalid({"man": None, "extra": 1})
        self.assertInvalid({"man": None, "man2": None})

    def test_bad_budgets_raise(self):
        self.assertInvalid({"man": None, "max_entries": True})
        self.assertInvalid({"man": None, "max_length": False})
        self.assertInvalid({"man": None, "max_entries": 0})
        self.assertInvalid({"man": None, "max_length": -1})
        self.assertInvalid({"man": None, "max_entries": "32"})
        self.assertInvalid({"man": None, "max_length": 1.5})
        self.assertInvalid({"man": None, "max_entries": None})

    def test_error_does_not_echo(self):
        secret = "super-secret-target-xyz"
        with self.assertRaises(ValueError) as ctx:
            run_feature({"man": [secret, secret]})
        self.assertEqual(str(ctx.exception), FIXED)
        self.assertNotIn(secret, str(ctx.exception))

    def test_fresh_containers(self):
        payload = {"man": ["man/b.1", "man/a.1"]}
        out1 = run_feature(payload)
        out2 = run_feature(payload)
        self.assertIsNot(out1, out2)
        self.assertIsNot(out1["entries"], out2["entries"])
        self.assertEqual(out1, out2)
        self.assertIsNot(out1["entries"], payload["man"])
        out1["entries"].append("mutated")
        self.assertEqual(out2["entries"], ["man/a.1", "man/b.1"])
        out3 = run_feature(payload)
        self.assertEqual(out3["entries"], ["man/a.1", "man/b.1"])

    def test_input_not_mutated(self):
        payload = {"man": ["man/b.1", "man/a.1"]}
        snapshot = {"man": ["man/b.1", "man/a.1"]}
        run_feature(payload)
        self.assertEqual(payload, snapshot)
        payload2 = {"man": "man/foo.1"}
        run_feature(payload2)
        self.assertEqual(payload2, {"man": "man/foo.1"})

    def test_str_subclass_accepted(self):
        class S(str):
            pass
        out = run_feature({"man": S("man/a.1")})
        self.assertEqual(out["entries"], ["man/a.1"])
        self.assertTrue(out["declared"])

    def test_custom_budgets_ok(self):
        out = run_feature({"man": ["a", "b"], "max_entries": 2, "max_length": 1})
        self.assertEqual(out["entries"], ["a", "b"])

if __name__ == "__main__":
    unittest.main()
