import unittest
try:
    from npm_tarball_audit.features.inventory_composition_summary import run_feature
except ImportError:
    from src.npm_tarball_audit.features.inventory_composition_summary import run_feature
PAYLOAD_ERROR = "Invalid inventory summary payload or budget"
RECORD_ERROR = "Invalid inventory record"
A64 = "a" * 64
B64 = "b" * 64
C64 = "c" * 64
D64 = "d" * 64
E64 = "A" * 64
class MyStr(str):
    pass
class MyInt(int):
    pass
def _rec(path, size, sha):
    return {"path": path, "bytes": size, "sha256": sha}
class TestInventoryCompositionSummary(unittest.TestCase):
    def test_two_files_distinct_extensions(self):
        payload = {"inventory": [_rec("package/index.js", 100, A64), _rec("package/README.md", 50, B64)]}
        out = run_feature(payload)
        self.assertEqual(out["total_files"], 2)
        self.assertEqual(out["total_bytes"], 150)
        self.assertEqual(out["by_extension"], [{"extension": "js", "count": 1, "bytes": 100}, {"extension": "md", "count": 1, "bytes": 50}])
        self.assertEqual(list(out.keys()), ["total_files", "total_bytes", "by_extension"])
    def test_empty_inventory(self):
        out = run_feature({"inventory": []})
        self.assertEqual(out, {"total_files": 0, "total_bytes": 0, "by_extension": []})
        self.assertEqual(list(out.keys()), ["total_files", "total_bytes", "by_extension"])
    def test_case_insensitive_dotless_leading_dot(self):
        payload = {"inventory": [_rec("package/.npmignore", 10, C64), _rec("package/lib/Tool.JS", 20, D64)]}
        out = run_feature(payload)
        self.assertEqual(out["total_files"], 2)
        self.assertEqual(out["total_bytes"], 30)
        self.assertEqual(out["by_extension"], [{"extension": "", "count": 1, "bytes": 10}, {"extension": "js", "count": 1, "bytes": 20}])
    def test_grouping_sorted_case_insensitive(self):
        payload = {"inventory": [_rec("package/a.TXT", 5, A64), _rec("package/b.txt", 7, B64), _rec("package/README", 3, C64)]}
        out = run_feature(payload)
        self.assertEqual(out["total_files"], 3)
        self.assertEqual(out["total_bytes"], 15)
        self.assertEqual(out["by_extension"], [{"extension": "", "count": 1, "bytes": 3}, {"extension": "txt", "count": 2, "bytes": 12}])
    def test_upper_hex_accepted(self):
        out = run_feature({"inventory": [_rec("package/a.js", 1, E64)]})
        self.assertEqual(out["total_files"], 1)
        self.assertEqual(out["by_extension"], [{"extension": "js", "count": 1, "bytes": 1}])
    def test_record_errors(self):
        backslash_path = "package/a" + chr(92) + "b.js"
        bad_paths = ["other/file.js", backslash_path, "package//a.js", "package/a/", "package/./a.js", "package/../a.js", "package/a/./b.js", "package/a/../b.js", "package/a/.", "package/a/..", "package/./", "package"]
        for bp in bad_paths:
            with self.assertRaises(ValueError) as cm:
                run_feature({"inventory": [_rec(bp, 1, A64)]})
            self.assertEqual(str(cm.exception), RECORD_ERROR)
            self.assertNotIn(bp, str(cm.exception))
        with self.assertRaises(ValueError) as cm:
            run_feature({"inventory": [_rec("package/dup.js", 1, A64), _rec("package/dup.js", 1, B64)]})
        self.assertEqual(str(cm.exception), RECORD_ERROR)
        out = run_feature({"inventory": [_rec("package/a.js", 1, A64), _rec("package/A.js", 1, B64)]})
        self.assertEqual(out["total_files"], 2)
        bad_records = [{"path": "package/a.js", "bytes": -1, "sha256": A64}, {"path": "package/a.js", "bytes": 33554433, "sha256": A64}, {"path": "package/a.js", "bytes": "10", "sha256": A64}, {"path": "package/a.js", "bytes": True, "sha256": A64}, {"path": "package/a.js", "bytes": 1.0, "sha256": A64}, {"path": "package/a.js", "bytes": 1, "sha256": "a" * 63}, {"path": "package/a.js", "bytes": 1, "sha256": "g" * 64}, {"path": "package/a.js", "bytes": 1, "sha256": 123}, {"path": 123, "bytes": 1, "sha256": A64}, {"path": "package/a.js", "bytes": 1}, {"path": "package/a.js", "bytes": 1, "sha256": A64, "extra": 1}]
        for rec in bad_records:
            with self.assertRaises(ValueError) as cm:
                run_feature({"inventory": [rec]})
            self.assertEqual(str(cm.exception), RECORD_ERROR)
        with self.assertRaises(ValueError) as cm:
            run_feature({"inventory": ["not-a-dict"]})
        self.assertEqual(str(cm.exception), RECORD_ERROR)
        with self.assertRaises(ValueError) as cm:
            run_feature({"inventory": [_rec("package/a.js", MyInt(1), A64)]})
        self.assertEqual(str(cm.exception), RECORD_ERROR)
    def test_payload_errors(self):
        with self.assertRaises(ValueError) as cm:
            run_feature([1, 2])
        self.assertEqual(str(cm.exception), PAYLOAD_ERROR)
        with self.assertRaises(ValueError) as cm:
            run_feature(None)
        self.assertEqual(str(cm.exception), PAYLOAD_ERROR)
        with self.assertRaises(ValueError) as cm:
            run_feature({})
        self.assertEqual(str(cm.exception), PAYLOAD_ERROR)
        with self.assertRaises(ValueError) as cm:
            run_feature({"inventory": [], "extra": 1})
        self.assertEqual(str(cm.exception), PAYLOAD_ERROR)
        with self.assertRaises(ValueError) as cm:
            run_feature({"max_entries": 10})
        self.assertEqual(str(cm.exception), PAYLOAD_ERROR)
        for bad_budget in [1.0, True, False, "10", [10], {"v": 1}, None, 0, 20001, -5, MyInt(10), MyStr("10")]:
            with self.assertRaises(ValueError) as cm:
                run_feature({"inventory": [], "max_entries": bad_budget})
            self.assertEqual(str(cm.exception), PAYLOAD_ERROR)
        with self.assertRaises(ValueError) as cm:
            run_feature({"inventory": [_rec("package/a.js", 1, A64), _rec("package/b.js", 1, B64)], "max_entries": 1})
        self.assertEqual(str(cm.exception), PAYLOAD_ERROR)
        with self.assertRaises(ValueError) as cm:
            run_feature({"inventory": "nope"})
        self.assertEqual(str(cm.exception), PAYLOAD_ERROR)
        with self.assertRaises(ValueError) as cm:
            run_feature("nope")
        self.assertEqual(str(cm.exception), PAYLOAD_ERROR)
    def test_subclass_strings_accepted(self):
        payload = {"inventory": [_rec(MyStr("package/a.js"), 1, MyStr(A64))]}
        out = run_feature(payload)
        self.assertEqual(out["total_files"], 1)
        self.assertEqual(out["by_extension"], [{"extension": "js", "count": 1, "bytes": 1}])
        self.assertTrue(type(out["by_extension"][0]["extension"]) is str)
    def test_preserve_input_fresh_order(self):
        payload = {"inventory": [_rec("package/b.md", 50, B64), _rec("package/a.js", 100, A64)]}
        out1 = run_feature(payload)
        self.assertEqual(payload, {"inventory": [_rec("package/b.md", 50, B64), _rec("package/a.js", 100, A64)]})
        self.assertEqual(list(out1.keys()), ["total_files", "total_bytes", "by_extension"])
        for entry in out1["by_extension"]:
            self.assertEqual(list(entry.keys()), ["extension", "count", "bytes"])
            self.assertTrue(type(entry["extension"]) is str)
        self.assertTrue(type(out1["total_files"]) is int)
        self.assertTrue(type(out1["total_bytes"]) is int)
        self.assertEqual([e["extension"] for e in out1["by_extension"]], sorted([e["extension"] for e in out1["by_extension"]]))
        out2 = run_feature(payload)
        self.assertEqual(out1, out2)
        self.assertIsNot(out1, out2)
        self.assertIsNot(out1["by_extension"], out2["by_extension"])
        self.assertIsNot(out1["by_extension"][0], out2["by_extension"][0])
        out1["by_extension"].append({"extension": "x", "count": 1, "bytes": 1})
        out3 = run_feature(payload)
        self.assertEqual(out3, out2)
if __name__ == "__main__":
    unittest.main()
