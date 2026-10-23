import copy
import unittest

try:
    from src.npm_tarball_audit.features.typesversions_declaration_scan import run_feature
except ImportError:
    from npm_tarball_audit.features.typesversions_declaration_scan import run_feature

FIXED = "Invalid typesVersions scan payload or budget"

class CommunityTypesVersionsDeclarationScanTest(unittest.TestCase):
    def test_absent_none(self):
        payload = {"typesVersions": None}
        before = copy.deepcopy(payload)
        out = run_feature(payload)
        self.assertEqual(out, {"declared": False, "entries": None})
        self.assertEqual(set(out.keys()), {"declared", "entries"})
        self.assertEqual(payload, before)
        out2 = run_feature({"typesVersions": None})
        self.assertEqual(out, out2)
        self.assertIsNot(out, out2)

    def test_empty_dict(self):
        payload = {"typesVersions": {}}
        out = run_feature(payload)
        self.assertEqual(out, {"declared": True, "entries": []})
        self.assertIsInstance(out["entries"], list)
        self.assertEqual(set(out.keys()), {"declared", "entries"})
        out["entries"].append({"selector": "x", "mappings": []})
        out2 = run_feature(payload)
        self.assertEqual(out2["entries"], [])
        self.assertIsNot(out["entries"], out2["entries"])
        self.assertEqual(payload, {"typesVersions": {}})

    def test_nested_sorted_verbatim(self):
        payload = {"typesVersions": {">=4.0": {"*": ["types-4/*"]}, ">=3.0": {"*": ["types-3/*", "types/*"]}}}
        before = copy.deepcopy(payload)
        out = run_feature(payload)
        self.assertTrue(out["declared"])
        self.assertEqual(len(out["entries"]), 2)
        self.assertEqual(out["entries"][0]["selector"], ">=3.0")
        self.assertEqual(out["entries"][1]["selector"], ">=4.0")
        self.assertEqual(out["entries"][0]["mappings"][0]["pattern"], "*")
        self.assertEqual(out["entries"][0]["mappings"][0]["targets"], ["types-3/*", "types/*"])
        self.assertEqual(payload, before)
        payload2 = {"typesVersions": {"b": {"z": ["t2"], "a": ["t1"]}, "A": {"m": ["x"]}}}
        out2 = run_feature(payload2)
        sels = [e["selector"] for e in out2["entries"]]
        self.assertEqual(sels, ["A", "b"])
        bentry = [e for e in out2["entries"] if e["selector"] == "b"][0]
        pats = [m["pattern"] for m in bentry["mappings"]]
        self.assertEqual(pats, ["a", "z"])
        keep = {"typesVersions": {"  k  ": {"  p  ": ["  v  "]}}}
        out3 = run_feature(keep)
        self.assertEqual(out3["entries"][0]["selector"], "  k  ")
        self.assertEqual(out3["entries"][0]["mappings"][0]["pattern"], "  p  ")
        self.assertEqual(out3["entries"][0]["mappings"][0]["targets"], ["  v  "])
        self.assertEqual(keep, {"typesVersions": {"  k  ": {"  p  ": ["  v  "]}}})

    def test_subclass_strings_accepted_as_plain(self):
        class S(str):
            pass
        payload = {"typesVersions": {S("s"): {S("*"): [S("a")]}}}
        out = run_feature(payload)
        self.assertEqual(out["entries"][0]["selector"], "s")
        self.assertEqual(type(out["entries"][0]["selector"]), str)
        self.assertEqual(out["entries"][0]["mappings"][0]["targets"], ["a"])
        self.assertEqual(type(out["entries"][0]["mappings"][0]["targets"][0]), str)

    def test_malformed_raises_fixed(self):
        bad_values = [
            {"typesVersions": {"": {"*": ["a"]}}},
            {"typesVersions": {"s": {}}},
            {"typesVersions": {"s": {"*": []}}},
            {"typesVersions": {"s": {"": ["a"]}}},
            {"typesVersions": {"s": {"*": [""]}}},
            {"typesVersions": {"s": {"*": "a"}}},
            {"typesVersions": {"s": ["a"]}},
            {"typesVersions": {"s": {"*": [123]}}},
            {"typesVersions": {"s": {"*": [None]}}},
            {"typesVersions": {"s": {"*": [True]}}},
            {"typesVersions": {"bad\x00key": {"*": ["a"]}}},
            {"typesVersions": {"s": {"*": ["a\x1f"]}}},
            {"typesVersions": {"s": {"*": ["\ud800"]}}},
            {"typesVersions": {"s": {"*": ["a\x07"]}}},
            {"typesVersions": "str"},
            {"typesVersions": 0},
            {"typesVersions": 1},
            {"typesVersions": True},
            {"typesVersions": False},
            {"typesVersions": 3.14},
            {"typesVersions": ["x"]},
        ]
        for p in bad_values:
            with self.assertRaises(ValueError) as cm:
                run_feature(p)
            self.assertEqual(str(cm.exception), FIXED)
        with self.assertRaises(ValueError) as cm:
            run_feature({"typesVersions": {"s": {"*": ["a", "b"]}}, "max_entries": 1})
        self.assertEqual(str(cm.exception), FIXED)
        with self.assertRaises(ValueError) as cm:
            run_feature({"typesVersions": {"toolong": {"*": ["a"]}}, "max_length": 2})
        self.assertEqual(str(cm.exception), FIXED)
        with self.assertRaises(ValueError) as cm:
            run_feature({"typesVersions": {"s": {"*": ["toolong"]}}, "max_length": 2})
        self.assertEqual(str(cm.exception), FIXED)

    def test_payload_budget_errors(self):
        bads = [
            None,
            [],
            "x",
            123,
            {},
            {"max_entries": 32},
            {"typesVersions": None, "extra": 1},
            {"typesVersions": None, "max_entries": True},
            {"typesVersions": None, "max_entries": False},
            {"typesVersions": None, "max_entries": "32"},
            {"typesVersions": None, "max_entries": 3.0},
            {"typesVersions": None, "max_entries": 0},
            {"typesVersions": None, "max_entries": 65},
            {"typesVersions": None, "max_length": True},
            {"typesVersions": None, "max_length": False},
            {"typesVersions": None, "max_length": 0},
            {"typesVersions": None, "max_length": 513},
            {"typesVersions": None, "max_length": "256"},
            {"typesVersions": None, "max_length": 2.5},
        ]
        for p in bads:
            with self.assertRaises(ValueError) as cm:
                run_feature(p)
            self.assertEqual(str(cm.exception), FIXED)

    def test_budgets_boundaries_ok(self):
        ok = {"typesVersions": {"s": {"*": ["a"]}}, "max_entries": 1, "max_length": 1}
        out = run_feature(ok)
        self.assertTrue(out["declared"])
        self.assertEqual(out["entries"][0]["selector"], "s")
        full = {"typesVersions": None, "max_entries": 64, "max_length": 512}
        out2 = run_feature(full)
        self.assertEqual(out2, {"declared": False, "entries": None})

    def test_deterministic_no_mutation_no_share(self):
        payload = {"typesVersions": {">=3.0": {"*": ["types-3/*", "types/*"]}}}
        before = copy.deepcopy(payload)
        a = run_feature(payload)
        b = run_feature(payload)
        self.assertEqual(a, b)
        self.assertIsNot(a, b)
        self.assertIsNot(a["entries"], b["entries"])
        self.assertIsNot(a["entries"][0], b["entries"][0])
        self.assertIsNot(a["entries"][0]["mappings"], b["entries"][0]["mappings"])
        self.assertIsNot(a["entries"][0]["mappings"][0]["targets"], b["entries"][0]["mappings"][0]["targets"])
        a["entries"][0]["mappings"][0]["targets"].append("evil")
        self.assertEqual(payload, before)
        c = run_feature(payload)
        self.assertEqual(len(c["entries"][0]["mappings"][0]["targets"]), 2)
        self.assertEqual(set(a.keys()), {"declared", "entries"})

if __name__ == "__main__":
    unittest.main()
