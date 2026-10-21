import copy
import unittest

try:
    from src.npm_tarball_audit.features.sideeffects_declaration_scan import run_feature
except ImportError:
    from npm_tarball_audit.features.sideeffects_declaration_scan import run_feature

FIXED = "Invalid sideEffects scan payload or budget"

class TestSideEffectsDeclarationScan(unittest.TestCase):
    def assertInvalid(self, payload, marker=None):
        before = copy.deepcopy(payload)
        with self.assertRaises(ValueError) as ctx:
            run_feature(payload)
        self.assertEqual(str(ctx.exception), FIXED)
        if marker is not None:
            self.assertNotIn(marker, str(ctx.exception))
        self.assertEqual(payload, before)

    def test_none_absent(self):
        payload = {"sideEffects": None}
        before = copy.deepcopy(payload)
        result = run_feature(payload)
        self.assertEqual(result, {"flag": None, "entries": None, "declared": False})
        self.assertEqual(set(result.keys()), {"flag", "entries", "declared"})
        self.assertEqual(payload, before)
        second = run_feature(payload)
        self.assertEqual(second, result)
        self.assertIsNot(second, result)

    def test_exact_bools(self):
        for value in (True, False):
            payload = {"sideEffects": value}
            before = copy.deepcopy(payload)
            result = run_feature(payload)
            self.assertEqual(result, {"flag": value, "entries": None, "declared": True})
            self.assertIs(result["flag"], value)
            self.assertEqual(payload, before)
        self.assertInvalid({"sideEffects": 0}, marker="0")
        self.assertInvalid({"sideEffects": 1}, marker="1")
        self.assertInvalid({"sideEffects": 2})
        self.assertInvalid({"sideEffects": {}})
        self.assertInvalid({"sideEffects": {"a": 1}})
        self.assertInvalid({"sideEffects": ("x",)})

    def test_single_string_verbatim(self):
        value = "  ./Src/*.JS  "
        payload = {"sideEffects": value}
        result = run_feature(payload)
        self.assertEqual(result, {"flag": None, "entries": [value], "declared": True})
        self.assertEqual(result["entries"][0], value)
        self.assertEqual(payload, {"sideEffects": value})
        ok = "x" * 512
        result2 = run_feature({"sideEffects": ok})
        self.assertEqual(result2["entries"], [ok])
        self.assertInvalid({"sideEffects": ""})
        self.assertInvalid({"sideEffects": "x" * 513}, marker="xxx")
        self.assertInvalid({"sideEffects": "x", "max_length": 0})

    def test_str_subclass_accepted(self):
        class S(str):
            pass
        value = S(" ./a.js ")
        result = run_feature({"sideEffects": value})
        self.assertEqual(result["entries"], [" ./a.js "])
        self.assertEqual(result["flag"], None)
        self.assertTrue(result["declared"])

    def test_list_verbatim_and_fresh(self):
        items = ["./src/*.js", "./Styles.CSS", "  spaced  "]
        payload = {"sideEffects": list(items)}
        result = run_feature(payload)
        self.assertEqual(result, {"flag": None, "entries": items, "declared": True})
        self.assertIsNot(result["entries"], payload["sideEffects"])
        result["entries"].append("mut")
        self.assertEqual(payload["sideEffects"], items)
        second = run_feature(payload)
        self.assertEqual(second["entries"], items)
        self.assertIsNot(second["entries"], result["entries"])
        self.assertIsNot(second, result)
        empty = run_feature({"sideEffects": []})
        self.assertEqual(empty, {"flag": None, "entries": [], "declared": True})
        max_items = ["a" for _ in range(32)]
        ok = run_feature({"sideEffects": max_items})
        self.assertEqual(len(ok["entries"]), 32)
        too_many = ["a" for _ in range(33)]
        self.assertInvalid({"sideEffects": too_many})
        self.assertInvalid({"sideEffects": ["ok", 1]})
        self.assertInvalid({"sideEffects": ["ok", None]})
        self.assertInvalid({"sideEffects": ["ok", True]})
        self.assertInvalid({"sideEffects": [""]})
        self.assertInvalid({"sideEffects": ["x" * 513]})

    def test_custom_budgets(self):
        result = run_feature({"sideEffects": ["a", "b"], "max_entries": 2, "max_length": 2})
        self.assertEqual(result["entries"], ["a", "b"])
        self.assertInvalid({"sideEffects": ["a", "b", "c"], "max_entries": 2})
        self.assertInvalid({"sideEffects": "abc", "max_length": 2})
        ok = run_feature({"sideEffects": "ab", "max_length": 2})
        self.assertEqual(ok["entries"], ["ab"])

    def test_missing_extra_and_non_dict(self):
        self.assertInvalid({})
        self.assertInvalid({"max_entries": 32})
        self.assertInvalid({"sideEffects": None, "extra": 1}, marker="extra")
        self.assertInvalid({"sideEffects": None, "SideEffects": None})
        for bad in (None, [], "x", 123, True, False):
            self.assertInvalid(bad)

    def test_bad_budgets(self):
        self.assertInvalid({"sideEffects": None, "max_entries": True})
        self.assertInvalid({"sideEffects": None, "max_length": False})
        self.assertInvalid({"sideEffects": None, "max_entries": 0})
        self.assertInvalid({"sideEffects": None, "max_length": -1})
        self.assertInvalid({"sideEffects": None, "max_entries": "32"})
        self.assertInvalid({"sideEffects": None, "max_length": 5.0})
        self.assertInvalid({"sideEffects": None, "max_length": None})

    def test_no_echo_and_no_mutation(self):
        marker = "ECHO_MARKER_987654321"
        self.assertInvalid({"sideEffects": marker * 10, "max_length": 2}, marker=marker)
        self.assertInvalid({"sideEffects": [marker], "max_length": 1}, marker=marker)
        payload = {"sideEffects": ["b", "a"]}
        before = copy.deepcopy(payload)
        result = run_feature(payload)
        self.assertEqual(result["entries"], ["b", "a"])
        self.assertEqual(payload, before)

    def test_contract_examples(self):
        self.assertEqual(run_feature({"sideEffects": None}), {"flag": None, "entries": None, "declared": False})
        self.assertEqual(run_feature({"sideEffects": False}), {"flag": False, "entries": None, "declared": True})
        self.assertEqual(run_feature({"sideEffects": ["./src/*.js", "./styles.css"]}), {"flag": None, "entries": ["./src/*.js", "./styles.css"], "declared": True})

if __name__ == "__main__":
    unittest.main()
