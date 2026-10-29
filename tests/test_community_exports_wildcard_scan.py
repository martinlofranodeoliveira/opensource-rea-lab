import copy
import unittest

try:
    from src.npm_tarball_audit.features.exports_wildcard_scan import run_feature
except ImportError:
    from npm_tarball_audit.features.exports_wildcard_scan import run_feature

PAYLOAD_ERROR = "Invalid exports payload or budget"
DECL_ERROR = "Invalid exports declaration"
ORDER = ["declared", "total_keys", "total_targets", "wildcard_key_occurrences", "wildcard_target_occurrences", "wildcard_keys", "wildcard_targets"]

class ExportsWildcardScanTest(unittest.TestCase):
    def test_absent_none(self):
        payload = {"exports": None}
        snap = copy.deepcopy(payload)
        out = run_feature(payload)
        self.assertEqual(payload, snap)
        self.assertEqual(list(out.keys()), ORDER)
        self.assertIs(out["declared"], False)
        self.assertEqual(out["total_keys"], 0)
        self.assertEqual(out["total_targets"], 0)
        self.assertEqual(out["wildcard_key_occurrences"], 0)
        self.assertEqual(out["wildcard_target_occurrences"], 0)
        self.assertEqual(out["wildcard_keys"], [])
        self.assertEqual(out["wildcard_targets"], [])

    def test_exact_string_no_wildcard(self):
        out = run_feature({"exports": "./index.js"})
        self.assertEqual(out, {"declared": True, "total_keys": 0, "total_targets": 1, "wildcard_key_occurrences": 0, "wildcard_target_occurrences": 0, "wildcard_keys": [], "wildcard_targets": []})

    def test_exact_dict_no_wildcard(self):
        out = run_feature({"exports": {".": "./index.js"}})
        self.assertTrue(out["declared"])
        self.assertEqual(out["total_keys"], 1)
        self.assertEqual(out["total_targets"], 1)
        self.assertEqual(out["wildcard_key_occurrences"], 0)
        self.assertEqual(out["wildcard_target_occurrences"], 0)
        self.assertEqual(out["wildcard_keys"], [])
        self.assertEqual(out["wildcard_targets"], [])

    def test_contract_example_one(self):
        out = run_feature({"exports": {".": "./index.js", "./features/*": "./features/*.js"}})
        self.assertEqual(out["total_keys"], 2)
        self.assertEqual(out["total_targets"], 2)
        self.assertEqual(out["wildcard_key_occurrences"], 1)
        self.assertEqual(out["wildcard_keys"], ["./features/*"])
        self.assertEqual(out["wildcard_target_occurrences"], 1)
        self.assertEqual(out["wildcard_targets"], ["./features/*.js"])

    def test_contract_example_nested_none(self):
        payload = {"exports": {".": {"default": "./index.js", "import": "./esm.js", "require": "./cjs.js"}, "./locale/*": None}}
        snap = copy.deepcopy(payload)
        out = run_feature(payload)
        self.assertEqual(payload, snap)
        self.assertEqual(out["total_keys"], 5)
        self.assertEqual(out["total_targets"], 3)
        self.assertEqual(out["wildcard_key_occurrences"], 1)
        self.assertEqual(out["wildcard_keys"], ["./locale/*"])
        self.assertEqual(out["wildcard_target_occurrences"], 0)
        self.assertEqual(out["wildcard_targets"], [])

    def test_wildcard_sorted_unique_with_duplicates(self):
        out = run_feature({"exports": ["./z/*.js", "./a/*.js", "./z/*.js", "./plain.js"]})
        self.assertEqual(out["total_targets"], 4)
        self.assertEqual(out["wildcard_target_occurrences"], 3)
        self.assertEqual(out["wildcard_targets"], ["./a/*.js", "./z/*.js"])
        out2 = run_feature({"exports": {"a": {"./k/*": "./x/*.js"}, "b": {"./k/*": "./y.js"}}})
        self.assertEqual(out2["total_keys"], 4)
        self.assertEqual(out2["wildcard_key_occurrences"], 2)
        self.assertEqual(out2["wildcard_keys"], ["./k/*"])
        self.assertEqual(out2["wildcard_target_occurrences"], 1)
        self.assertEqual(out2["wildcard_targets"], ["./x/*.js"])

    def test_nested_within_budgets(self):
        payload = {"exports": {".": ["./a.js", {"inner": "./b/*.js"}]}, "max_depth": 4, "max_entries": 64}
        out = run_feature(payload)
        self.assertTrue(out["declared"])
        self.assertEqual(out["total_keys"], 2)
        self.assertEqual(out["total_targets"], 2)
        self.assertEqual(out["wildcard_targets"], ["./b/*.js"])

    def test_depth_exceeded(self):
        payload = {"exports": {"a": {"b": {"c": "./x.js"}}}, "max_depth": 2}
        with self.assertRaises(ValueError) as cm:
            run_feature(payload)
        self.assertEqual(str(cm.exception), DECL_ERROR)

    def test_over_budget_entries(self):
        payload = {"exports": {".": "./a.js", "./b": "./b.js"}, "max_entries": 1}
        snap = copy.deepcopy(payload)
        with self.assertRaises(ValueError) as cm:
            run_feature(payload)
        self.assertEqual(str(cm.exception), PAYLOAD_ERROR)
        self.assertEqual(payload, snap)
        self.assertNotIn("./a.js", str(cm.exception))

    def test_over_budget_length(self):
        with self.assertRaises(ValueError) as cm:
            run_feature({"exports": "", "max_length": 256})
        self.assertEqual(str(cm.exception), DECL_ERROR)
        with self.assertRaises(ValueError) as cm2:
            run_feature({"exports": "abc", "max_length": 2})
        self.assertEqual(str(cm2.exception), DECL_ERROR)
        with self.assertRaises(ValueError) as cm3:
            run_feature({"exports": {"": "./x.js"}})
        self.assertEqual(str(cm3.exception), DECL_ERROR)

    def test_disallowed_types(self):
        for bad in [123, 4.5, True, False, ("./x.js",), b"./x.js"]:
            with self.assertRaises(ValueError) as cm:
                run_feature({"exports": bad})
            self.assertEqual(str(cm.exception), DECL_ERROR)
        with self.assertRaises(ValueError) as cm:
            run_feature({"exports": [123]})
        self.assertEqual(str(cm.exception), DECL_ERROR)
        with self.assertRaises(ValueError) as cm:
            run_feature({"exports": {123: "./x.js"}})
        self.assertEqual(str(cm.exception), DECL_ERROR)
        with self.assertRaises(ValueError) as cm:
            run_feature({"exports": {"a": 123}})
        self.assertEqual(str(cm.exception), DECL_ERROR)

    def test_payload_errors(self):
        with self.assertRaises(ValueError) as cm:
            run_feature([1, 2])
        self.assertEqual(str(cm.exception), PAYLOAD_ERROR)
        with self.assertRaises(ValueError) as cm:
            run_feature({})
        self.assertEqual(str(cm.exception), PAYLOAD_ERROR)
        with self.assertRaises(ValueError) as cm:
            run_feature({"exports": None, "extra": 1})
        self.assertEqual(str(cm.exception), PAYLOAD_ERROR)
        for bad_budget in [True, False, 1.5, "64", [64], {"v": 1}, None, 0, 257]:
            with self.assertRaises(ValueError) as cm:
                run_feature({"exports": None, "max_entries": bad_budget})
            self.assertEqual(str(cm.exception), PAYLOAD_ERROR)
        for key, lo, hi in [("max_entries", 1, 256), ("max_length", 1, 1024), ("max_depth", 1, 16)]:
            with self.assertRaises(ValueError) as cm:
                run_feature({"exports": None, key: hi + 1})
            self.assertEqual(str(cm.exception), PAYLOAD_ERROR)
            with self.assertRaises(ValueError) as cm:
                run_feature({"exports": None, key: lo - 1})
            self.assertEqual(str(cm.exception), PAYLOAD_ERROR)

    def test_str_subclass_accepted_as_plain(self):
        class S(str):
            pass
        payload = {"exports": S("./a.js")}
        out = run_feature(payload)
        self.assertEqual(out["total_targets"], 1)
        self.assertIs(type(out["wildcard_targets"]), list)
        payload2 = {"exports": {S("./k/*"): S("./v/*.js")}}
        out2 = run_feature(payload2)
        self.assertEqual(out2["wildcard_keys"], ["./k/*"])
        self.assertEqual(out2["wildcard_targets"], ["./v/*.js"])
        self.assertIs(type(out2["wildcard_keys"][0]), str)
        self.assertIs(type(out2["wildcard_targets"][0]), str)

    def test_fresh_deterministic(self):
        payload = {"exports": {".": "./index.js", "./features/*": "./features/*.js"}}
        a = run_feature(payload)
        b = run_feature(payload)
        self.assertEqual(a, b)
        self.assertIsNot(a, b)
        self.assertIsNot(a["wildcard_keys"], b["wildcard_keys"])
        self.assertIsNot(a["wildcard_targets"], b["wildcard_targets"])
        a["wildcard_keys"].append("./evil")
        self.assertNotEqual(a, b)
        c = run_feature(payload)
        self.assertEqual(c, b)

    def test_input_preserved(self):
        payload = {"exports": {".": ["./a.js", None], "./w/*": {"x": "./y/*.js"}}}
        snap = copy.deepcopy(payload)
        run_feature(payload)
        self.assertEqual(payload, snap)

if __name__ == "__main__":
    unittest.main()
