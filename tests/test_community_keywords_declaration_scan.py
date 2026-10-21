import unittest

try:
    from src.npm_tarball_audit.features.keywords_declaration_scan import run_feature
except ImportError:
    from npm_tarball_audit.features.keywords_declaration_scan import run_feature

EXPECTED_ERROR = "Invalid keywords scan payload or budget"


class KeywordsDeclarationScanTest(unittest.TestCase):
    def test_absent_none(self):
        payload = {"keywords": None}
        snapshot = {"keywords": None}
        out = run_feature(payload)
        self.assertEqual(out, {"keywords": [], "count": 0, "declared": False})
        self.assertEqual(payload, snapshot)
        self.assertEqual(set(out.keys()), {"keywords", "count", "declared"})

    def test_empty_list_absent(self):
        out = run_feature({"keywords": []})
        self.assertEqual(out, {"keywords": [], "count": 0, "declared": False})
        self.assertFalse(out["declared"])
        self.assertEqual(out["count"], 0)

    def test_non_empty_preserves_order_case_whitespace(self):
        payload = {"keywords": ["  Search  ", "Node.js", "audit"]}
        out = run_feature(payload)
        self.assertEqual(out["keywords"], ["  Search  ", "Node.js", "audit"])
        self.assertEqual(out["count"], 3)
        self.assertTrue(out["declared"])
        self.assertEqual(payload, {"keywords": ["  Search  ", "Node.js", "audit"]})

    def test_examples_from_contract(self):
        self.assertEqual(run_feature({"keywords": None}), {"keywords": [], "count": 0, "declared": False})
        self.assertEqual(run_feature({"keywords": ["audit", "reproducible"]}), {"keywords": ["audit", "reproducible"], "count": 2, "declared": True})
        out = run_feature({"keywords": ["  Search  ", "Node.js"], "max_entries": 64, "max_length": 256})
        self.assertEqual(out, {"keywords": ["  Search  ", "Node.js"], "count": 2, "declared": True})

    def test_str_subclass_accepted(self):
        class MyStr(str):
            pass
        payload = {"keywords": [MyStr("hello"), MyStr(" World ")]}
        out = run_feature(payload)
        self.assertEqual(out["keywords"], ["hello", " World "])
        self.assertEqual(out["count"], 2)
        self.assertTrue(out["declared"])

    def test_custom_budgets_valid(self):
        out = run_feature({"keywords": ["a", "b"], "max_entries": 2, "max_length": 1})
        self.assertEqual(out["count"], 2)
        self.assertTrue(out["declared"])
        out2 = run_feature({"keywords": ["ab"], "max_length": 2})
        self.assertEqual(out2["keywords"], ["ab"])

    def test_oversize_list_raises(self):
        big = []
        for i in range(65):
            big.append("k")
        with self.assertRaises(ValueError) as cm:
            run_feature({"keywords": big})
        self.assertEqual(str(cm.exception), EXPECTED_ERROR)
        with self.assertRaises(ValueError) as cm2:
            run_feature({"keywords": ["a", "b", "c"], "max_entries": 2})
        self.assertEqual(str(cm2.exception), EXPECTED_ERROR)

    def test_overlong_and_empty_string_raise(self):
        long_s = ""
        for i in range(257):
            long_s = long_s + "x"
        with self.assertRaises(ValueError) as cm:
            run_feature({"keywords": [long_s]})
        self.assertEqual(str(cm.exception), EXPECTED_ERROR)
        with self.assertRaises(ValueError):
            run_feature({"keywords": [""]})
        with self.assertRaises(ValueError):
            run_feature({"keywords": ["ok", ""]})
        with self.assertRaises(ValueError) as cm3:
            run_feature({"keywords": ["abc"], "max_length": 2})
        self.assertEqual(str(cm3.exception), EXPECTED_ERROR)

    def test_wrong_types_raise(self):
        bad_payloads = [None, [], "x", 123, {"keywords": "audit"}, {"keywords": 123}, {"keywords": True}, {"keywords": ("a",)}, {"keywords": [123]}, {"keywords": [None]}, {"keywords": [True]}, {"keywords": [b"bytes"]}]
        for p in bad_payloads:
            with self.assertRaises(ValueError) as cm:
                run_feature(p)
            self.assertEqual(str(cm.exception), EXPECTED_ERROR)

    def test_extra_and_missing_keys_raise(self):
        with self.assertRaises(ValueError) as cm:
            run_feature({})
        self.assertEqual(str(cm.exception), EXPECTED_ERROR)
        with self.assertRaises(ValueError) as cm2:
            run_feature({"max_entries": 64})
        self.assertEqual(str(cm2.exception), EXPECTED_ERROR)
        with self.assertRaises(ValueError) as cm3:
            run_feature({"keywords": None, "extra": 1})
        self.assertEqual(str(cm3.exception), EXPECTED_ERROR)
        with self.assertRaises(ValueError) as cm4:
            run_feature({"keywords": [], "max_entries": 64, "unknown": 1})
        self.assertEqual(str(cm4.exception), EXPECTED_ERROR)

    def test_bad_budgets_raise(self):
        bad_budgets = [0, -1, -100, True, False, 1.5, "64", None, [], {}]
        for b in bad_budgets:
            with self.assertRaises(ValueError) as cm:
                run_feature({"keywords": [], "max_entries": b})
            self.assertEqual(str(cm.exception), EXPECTED_ERROR)
            with self.assertRaises(ValueError) as cm2:
                run_feature({"keywords": [], "max_length": b})
            self.assertEqual(str(cm2.exception), EXPECTED_ERROR)

    def test_error_does_not_echo_input(self):
        marker = "evil-marker-xyz-987"
        with self.assertRaises(ValueError) as cm:
            run_feature({"keywords": [marker], "max_length": 2, "extra-echo-test": marker})
        self.assertEqual(str(cm.exception), EXPECTED_ERROR)
        self.assertNotIn(marker, str(cm.exception))
        long_marker = "qm-" + marker
        with self.assertRaises(ValueError) as cm2:
            run_feature({"keywords": long_marker})
        self.assertEqual(str(cm2.exception), EXPECTED_ERROR)
        self.assertNotIn(marker, str(cm2.exception))

    def test_no_mutation(self):
        original = ["  A  ", "b"]
        payload = {"keywords": original}
        snap_list = list(original)
        out = run_feature(payload)
        self.assertEqual(payload["keywords"], snap_list)
        self.assertEqual(original, snap_list)
        out["keywords"].append("mut")
        self.assertEqual(payload["keywords"], snap_list)
        payload2 = {"keywords": None}
        run_feature(payload2)
        self.assertEqual(payload2, {"keywords": None})

    def test_fresh_containers_and_deterministic(self):
        payload = {"keywords": ["audit", "Node.js"]}
        out1 = run_feature(payload)
        out2 = run_feature(payload)
        self.assertEqual(out1, out2)
        self.assertIsNot(out1, out2)
        self.assertIsNot(out1["keywords"], out2["keywords"])
        self.assertIsNot(out1["keywords"], payload["keywords"])
        self.assertIsNot(out1, payload)
        out1["keywords"].append("x")
        self.assertEqual(out2["keywords"], ["audit", "Node.js"])
        self.assertEqual(payload["keywords"], ["audit", "Node.js"])
        empty1 = run_feature({"keywords": None})
        empty2 = run_feature({"keywords": None})
        self.assertEqual(empty1, empty2)
        self.assertIsNot(empty1["keywords"], empty2["keywords"])


if __name__ == "__main__":
    unittest.main()
