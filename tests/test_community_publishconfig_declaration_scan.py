import copy
import unittest

from src.npm_tarball_audit.features.publishconfig_declaration_scan import run_feature

EXPECTED = "Invalid publishConfig scan payload or budget"


class PublishConfigDeclarationScanTest(unittest.TestCase):
    def test_absent_none(self):
        payload = {"publishConfig": None}
        snapshot = copy.deepcopy(payload)
        result = run_feature(payload)
        self.assertEqual(result, {"entries": None, "declared": False})
        self.assertIsNone(result["entries"])
        self.assertIs(result["declared"], False)
        self.assertEqual(payload, snapshot)

    def test_empty_dict(self):
        first = run_feature({"publishConfig": {}})
        second = run_feature({"publishConfig": {}})
        self.assertEqual(first, {"entries": [], "declared": True})
        self.assertEqual(second, {"entries": [], "declared": True})
        self.assertEqual(first, second)
        self.assertIsNot(first, second)
        self.assertIsNot(first["entries"], second["entries"])

    def test_populated_sorted_verbatim(self):
        payload = {"publishConfig": {"access": "public", "registry": "https://registry.npmjs.org/"}}
        result = run_feature(payload)
        self.assertTrue(result["declared"])
        self.assertEqual(result["entries"], [{"key": "access", "value": "public"}, {"key": "registry", "value": "https://registry.npmjs.org/"}])
        unsorted = {"publishConfig": {"zebra": "1", "apple": "2", "mango": "3"}}
        ordered = run_feature(unsorted)
        self.assertEqual([e["key"] for e in ordered["entries"]], ["apple", "mango", "zebra"])

    def test_codepoint_sort_and_verbatim(self):
        payload = {"publishConfig": {"b": " B ", "a": "A", "A": " a "}}
        result = run_feature(payload)
        self.assertEqual([e["key"] for e in result["entries"]], ["A", "a", "b"])
        self.assertEqual(result["entries"][2], {"key": "b", "value": " B "})
        uni = {"publishConfig": {"caf\u00e9": " v\u00e9 ", "caféX": "x"}}
        ures = run_feature(uni)
        self.assertEqual(ures["entries"][0]["value"], " v\u00e9 ")

    def test_str_subclass_accepted(self):
        class S(str):
            pass
        payload = {"publishConfig": {S("k"): S("v")}}
        result = run_feature(payload)
        self.assertEqual(result, {"entries": [{"key": "k", "value": "v"}], "declared": True})

    def test_non_dict_publishconfig_values_raise_fixed(self):
        bad_values = ["public", "", 0, 1, 123, True, False, [], ["a"], 3.14, ("a",), {"a"}]
        for bad in bad_values:
            with self.subTest(bad=repr(bad)):
                with self.assertRaises(ValueError) as ctx:
                    run_feature({"publishConfig": bad})
                self.assertEqual(str(ctx.exception), EXPECTED)
                self.assertNotIn(repr(bad), str(ctx.exception))

    def test_non_string_key_or_value_raise(self):
        cases = [{123: "v"}, {"k": 123}, {"k": None}, {"k": True}, {None: "v"}, {(1, 2): "v"}, {"k": ["v"]}]
        for case in cases:
            with self.subTest(case=repr(case)):
                with self.assertRaises(ValueError) as ctx:
                    run_feature({"publishConfig": case})
                self.assertEqual(str(ctx.exception), EXPECTED)

    def test_empty_or_overlength_string_raise(self):
        with self.assertRaises(ValueError) as ctx:
            run_feature({"publishConfig": {"": "v"}})
        self.assertEqual(str(ctx.exception), EXPECTED)
        with self.assertRaises(ValueError) as ctx:
            run_feature({"publishConfig": {"k": ""}})
        self.assertEqual(str(ctx.exception), EXPECTED)
        long_s = "x" * 513
        with self.assertRaises(ValueError) as ctx:
            run_feature({"publishConfig": {"k": long_s}})
        self.assertEqual(str(ctx.exception), EXPECTED)
        with self.assertRaises(ValueError) as ctx:
            run_feature({"publishConfig": {long_s: "v"}})
        self.assertEqual(str(ctx.exception), EXPECTED)
        self.assertNotIn(long_s, str(ctx.exception))

    def test_over_count_extra_key_missing_key_nondict_payload(self):
        big = {}
        for i in range(33):
            big["k" + str(i)] = "v"
        with self.assertRaises(ValueError) as ctx:
            run_feature({"publishConfig": big})
        self.assertEqual(str(ctx.exception), EXPECTED)
        with self.assertRaises(ValueError) as ctx:
            run_feature({"publishConfig": None, "extra": 1})
        self.assertEqual(str(ctx.exception), EXPECTED)
        with self.assertRaises(ValueError) as ctx:
            run_feature({})
        self.assertEqual(str(ctx.exception), EXPECTED)
        for bad_payload in [None, [], "x", 0, True, 123]:
            with self.subTest(payload=repr(bad_payload)):
                with self.assertRaises(ValueError) as ctx:
                    run_feature(bad_payload)
                self.assertEqual(str(ctx.exception), EXPECTED)

    def test_invalid_budgets_raise(self):
        for key in ("max_entries", "max_length"):
            for bad in [True, False, 0, -1, -5, "2", 2.0, None, [], {}]:
                with self.subTest(key=key, bad=repr(bad)):
                    with self.assertRaises(ValueError) as ctx:
                        run_feature({"publishConfig": None, key: bad})
                    self.assertEqual(str(ctx.exception), EXPECTED)

    def test_custom_budgets_enforce_bounds(self):
        ok = {"publishConfig": {"a": "1", "b": "2"}, "max_entries": 2}
        res = run_feature(ok)
        self.assertEqual(len(res["entries"]), 2)
        with self.assertRaises(ValueError):
            run_feature({"publishConfig": {"a": "1", "b": "2", "c": "3"}, "max_entries": 2})
        exact = "y" * 3
        res2 = run_feature({"publishConfig": {"k": exact}, "max_length": 3})
        self.assertEqual(res2["entries"][0]["value"], exact)
        with self.assertRaises(ValueError):
            run_feature({"publishConfig": {"k": "yyyy"}, "max_length": 3})
        with self.assertRaises(ValueError):
            run_feature({"publishConfig": {}, "max_entries": True})
        with self.assertRaises(ValueError):
            run_feature({"publishConfig": {}, "max_length": False})

    def test_repeated_calls_independent(self):
        payload = {"publishConfig": {"b": "2", "a": "1"}}
        first = run_feature(payload)
        second = run_feature(payload)
        self.assertEqual(first, second)
        self.assertIsNot(first, second)
        self.assertIsNot(first["entries"], second["entries"])
        self.assertIsNot(first["entries"][0], second["entries"][0])
        first["entries"][0]["value"] = "MUT"
        first["entries"].append({"key": "x", "value": "y"})
        third = run_feature(payload)
        self.assertEqual(third, second)
        self.assertEqual(payload, {"publishConfig": {"b": "2", "a": "1"}})

    def test_no_echo_and_no_mutation(self):
        payload = {"publishConfig": {"k": "v"}}
        snapshot = copy.deepcopy(payload)
        run_feature(payload)
        self.assertEqual(payload, snapshot)
        evil = "EVIL-ECHO-UNIQUE-12345"
        with self.assertRaises(ValueError) as ctx:
            run_feature({"publishConfig": {evil: "v"}, "max_length": 2})
        self.assertEqual(str(ctx.exception), EXPECTED)
        self.assertNotIn(evil, str(ctx.exception))


if __name__ == "__main__":
    unittest.main()
