import copy
import unittest

try:
    from npm_tarball_audit.features.resolutions_declaration_scan import run_feature
except ImportError:
    from src.npm_tarball_audit.features.resolutions_declaration_scan import run_feature

ERROR = "Invalid resolutions scan payload or budget"

class TestResolutionsDeclarationScan(unittest.TestCase):
    def assertInvalid(self, payload):
        with self.assertRaises(ValueError) as cm:
            run_feature(payload)
        self.assertEqual(str(cm.exception), ERROR)

    def test_absent_none_default(self):
        payload = {"resolutions": None}
        snapshot = copy.deepcopy(payload)
        result = run_feature(payload)
        self.assertEqual(result, {"declared": False, "entries": None})
        self.assertEqual(payload, snapshot)
        self.assertIsNone(result["entries"])
        second = run_feature({"resolutions": None})
        self.assertEqual(second, result)
        self.assertIsNot(second, result)

    def test_empty_dict(self):
        payload = {"resolutions": {}}
        result = run_feature(payload)
        self.assertEqual(result, {"declared": True, "entries": []})
        self.assertIsInstance(result["entries"], list)
        self.assertEqual(len(result["entries"]), 0)
        self.assertIsNot(result["entries"], payload["resolutions"])
        result["entries"].append({"selector": "x", "pin": "y"})
        second = run_feature(payload)
        self.assertEqual(second, {"declared": True, "entries": []})

    def test_present_sorted_verbatim(self):
        payload = {"resolutions": {"react": "18.2.0", "**/lodash": "4.17.21"}}
        snapshot = copy.deepcopy(payload)
        result = run_feature(payload)
        self.assertEqual(result, {"declared": True, "entries": [{"selector": "**/lodash", "pin": "4.17.21"}, {"selector": "react", "pin": "18.2.0"}]})
        self.assertEqual(payload, snapshot)
        payload2 = {"resolutions": {"lodash": "4.17.21"}}
        self.assertEqual(run_feature(payload2), {"declared": True, "entries": [{"selector": "lodash", "pin": "4.17.21"}]})
        payload3 = {"resolutions": {"b": "1", "A": "2"}}
        r3 = run_feature(payload3)
        self.assertEqual([e["selector"] for e in r3["entries"]], ["A", "b"])
        payload4 = {"resolutions": {"  React  ": " 1.0.0 "}}
        r4 = run_feature(payload4)
        self.assertEqual(r4["entries"][0]["selector"], "  React  ")
        self.assertEqual(r4["entries"][0]["pin"], " 1.0.0 ")
        payload5 = {"resolutions": {"a\tb": "x\ny", "c\rd": "z\t"}}
        r5 = run_feature(payload5)
        self.assertEqual(len(r5["entries"]), 2)

    def test_non_dict_missing_extra_bad_budgets(self):
        for bad in [None, [], "x", 0, 1, True, False, 3.14, 123]:
            self.assertInvalid(bad)
        self.assertInvalid({})
        self.assertInvalid({"max_entries": 64})
        self.assertInvalid({"resolutions": None, "extra": 1})
        self.assertInvalid({"resolutions": None, "RESOLUTIONS": None})
        self.assertInvalid({"resolutions": None, "max_entries": "64"})
        self.assertInvalid({"resolutions": None, "max_entries": 64.0})
        self.assertInvalid({"resolutions": None, "max_entries": True})
        self.assertInvalid({"resolutions": None, "max_entries": False})
        self.assertInvalid({"resolutions": None, "max_length": True})
        self.assertInvalid({"resolutions": None, "max_length": False})
        self.assertInvalid({"resolutions": None, "max_entries": 0})
        self.assertInvalid({"resolutions": None, "max_entries": 129})
        self.assertInvalid({"resolutions": None, "max_entries": -1})
        self.assertInvalid({"resolutions": None, "max_length": 0})
        self.assertInvalid({"resolutions": None, "max_length": 513})
        self.assertInvalid({"resolutions": None, "max_length": "256"})
        self.assertInvalid({"resolutions": None, "max_length": None})
        self.assertInvalid({"resolutions": None, "max_entries": None})

    def test_wrong_types_empty_controls_surrogates_overbudget(self):
        for bad_res in ["lodash", 0, 1, True, False, 3.14, [], ["a"], 123]:
            self.assertInvalid({"resolutions": bad_res})
        self.assertInvalid({"resolutions": {"": "1.0.0"}})
        self.assertInvalid({"resolutions": {"a": ""}})
        self.assertInvalid({"resolutions": {123: "1.0.0"}})
        self.assertInvalid({"resolutions": {None: "1.0.0"}})
        self.assertInvalid({"resolutions": {True: "1.0.0"}})
        self.assertInvalid({"resolutions": {"a": 123}})
        self.assertInvalid({"resolutions": {"a": None}})
        self.assertInvalid({"resolutions": {"a": True}})
        self.assertInvalid({"resolutions": {"a": ["1"]}})
        self.assertInvalid({"resolutions": {"a\x00b": "1.0.0"}})
        self.assertInvalid({"resolutions": {"a": "b\x01"}})
        self.assertInvalid({"resolutions": {"a\x1f": "1"}})
        self.assertInvalid({"resolutions": {"a\x07": "1"}})
        self.assertInvalid({"resolutions": {"\ud800": "1.0.0"}})
        self.assertInvalid({"resolutions": {"a": "\udc00"}})
        self.assertInvalid({"resolutions": {"a": "b", "c": "d", "e": "f"}, "max_entries": 2})
        self.assertInvalid({"resolutions": {"abc": "1"}, "max_length": 2})
        self.assertInvalid({"resolutions": {"a": "abcd"}, "max_length": 3})

    def test_custom_budgets_independent(self):
        r = run_feature({"resolutions": {"a": "1"}, "max_entries": 1, "max_length": 1})
        self.assertEqual(r["declared"], True)
        self.assertInvalid({"resolutions": {"a": "1", "b": "2"}, "max_entries": 1})
        r2 = run_feature({"resolutions": {"a": "1", "b": "2"}, "max_entries": 2})
        self.assertEqual(len(r2["entries"]), 2)
        long512 = "a" * 512
        r3 = run_feature({"resolutions": {long512: long512}, "max_length": 512})
        self.assertEqual(r3["entries"][0]["selector"], long512)
        self.assertInvalid({"resolutions": {long512: "a"}, "max_length": 511})
        self.assertInvalid({"resolutions": {"a": "1"}, "max_entries": True})
        self.assertInvalid({"resolutions": {"a": "1"}, "max_length": False})
        r4 = run_feature({"resolutions": {"a": "1"}, "max_entries": 128, "max_length": 512})
        self.assertEqual(len(r4["entries"]), 1)

    def test_fresh_no_mutation_no_shared(self):
        payload = {"resolutions": {"b": "2", "a": "1"}}
        snapshot = copy.deepcopy(payload)
        first = run_feature(payload)
        second = run_feature(payload)
        self.assertEqual(first, second)
        self.assertIsNot(first, second)
        self.assertIsNot(first["entries"], second["entries"])
        self.assertIsNot(first["entries"][0], second["entries"][0])
        self.assertEqual(payload, snapshot)
        first["entries"].append({"selector": "z", "pin": "9"})
        first["entries"][0]["selector"] = "mut"
        third = run_feature(payload)
        self.assertEqual(len(third["entries"]), 2)
        self.assertEqual(payload, snapshot)
        none_payload = {"resolutions": None}
        n1 = run_feature(none_payload)
        n2 = run_feature(none_payload)
        self.assertEqual(n1, n2)
        self.assertIsNot(n1, n2)

if __name__ == "__main__":
    unittest.main()
