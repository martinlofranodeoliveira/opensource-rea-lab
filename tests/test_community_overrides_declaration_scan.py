import copy
import unittest
try:
    from npm_tarball_audit.features.overrides_declaration_scan import run_feature
except ImportError:
    from src.npm_tarball_audit.features.overrides_declaration_scan import run_feature
EXPECTED_ERROR = "Invalid overrides scan payload or budget"
class TestOverridesDeclarationScan(unittest.TestCase):
    def test_absent_none(self):
        payload = {"overrides": None}
        before = copy.deepcopy(payload)
        out = run_feature(payload)
        self.assertEqual(out, {"declared": False, "entries": None})
        self.assertEqual(payload, before)
    def test_empty_dict(self):
        first = run_feature({"overrides": {}})
        second = run_feature({"overrides": {}})
        self.assertEqual(first, {"declared": True, "entries": []})
        self.assertIsInstance(first["entries"], list)
        self.assertIsNot(first, second)
        self.assertIsNot(first["entries"], second["entries"])
    def test_flat_sorted_verbatim(self):
        payload = {"overrides": {"b": "2.0.0", "A": "1.0.0", "  spaced  ": "x"}}
        out = run_feature(payload)
        self.assertTrue(out["declared"])
        keys = [e["key"] for e in out["entries"]]
        self.assertEqual(keys, sorted(keys))
        by_key = {e["key"]: e["value"] for e in out["entries"]}
        self.assertEqual(by_key["  spaced  "], "x")
        self.assertEqual(by_key["b"], "2.0.0")
    def test_nested_sorted(self):
        payload = {"overrides": {"foo@2": {"zebra": "2.0.0", "apple": "1.0.0"}, "aaa": "9.9.9"}}
        out = run_feature(payload)
        self.assertTrue(out["declared"])
        self.assertEqual([e["key"] for e in out["entries"]], ["aaa", "foo@2"])
        nested = out["entries"][1]["value"]
        self.assertEqual(list(nested.keys()), ["apple", "zebra"])
        self.assertEqual(nested["apple"], "1.0.0")
    def test_allowed_controls_preserved(self):
        out = run_feature({"overrides": {"a": "1.0\t0"}})
        self.assertEqual(out["entries"][0]["value"], "1.0\t0")
        out2 = run_feature({"overrides": {"a\nb": "v\rv"}})
        self.assertEqual(out2["entries"][0]["key"], "a\nb")
    def test_str_subclass_accepted(self):
        class S(str):
            pass
        payload = {"overrides": {S("k"): S("v")}}
        out = run_feature(payload)
        self.assertEqual(out["entries"], [{"key": "k", "value": "v"}])
        self.assertEqual(type(out["entries"][0]["key"]), str)
    def test_invalid_payloads(self):
        bad = [
            None,
            [],
            "x",
            0,
            1,
            True,
            {},
            {"max_entries": 32},
            {"overrides": None, "extra": 1},
            {"overrides": None, "max_entries": True},
            {"overrides": None, "max_length": False},
            {"overrides": None, "max_entries": "32"},
            {"overrides": None, "max_entries": 0},
            {"overrides": None, "max_entries": 65},
            {"overrides": None, "max_length": 0},
            {"overrides": None, "max_length": 1025},
            {"overrides": "x"},
            {"overrides": 0},
            {"overrides": 1},
            {"overrides": True},
            {"overrides": []},
            {"overrides": {"": "1.0.0"}},
            {"overrides": {"a": ""}},
            {"overrides": {"a": {}}},
            {"overrides": {"a": ["1.0.0"]}},
            {"overrides": {"a": {"b": ["1"]}}},
            {"overrides": {"a": {"b": {"c": "1"}}}},
            {"overrides": {"a": None}},
            {"overrides": {"a": 1}},
            {"overrides": {"\x01bad": "1.0.0"}},
            {"overrides": {"a": "bad\x00"}},
            {"overrides": {"\ud800": "1.0.0"}},
            {"overrides": {"a": "\udc00"}},
            {"overrides": {"a": "1.0.0"}, "max_entries": 64, "max_length": 256, "zzz": 1},
        ]
        for p in bad:
            with self.subTest(payload_repr=repr(p)[:80]):
                with self.assertRaises(ValueError) as cm:
                    run_feature(p)
                self.assertEqual(str(cm.exception), EXPECTED_ERROR)
    def test_budgets_enforced(self):
        with self.assertRaises(ValueError) as cm:
            run_feature({"overrides": {"a": "1", "b": "2"}, "max_entries": 1})
        self.assertEqual(str(cm.exception), EXPECTED_ERROR)
        with self.assertRaises(ValueError) as cm2:
            run_feature({"overrides": {"abc": "1"}, "max_length": 2})
        self.assertEqual(str(cm2.exception), EXPECTED_ERROR)
        with self.assertRaises(ValueError) as cm3:
            run_feature({"overrides": {"a": {"x": "1", "y": "2"}}, "max_entries": 1})
        self.assertEqual(str(cm3.exception), EXPECTED_ERROR)
        ok = run_feature({"overrides": {"a": "1", "b": "2"}, "max_entries": 2, "max_length": 256})
        self.assertEqual(len(ok["entries"]), 2)
    def test_pure_fresh_no_mutate(self):
        payload = {"overrides": {"b": "2", "a": {"z": "1", "m": "2"}}}
        snapshot = copy.deepcopy(payload)
        first = run_feature(payload)
        second = run_feature(payload)
        self.assertEqual(payload, snapshot)
        self.assertEqual(first, second)
        self.assertIsNot(first, second)
        self.assertIsNot(first["entries"], second["entries"])
        self.assertIsNot(first["entries"][0], second["entries"][0])
        self.assertIsNot(first["entries"][1], second["entries"][1])
        self.assertIsInstance(first["entries"][0]["value"], dict)
        self.assertIsNot(first["entries"][0]["value"], second["entries"][0]["value"])
        self.assertEqual(first["entries"][1]["value"], "2")
        self.assertEqual(second["entries"][1]["value"], "2")
        first["entries"].append({"key": "evil", "value": "x"})
        first["entries"][0]["key"] = "mut"
        first["entries"][0]["value"]["m"] = "mut"
        third = run_feature(payload)
        self.assertEqual(len(third["entries"]), 2)
        self.assertEqual(third, second)
        self.assertEqual(payload, snapshot)
    def test_examples_from_contract(self):
        self.assertEqual(run_feature({"overrides": None}), {"declared": False, "entries": None})
        self.assertEqual(run_feature({"overrides": {"lodash": "4.17.21"}}), {"declared": True, "entries": [{"key": "lodash", "value": "4.17.21"}]})
        self.assertEqual(run_feature({"overrides": {"aaa": "1.0.0", "foo@2": {"bar": "3.0.0"}}}), {"declared": True, "entries": [{"key": "aaa", "value": "1.0.0"}, {"key": "foo@2", "value": {"bar": "3.0.0"}}]})
if __name__ == "__main__":
    unittest.main()
