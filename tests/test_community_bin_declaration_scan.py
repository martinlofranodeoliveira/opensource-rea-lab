import unittest
try:
    from npm_tarball_audit.features.bin_declaration_scan import run_feature
except ImportError:
    from src.npm_tarball_audit.features.bin_declaration_scan import run_feature

PAYLOAD_ERROR = "Invalid bin payload or budget"
DECLARATION_ERROR = "Invalid bin declaration"

class TestCommunityBinDeclarationScan(unittest.TestCase):
    def test_absent_none(self):
        payload = {"bin": None}
        result = run_feature(payload)
        self.assertEqual(payload, {"bin": None})
        self.assertEqual(result, {"present": False, "kind": "absent", "total": 0, "valid_count": 0, "invalid_count": 0, "entries": []})
        self.assertEqual(list(result.keys()), ["present", "kind", "total", "valid_count", "invalid_count", "entries"])

    def test_string_valid(self):
        payload = {"bin": "bin/cli.js"}
        result = run_feature(payload)
        self.assertEqual(payload, {"bin": "bin/cli.js"})
        self.assertEqual(result["present"], True)
        self.assertEqual(result["kind"], "string")
        self.assertEqual(result["total"], 1)
        self.assertEqual(result["valid_count"], 1)
        self.assertEqual(result["invalid_count"], 0)
        self.assertEqual(len(result["entries"]), 1)
        entry = result["entries"][0]
        self.assertIsNone(entry["key"])
        self.assertEqual(entry["target"], "bin/cli.js")
        self.assertEqual(entry["valid"], True)
        self.assertEqual(entry["reasons"], [])
        self.assertEqual(list(result.keys()), ["present", "kind", "total", "valid_count", "invalid_count", "entries"])

    def test_string_dot_slash_prefix_valid(self):
        result = run_feature({"bin": "./bin/cli.js"})
        self.assertEqual(result["kind"], "string")
        self.assertEqual(result["entries"][0]["valid"], True)
        self.assertEqual(result["entries"][0]["reasons"], [])
        self.assertEqual(result["entries"][0]["target"], "./bin/cli.js")

    def test_string_syntax_invalid(self):
        targets = ["/abs/path", "a//b", "a/b/", "a/./b", "a/../b", ".", "./", "a" + chr(92) + "b", "a*b", "a:b", "../evil", "./../evil", "a/" + chr(1) + "b", "a" + chr(127) + "b"]
        for target in targets:
            with self.subTest(target=target):
                result = run_feature({"bin": target})
                self.assertEqual(result["kind"], "string")
                entry = result["entries"][0]
                self.assertEqual(entry["valid"], False)
                self.assertEqual(entry["reasons"], ["value_syntax"])
                self.assertIsNone(entry["key"])

    def test_string_length_invalid(self):
        result = run_feature({"bin": ""})
        self.assertEqual(result["entries"][0]["reasons"], ["value_length"])
        self.assertEqual(result["entries"][0]["valid"], False)
        long_target = "a" * 257
        result2 = run_feature({"bin": long_target})
        self.assertEqual(result2["entries"][0]["reasons"], ["value_length"])
        ok_target = "a" * 256
        result3 = run_feature({"bin": ok_target})
        self.assertEqual(result3["entries"][0]["valid"], True)
        self.assertEqual(result3["entries"][0]["reasons"], [])

    def test_map_sorted_counts_example(self):
        payload = {"bin": {"Bad!": "../evil", "tool": "bin/cli.js"}}
        result = run_feature(payload)
        self.assertEqual(payload, {"bin": {"Bad!": "../evil", "tool": "bin/cli.js"}})
        self.assertEqual(result["present"], True)
        self.assertEqual(result["kind"], "map")
        self.assertEqual(result["total"], 2)
        self.assertEqual(result["valid_count"], 1)
        self.assertEqual(result["invalid_count"], 1)
        self.assertEqual([e["key"] for e in result["entries"]], ["Bad!", "tool"])
        first = result["entries"][0]
        self.assertEqual(first["target"], "../evil")
        self.assertEqual(first["valid"], False)
        self.assertEqual(first["reasons"], ["key_syntax", "value_syntax"])
        second = result["entries"][1]
        self.assertEqual(second["target"], "bin/cli.js")
        self.assertEqual(second["reasons"], [])
        self.assertEqual(second["valid"], True)

    def test_map_key_syntax(self):
        result = run_feature({"bin": {"-bad": "bin/a.js", "Good": "bin/b.js", "ok_name-1.2": "bin/c.js"}})
        by_key = {}
        for e in result["entries"]:
            by_key[e["key"]] = e
        self.assertIn("key_syntax", by_key["-bad"]["reasons"])
        self.assertIn("key_syntax", by_key["Good"]["reasons"])
        self.assertEqual(by_key["ok_name-1.2"]["reasons"], [])
        self.assertEqual([e["key"] for e in result["entries"]], sorted(["-bad", "Good", "ok_name-1.2"]))

    def test_empty_dict(self):
        payload = {"bin": {}}
        result = run_feature(payload)
        self.assertEqual(payload, {"bin": {}})
        self.assertEqual(result["present"], True)
        self.assertEqual(result["kind"], "empty")
        self.assertEqual(result["total"], 0)
        self.assertEqual(result["valid_count"], 0)
        self.assertEqual(result["invalid_count"], 0)
        self.assertEqual(result["entries"], [])

    def test_oversize_dict_raises(self):
        payload = {"bin": {"a": "b", "c": "d"}, "max_entries": 1}
        with self.assertRaises(ValueError) as ctx:
            run_feature(payload)
        self.assertEqual(str(ctx.exception), DECLARATION_ERROR)
        self.assertEqual(payload, {"bin": {"a": "b", "c": "d"}, "max_entries": 1})

    def test_non_str_keys_values_raise(self):
        bads = [{"bin": {123: "bin/a.js"}}, {"bin": {"a": 123}}, {"bin": {"a": None}}, {"bin": {True: "bin/a.js"}}]
        for bad in bads:
            with self.subTest(bad=bad):
                with self.assertRaises(ValueError) as ctx:
                    run_feature(bad)
                self.assertEqual(str(ctx.exception), DECLARATION_ERROR)

    def test_top_bin_types_raise(self):
        bad_bins = [123, True, False, 1.5, ["bin/a.js"], ("a",)]
        for bad_bin in bad_bins:
            with self.subTest(bad_bin=bad_bin):
                with self.assertRaises(ValueError) as ctx:
                    run_feature({"bin": bad_bin})
                self.assertEqual(str(ctx.exception), DECLARATION_ERROR)

    def test_bad_budgets_raise(self):
        bad_budgets = [True, False, 1.5, "16", None, [], {}, 0, 65]
        for bad in bad_budgets:
            with self.subTest(bad=bad):
                with self.assertRaises(ValueError) as ctx:
                    run_feature({"bin": None, "max_entries": bad})
                self.assertEqual(str(ctx.exception), PAYLOAD_ERROR)
        with self.assertRaises(ValueError) as ctx2:
            run_feature({"bin": None, "max_key_length": 0})
        self.assertEqual(str(ctx2.exception), PAYLOAD_ERROR)
        with self.assertRaises(ValueError) as ctx3:
            run_feature({"bin": None, "max_value_length": 513})
        self.assertEqual(str(ctx3.exception), PAYLOAD_ERROR)
        with self.assertRaises(ValueError) as ctx4:
            run_feature({"bin": None, "max_key_length": 129})
        self.assertEqual(str(ctx4.exception), PAYLOAD_ERROR)

    def test_missing_extra_keys_raise(self):
        with self.assertRaises(ValueError) as ctx:
            run_feature({})
        self.assertEqual(str(ctx.exception), PAYLOAD_ERROR)
        with self.assertRaises(ValueError) as ctx2:
            run_feature({"bin": None, "extra": 1})
        self.assertEqual(str(ctx2.exception), PAYLOAD_ERROR)
        for bad_payload in [None, [], "x", 123]:
            with self.subTest(bad_payload=bad_payload):
                with self.assertRaises(ValueError) as ctx3:
                    run_feature(bad_payload)
                self.assertEqual(str(ctx3.exception), PAYLOAD_ERROR)

    def test_input_not_mutated_and_fresh(self):
        payload = {"bin": {"b": "bin/b.js", "a": "bin/a.js"}}
        first = run_feature(payload)
        second = run_feature(payload)
        self.assertEqual(payload, {"bin": {"b": "bin/b.js", "a": "bin/a.js"}})
        self.assertEqual(first, second)
        self.assertIsNot(first, second)
        self.assertIsNot(first["entries"], second["entries"])
        self.assertIsNot(first["entries"][0], second["entries"][0])
        self.assertIsNot(first["entries"][0]["reasons"], second["entries"][0]["reasons"])
        first["entries"].append({"key": "x", "target": "y", "valid": True, "reasons": []})
        self.assertNotEqual(first, second)

    def test_custom_budgets_enforced(self):
        result = run_feature({"bin": "ab", "max_value_length": 2})
        self.assertEqual(result["entries"][0]["valid"], True)
        result2 = run_feature({"bin": "abc", "max_value_length": 2})
        self.assertEqual(result2["entries"][0]["reasons"], ["value_length"])
        result3 = run_feature({"bin": {"toolongkey": "bin/a.js"}, "max_key_length": 3})
        self.assertEqual(result3["entries"][0]["reasons"], ["key_syntax"])

if __name__ == "__main__":
    unittest.main()
