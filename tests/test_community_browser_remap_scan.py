import copy
import unittest
try:
    from src.npm_tarball_audit.features.browser_remap_scan import run_feature
except ImportError:
    from npm_tarball_audit.features.browser_remap_scan import run_feature

class BrowserRemapScanTest(unittest.TestCase):
    def test_absent(self):
        out = run_feature({"browser": None})
        self.assertEqual(out, {"kind": "absent", "replacement": None, "ignored": [], "remapped": [], "entry_count": 0})
        self.assertEqual(set(out.keys()), {"kind", "replacement", "ignored", "remapped", "entry_count"})
        self.assertIsNone(out["replacement"])
        self.assertIsInstance(out["ignored"], list)
        self.assertIsInstance(out["remapped"], list)
    def test_replacement(self):
        out = run_feature({"browser": "./browser.js"})
        self.assertEqual(out["kind"], "replacement")
        self.assertEqual(out["replacement"], "./browser.js")
        self.assertEqual(out["ignored"], [])
        self.assertEqual(out["remapped"], [])
        self.assertEqual(out["entry_count"], 1)
    def test_remap_sorted(self):
        payload = {"browser": {"./server.js": False, "fs": "./shim.js"}}
        out = run_feature(payload)
        self.assertEqual(out["kind"], "remap")
        self.assertIsNone(out["replacement"])
        self.assertEqual(out["ignored"], ["./server.js"])
        self.assertEqual(out["remapped"], [{"from": "fs", "to": "./shim.js"}])
        self.assertEqual(out["entry_count"], 2)
    def test_remap_sorting_and_empty(self):
        out = run_feature({"browser": {}})
        self.assertEqual(out["kind"], "remap")
        self.assertEqual(out["ignored"], [])
        self.assertEqual(out["remapped"], [])
        self.assertEqual(out["entry_count"], 0)
        out2 = run_feature({"browser": {"b": "y", "A": "z", "a": False}})
        self.assertEqual(out2["ignored"], ["a"])
        self.assertEqual([d["from"] for d in out2["remapped"]], ["A", "b"])
        self.assertEqual(out2["entry_count"], 3)
    def test_errors_fixed_message(self):
        bad = [None, [], "x", {}, {"browser": None, "extra": 1}, {"browser": True}, {"browser": 1}, {"browser": {"a": True}}, {"browser": {"a": None}}, {"browser": {"a": 0}}, {"browser": {1: "x"}}, {"max_entries": 10}, {"browser": None, "max_entries": True}, {"browser": None, "max_entries": 0}, {"browser": None, "max_length": -1}, {"browser": None, "max_entries": "2"}]
        for p in bad:
            with self.assertRaises(ValueError) as cm:
                run_feature(p)
            self.assertEqual(str(cm.exception), "Invalid browser scan payload or budget")
            self.assertNotIn("extra", str(cm.exception))
        with self.assertRaises(ValueError) as cm:
            run_feature({"browser": "x" * 4097})
        self.assertEqual(str(cm.exception), "Invalid browser scan payload or budget")
        with self.assertRaises(ValueError) as cm:
            run_feature({"browser": {"a": "b", "c": "d"}, "max_entries": 1})
        self.assertEqual(str(cm.exception), "Invalid browser scan payload or budget")
        with self.assertRaises(ValueError) as cm:
            run_feature({"browser": "x", "max_length": 1, "max_entries": 200})
            run_feature({"browser": "xy", "max_length": 1})
        self.assertEqual(str(cm.exception), "Invalid browser scan payload or budget")
    def test_no_mutation_fresh(self):
        inner = {"b": "y", "a": False}
        payload = {"browser": inner}
        snap = copy.deepcopy(payload)
        o1 = run_feature(payload)
        self.assertEqual(payload, snap)
        o2 = run_feature(payload)
        self.assertEqual(o1, o2)
        self.assertIsNot(o1, o2)
        self.assertIsNot(o1["ignored"], o2["ignored"])
        self.assertIsNot(o1["remapped"], o2["remapped"])
        o1["ignored"].append("zzz")
        o1["remapped"].append({"from": "q", "to": "w"})
        self.assertEqual(payload, snap)
        o3 = run_feature(payload)
        self.assertEqual(o3["entry_count"], 2)
    def test_subclass_preserved(self):
        class S(str):
            pass
        s = S("./BROWSER.JS")
        out = run_feature({"browser": s})
        self.assertEqual(out["replacement"], "./BROWSER.JS")
        self.assertIsInstance(out["replacement"], str)
        k = S("Fs")
        v = S("./Shim.JS")
        out2 = run_feature({"browser": {k: v}})
        self.assertEqual(out2["remapped"], [{"from": "Fs", "to": "./Shim.JS"}])
        self.assertIsInstance(list(out2["remapped"][0].values())[0], str)
    def test_deterministic(self):
        p = {"browser": {"z": "1", "a": False}}
        self.assertEqual(run_feature(p), run_feature(copy.deepcopy(p)))
if __name__ == "__main__":
    unittest.main()
