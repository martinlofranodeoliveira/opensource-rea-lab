import unittest
try:
    from npm_tarball_audit.features.volta_declaration_scan import run_feature
except ImportError:
    from src.npm_tarball_audit.features.volta_declaration_scan import run_feature
class TestVoltaDeclarationScan(unittest.TestCase):
    def test_absent_null(self):
        payload = {"volta": None}
        before = {"volta": None}
        out = run_feature(payload)
        self.assertEqual(payload, before)
        self.assertEqual(out["present"], False)
        self.assertEqual(out["kind"], "absent")
        self.assertEqual(out["total"], 0)
        self.assertEqual(out["valid_count"], 0)
        self.assertEqual(out["invalid_count"], 0)
        self.assertEqual(out["entries"], [])
        self.assertEqual(list(out.keys()), ["present", "kind", "total", "valid_count", "invalid_count", "entries"])
    def test_empty_dict(self):
        out = run_feature({"volta": {}})
        self.assertEqual(out["present"], True)
        self.assertEqual(out["kind"], "empty")
        self.assertEqual(out["total"], 0)
        self.assertEqual(out["valid_count"], 0)
        self.assertEqual(out["invalid_count"], 0)
        self.assertEqual(out["entries"], [])
    def test_pinned_valid_sorted(self):
        out = run_feature({"volta": {"yarn": "1.22.19", "node": "18.17.1", "npm": "9.6.7"}})
        self.assertEqual(out["present"], True)
        self.assertEqual(out["kind"], "pinned")
        self.assertEqual(out["total"], 3)
        self.assertEqual(out["valid_count"], 3)
        self.assertEqual(out["invalid_count"], 0)
        self.assertEqual([e["key"] for e in out["entries"]], ["node", "npm", "yarn"])
        for e in out["entries"]:
            self.assertEqual(e["valid"], True)
            self.assertEqual(e["reasons"], [])
    def test_contract_example_mixed(self):
        out = run_feature({"volta": {"node": "^18.0.0", "yarn": ""}})
        self.assertEqual(out["total"], 2)
        self.assertEqual(out["valid_count"], 0)
        self.assertEqual(out["invalid_count"], 2)
        first = out["entries"][0]
        second = out["entries"][1]
        self.assertEqual(first["key"], "node")
        self.assertEqual(first["reasons"], ["value_syntax"])
        self.assertEqual(first["valid"], False)
        self.assertEqual(second["key"], "yarn")
        self.assertEqual(second["reasons"], ["value_length"])
    def test_tool_allowlist(self):
        out = run_feature({"volta": {"grunt": "1.2.3", "node": "1.2.3"}})
        by_key = {}
        for e in out["entries"]:
            by_key[e["key"]] = e
        self.assertEqual(by_key["grunt"]["reasons"], ["key_name"])
        self.assertEqual(by_key["grunt"]["valid"], False)
        self.assertEqual(by_key["node"]["valid"], True)
    def test_case_sensitive_keys(self):
        out = run_feature({"volta": {"Node": "1.2.3"}})
        self.assertEqual(out["entries"][0]["reasons"], ["key_name"])
    def test_valid_pin_shapes(self):
        for good in ["1", "18", "1.2", "18.17.1", "1.2.3.4", "00000000", "12345678.12345678.12345678.12345678"]:
            out = run_feature({"volta": {"node": good}})
            self.assertEqual(out["entries"][0]["valid"], True, msg=good)
    def test_invalid_pin_syntax(self):
        for bad in ["^18.0.0", "~1.2.3", "1.2.x", "*", "latest", "1.2.3.4.5", "123456789", "1..2", ".1", "1.", "1-2", "1+2", "1 2", "1:2", "1|2", "v1.2.3"]:
            out = run_feature({"volta": {"node": bad}})
            self.assertEqual(out["entries"][0]["reasons"], ["value_syntax"], msg=bad)
            self.assertEqual(out["entries"][0]["valid"], False)
    def test_value_length_edges(self):
        out = run_feature({"volta": {"node": ""}})
        self.assertEqual(out["entries"][0]["reasons"], ["value_length"])
        long_target = "1" * 65
        out2 = run_feature({"volta": {"node": long_target}})
        self.assertEqual(out2["entries"][0]["reasons"], ["value_length"])
    def test_reason_order_combined(self):
        out = run_feature({"volta": {"grunt": ""}})
        self.assertEqual(out["entries"][0]["reasons"], ["key_name", "value_length"])
        out2 = run_feature({"volta": {"grunt": "^1.0.0"}})
        self.assertEqual(out2["entries"][0]["reasons"], ["key_name", "value_syntax"])
    def test_bad_payload_shapes(self):
        bad_payloads = [None, [], "x", 5, {}, {"npm": "1"}, {"volta": None, "extra": 1}, {"volta": None, "max_entries": 8, "oops": 1}]
        for p in bad_payloads:
            with self.assertRaises(ValueError) as cm:
                run_feature(p)
            self.assertEqual(str(cm.exception), "Invalid volta payload or budget")
    def test_bad_budget_values(self):
        for b in [True, False, 0.0, "8", None, [], {}, 0, 17, -1, 1.0]:
            with self.assertRaises(ValueError) as cm:
                run_feature({"volta": None, "max_entries": b})
            self.assertEqual(str(cm.exception), "Invalid volta payload or budget")
        for b in [0, 33, True, "16"]:
            with self.assertRaises(ValueError) as cm:
                run_feature({"volta": None, "max_key_length": b})
            self.assertEqual(str(cm.exception), "Invalid volta payload or budget")
        for b in [0, 129, False, "64"]:
            with self.assertRaises(ValueError) as cm:
                run_feature({"volta": None, "max_value_length": b})
            self.assertEqual(str(cm.exception), "Invalid volta payload or budget")
    def test_no_echo_in_payload_error(self):
        secret = "evil-secret-marker"
        try:
            run_feature({"volta": None, secret: 1})
        except ValueError as e:
            self.assertEqual(str(e), "Invalid volta payload or budget")
            self.assertNotIn(secret, str(e))
        else:
            self.fail("expected ValueError")
    def test_bad_volta_shapes(self):
        for v in [5, True, 1.5, [], "1.2.3", "node"]:
            with self.assertRaises(ValueError) as cm:
                run_feature({"volta": v})
            self.assertEqual(str(cm.exception), "Invalid volta declaration")
            self.assertNotIn(str(v), str(cm.exception))
    def test_bad_volta_entries(self):
        with self.assertRaises(ValueError) as cm:
            run_feature({"volta": {1: "1.2.3"}})
        self.assertEqual(str(cm.exception), "Invalid volta declaration")
        with self.assertRaises(ValueError) as cm2:
            run_feature({"volta": {"node": 5}})
        self.assertEqual(str(cm2.exception), "Invalid volta declaration")
        with self.assertRaises(ValueError) as cm3:
            run_feature({"volta": {"node": None}})
        self.assertEqual(str(cm3.exception), "Invalid volta declaration")
    def test_size_budget_enforced(self):
        with self.assertRaises(ValueError) as cm:
            run_feature({"volta": {"node": "1", "npm": "1", "yarn": "1"}, "max_entries": 2})
        self.assertEqual(str(cm.exception), "Invalid volta declaration")
    def test_custom_budgets(self):
        out = run_feature({"volta": {"node": "1.2.3"}, "max_entries": 1, "max_key_length": 4, "max_value_length": 5})
        self.assertEqual(out["entries"][0]["valid"], True)
        out2 = run_feature({"volta": {"node": "1.2.3"}, "max_key_length": 3})
        self.assertEqual(out2["entries"][0]["reasons"], ["key_name"])
        out3 = run_feature({"volta": {"node": "1.2.3"}, "max_value_length": 4})
        self.assertEqual(out3["entries"][0]["reasons"], ["value_length"])
    def test_subclass_strings_accepted(self):
        class S(str):
            pass
        out = run_feature({"volta": {S("node"): S("1.2.3")}})
        self.assertEqual(out["entries"][0]["valid"], True)
        self.assertEqual(type(out["entries"][0]["key"]), str)
        self.assertEqual(type(out["entries"][0]["target"]), str)
    def test_input_not_mutated_and_fresh(self):
        payload = {"volta": {"yarn": "1.2.3", "node": "1.0.0"}}
        snapshot_keys = sorted(payload["volta"].keys())
        out1 = run_feature(payload)
        self.assertEqual(sorted(payload["volta"].keys()), snapshot_keys)
        self.assertEqual(payload, {"volta": {"yarn": "1.2.3", "node": "1.0.0"}})
        out2 = run_feature(payload)
        self.assertEqual(out1, out2)
        self.assertIsNot(out1, out2)
        self.assertIsNot(out1["entries"], out2["entries"])
        out1["entries"].append({"key": "x", "target": "1", "valid": True, "reasons": []})
        self.assertEqual(len(out2["entries"]), 2)
        out1["entries"][0]["reasons"].append("tamper")
        self.assertEqual(out2["entries"][0]["reasons"], [])
if __name__ == "__main__":
    unittest.main()
