import unittest

try:
    from src.npm_tarball_audit.features.files_allowlist_scan import run_feature
except ImportError:
    from npm_tarball_audit.features.files_allowlist_scan import run_feature

EXPECTED_ERROR = "Invalid files scan payload or budget"


class FilesAllowlistScanTest(unittest.TestCase):
    def assertInvalid(self, payload):
        with self.assertRaises(ValueError) as ctx:
            run_feature(payload)
        self.assertEqual(str(ctx.exception), EXPECTED_ERROR)

    def test_valid_list_sorted_fresh_no_mutation(self):
        payload = {"files": ["dist/", "README.md"]}
        snapshot = list(payload["files"])
        result = run_feature(payload)
        self.assertEqual(result, {"files": ["README.md", "dist/"], "count": 2})
        self.assertEqual(set(result.keys()), {"files", "count"})
        self.assertEqual(payload["files"], snapshot)
        self.assertIsNot(result["files"], payload["files"])

    def test_contract_examples(self):
        self.assertEqual(run_feature({"files": ["dist/", "README.md"]}), {"files": ["README.md", "dist/"], "count": 2})
        self.assertEqual(run_feature({"files": None}), {"files": [], "count": 0})
        self.assertEqual(run_feature({"files": ["lib/index.js"], "max_entries": 128, "max_length": 1024}), {"files": ["lib/index.js"], "count": 1})

    def test_none_returns_empty_fresh(self):
        r1 = run_feature({"files": None})
        r2 = run_feature({"files": None})
        self.assertEqual(r1, {"files": [], "count": 0})
        self.assertEqual(r2, {"files": [], "count": 0})
        self.assertIsNot(r1, r2)
        self.assertIsNot(r1["files"], r2["files"])

    def test_unsorted_duplicates_verbatim_codepoint(self):
        payload = {"files": ["b", "a", "b", "A", "*.js", "Lib/", "lib/"]}
        result = run_feature(payload)
        self.assertEqual(result["files"], ["*.js", "A", "Lib/", "a", "b", "b", "lib/"])
        self.assertEqual(result["files"], sorted(payload["files"]))
        self.assertEqual(result["count"], 7)
        self.assertEqual(result["count"], len(payload["files"]))

    def test_case_pattern_spacing_preserved_no_glob(self):
        result = run_feature({"files": ["lib/", "Lib/", "*.js"]})
        self.assertEqual(result["files"], ["*.js", "Lib/", "lib/"])
        result2 = run_feature({"files": ["  spaced  ", "*.min.js"]})
        self.assertIn("  spaced  ", result2["files"])
        self.assertIn("*.min.js", result2["files"])
        self.assertEqual(result2["count"], 2)

    def test_str_subclass_accepted_without_coercion(self):
        class MyStr(str):
            pass
        payload = {"files": [MyStr("b"), MyStr("A")]}
        result = run_feature(payload)
        self.assertEqual(list(result["files"]), ["A", "b"])
        self.assertEqual(result["count"], 2)
        for value in result["files"]:
            self.assertTrue(isinstance(value, str))

    def test_invalid_shapes(self):
        self.assertInvalid(None)
        self.assertInvalid([])
        self.assertInvalid("x")
        self.assertInvalid(123)
        self.assertInvalid({})
        self.assertInvalid({"max_entries": 128})
        self.assertInvalid({"files": [], "extra": 1})
        self.assertInvalid({"files": "abc"})
        self.assertInvalid({"files": 123})
        self.assertInvalid({"files": {}})
        self.assertInvalid({"files": ("a",)})
        self.assertInvalid({"files": [123]})
        self.assertInvalid({"files": [None]})
        self.assertInvalid({"files": [True]})
        self.assertInvalid({"files": [""]})
        self.assertInvalid({"files": ["a", 2]})

    def test_invalid_budgets(self):
        self.assertInvalid({"files": [], "max_entries": True})
        self.assertInvalid({"files": [], "max_length": False})
        self.assertInvalid({"files": [], "max_entries": 0})
        self.assertInvalid({"files": [], "max_length": 0})
        self.assertInvalid({"files": [], "max_entries": -1})
        self.assertInvalid({"files": [], "max_length": -5})
        self.assertInvalid({"files": [], "max_entries": "128"})
        self.assertInvalid({"files": [], "max_length": 1.5})
        self.assertInvalid({"files": [], "max_entries": None})
        self.assertInvalid({"files": [], "max_length": []})
        self.assertInvalid({"files": [], "max_entries": 128.0})

    def test_over_length_and_over_entries(self):
        self.assertInvalid({"files": ["abcdef"], "max_length": 5})
        self.assertInvalid({"files": ["a", "b", "c"], "max_entries": 2})
        many = ["f" + str(i) for i in range(129)]
        self.assertInvalid({"files": many})
        self.assertInvalid({"files": ["x" * 1025]})

    def test_custom_budgets_boundary(self):
        result = run_feature({"files": ["abcde"], "max_length": 5, "max_entries": 1})
        self.assertEqual(result, {"files": ["abcde"], "count": 1})

    def test_error_does_not_echo_input(self):
        marker = "UNIQUE_MARKER_QZXW_987"
        with self.assertRaises(ValueError) as ctx:
            run_feature({"files": [marker], "max_entries": 0})
        self.assertEqual(str(ctx.exception), EXPECTED_ERROR)
        self.assertNotIn(marker, str(ctx.exception))

    def test_repeated_calls_equal_fresh_no_shared_refs(self):
        payload = {"files": ["z", "a", "m"]}
        r1 = run_feature(payload)
        r2 = run_feature(payload)
        self.assertEqual(r1, r2)
        self.assertIsNot(r1, r2)
        self.assertIsNot(r1["files"], r2["files"])
        r1["files"].append("mut")
        self.assertNotEqual(r1, r2)
        r3 = run_feature(payload)
        self.assertEqual(r3, r2)

    def test_input_never_mutated(self):
        inner = ["c", "b", "a"]
        payload = {"files": inner}
        before = list(inner)
        run_feature(payload)
        self.assertEqual(inner, before)
        self.assertEqual(payload, {"files": before})


if __name__ == "__main__":
    unittest.main()
