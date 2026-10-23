import unittest
try:
    from npm_tarball_audit.features.peer_meta_declaration_scan import run_feature
except ImportError:
    from src.npm_tarball_audit.features.peer_meta_declaration_scan import run_feature

_FIXED = "Invalid peer metadata scan payload or budget"

class TestPeerMetaDeclarationScan(unittest.TestCase):
    def test_absent_none(self):
        payload = {"peerDependenciesMeta": None}
        out = run_feature(payload)
        self.assertEqual(out, {"declared": False, "entries": None})
        self.assertEqual(payload, {"peerDependenciesMeta": None})
        self.assertIsNone(out["entries"])
        self.assertEqual(set(out.keys()), {"declared", "entries"})

    def test_empty_dict(self):
        payload = {"peerDependenciesMeta": {}}
        out = run_feature(payload)
        self.assertEqual(out, {"declared": True, "entries": []})
        self.assertEqual(payload, {"peerDependenciesMeta": {}})
        self.assertIsInstance(out["entries"], list)

    def test_present_sorted_verbatim(self):
        payload = {"peerDependenciesMeta": {"react": {"optional": True}, "lodash": {}, "A": {"optional": False}}}
        out = run_feature(payload)
        self.assertTrue(out["declared"])
        self.assertEqual(out["entries"], [{"name": "A", "optional": False}, {"name": "lodash", "optional": None}, {"name": "react", "optional": True}])
        self.assertEqual(payload, {"peerDependenciesMeta": {"react": {"optional": True}, "lodash": {}, "A": {"optional": False}}})

    def test_verbatim_spacing_and_case(self):
        payload = {"peerDependenciesMeta": {" b ": {}, "a": {"optional": True}}}
        out = run_feature(payload)
        self.assertEqual(out["entries"][0], {"name": " b ", "optional": None})
        self.assertEqual(out["entries"][1], {"name": "a", "optional": True})
        self.assertEqual(payload, {"peerDependenciesMeta": {" b ": {}, "a": {"optional": True}}})

    def test_str_subclass_key(self):
        class S(str):
            pass
        payload = {"peerDependenciesMeta": {S("x"): {}}}
        out = run_feature(payload)
        self.assertEqual(out, {"declared": True, "entries": [{"name": "x", "optional": None}]})

    def test_invalid_payloads_fixed_error(self):
        bad = []
        bad.append(None)
        bad.append([])
        bad.append("x")
        bad.append(123)
        bad.append({})
        bad.append({"peerDependenciesMeta": None, "extra": 1})
        bad.append({"peerDependenciesMeta": None, "max_entries": True})
        bad.append({"peerDependenciesMeta": None, "max_entries": False})
        bad.append({"peerDependenciesMeta": None, "max_entries": 0})
        bad.append({"peerDependenciesMeta": None, "max_entries": 65})
        bad.append({"peerDependenciesMeta": None, "max_entries": "32"})
        bad.append({"peerDependenciesMeta": None, "max_length": True})
        bad.append({"peerDependenciesMeta": None, "max_length": 0})
        bad.append({"peerDependenciesMeta": None, "max_length": 215})
        bad.append({"peerDependenciesMeta": None, "max_length": 1.5})
        bad.append({"peerDependenciesMeta": "x"})
        bad.append({"peerDependenciesMeta": 0})
        bad.append({"peerDependenciesMeta": 1})
        bad.append({"peerDependenciesMeta": True})
        bad.append({"peerDependenciesMeta": False})
        bad.append({"peerDependenciesMeta": []})
        bad.append({"peerDependenciesMeta": {123: {}}})
        bad.append({"peerDependenciesMeta": {"": {}}})
        bad.append({"peerDependenciesMeta": {"a": "x"}})
        bad.append({"peerDependenciesMeta": {"a": None}})
        bad.append({"peerDependenciesMeta": {"a": []}})
        bad.append({"peerDependenciesMeta": {"a": {"optional": 1}}})
        bad.append({"peerDependenciesMeta": {"a": {"optional": 0}}})
        bad.append({"peerDependenciesMeta": {"a": {"optional": "t"}}})
        bad.append({"peerDependenciesMeta": {"a": {"other": True}}})
        bad.append({"peerDependenciesMeta": {"a": {"optional": True, "x": 1}}})
        bad.append({"peerDependenciesMeta": {"a": {"optional": None}}})
        for p in bad:
            with self.subTest(payload=p):
                with self.assertRaises(ValueError) as cm:
                    run_feature(p)
                self.assertEqual(str(cm.exception), _FIXED)

    def test_budgets_bounds_and_defaults(self):
        out = run_feature({"peerDependenciesMeta": {"a": {}}})
        self.assertEqual(len(out["entries"]), 1)
        out2 = run_feature({"peerDependenciesMeta": {"a": {}}, "max_entries": 1, "max_length": 1})
        self.assertEqual(out2["entries"], [{"name": "a", "optional": None}])
        with self.assertRaises(ValueError) as cm:
            run_feature({"peerDependenciesMeta": {"abc": {}}, "max_length": 2})
        self.assertEqual(str(cm.exception), _FIXED)
        long_key = "k" * 214
        out3 = run_feature({"peerDependenciesMeta": {long_key: {}}})
        self.assertEqual(out3["entries"][0]["name"], long_key)
        with self.assertRaises(ValueError) as cm2:
            run_feature({"peerDependenciesMeta": {"k" * 215: {}}})
        self.assertEqual(str(cm2.exception), _FIXED)
        many = {}
        for i in range(33):
            many["p" + str(i)] = {}
        with self.assertRaises(ValueError):
            run_feature({"peerDependenciesMeta": many})
        many_ok = {}
        for i in range(32):
            many_ok["q" + str(i)] = {}
        out4 = run_feature({"peerDependenciesMeta": many_ok})
        self.assertEqual(len(out4["entries"]), 32)
        limited = {}
        for i in range(3):
            limited["z" + str(i)] = {}
        with self.assertRaises(ValueError):
            run_feature({"peerDependenciesMeta": limited, "max_entries": 2})

    def test_repeated_calls_fresh(self):
        payload = {"peerDependenciesMeta": {"b": {}, "a": {"optional": True}}}
        r1 = run_feature(payload)
        r2 = run_feature(payload)
        self.assertEqual(r1, r2)
        self.assertIsNot(r1, r2)
        self.assertIsNot(r1["entries"], r2["entries"])
        self.assertIsNot(r1["entries"][0], r2["entries"][0])
        r1["entries"].append({"name": "zzz", "optional": True})
        r1["entries"][0]["name"] = "mut"
        self.assertNotEqual(r1, r2)
        r3 = run_feature(payload)
        self.assertEqual(r3, r2)
        self.assertEqual(payload, {"peerDependenciesMeta": {"b": {}, "a": {"optional": True}}})

if __name__ == "__main__":
    unittest.main()
