import unittest

try:
    from src.npm_tarball_audit.features.description_declaration_scan import run_feature
except ImportError:
    from npm_tarball_audit.features.description_declaration_scan import run_feature

FIXED = "Invalid description scan payload or budget"


class DescriptionDeclarationScanTest(unittest.TestCase):
    def test_contract_examples(self):
        r1 = run_feature({"description": "Small audit helper"})
        self.assertEqual(r1, {"description": "Small audit helper", "declared": True})
        r2 = run_feature({"description": None})
        self.assertEqual(r2, {"description": None, "declared": False})
        r3 = run_feature({"description": "Hi", "max_length": 4})
        self.assertEqual(r3, {"description": "Hi", "declared": True})

    def test_present_returns_verbatim_and_fresh(self):
        payload = {"description": "Small audit helper"}
        before = {"description": "Small audit helper"}
        result = run_feature(payload)
        self.assertEqual(result, {"description": "Small audit helper", "declared": True})
        self.assertIs(result["declared"], True)
        self.assertEqual(set(result.keys()), {"description", "declared"})
        self.assertEqual(payload, before)
        self.assertIsNot(result, payload)
        second = run_feature(payload)
        self.assertEqual(second, result)
        self.assertIsNot(second, result)
        self.assertEqual(payload, before)

    def test_whitespace_case_preserved_no_mutation(self):
        text = "  HeLLo \tWoRLd  "
        payload = {"description": text}
        result = run_feature(payload)
        self.assertEqual(result["description"], text)
        self.assertIs(result["declared"], True)
        self.assertEqual(payload, {"description": text})
        result["description"] = "mutated"
        self.assertEqual(payload, {"description": text})
        again = run_feature(payload)
        self.assertEqual(again["description"], text)

    def test_none_returns_false_and_fresh(self):
        payload = {"description": None}
        result = run_feature(payload)
        self.assertEqual(result, {"description": None, "declared": False})
        self.assertIs(result["description"], None)
        self.assertIs(result["declared"], False)
        self.assertEqual(set(result.keys()), {"description", "declared"})
        self.assertIsNot(result, payload)
        second = run_feature(payload)
        self.assertEqual(second, result)
        self.assertIsNot(second, result)
        self.assertEqual(payload, {"description": None})

    def test_empty_overlength_non_str_raise_fixed(self):
        with self.assertRaises(ValueError) as cm:
            run_feature({"description": ""})
        self.assertEqual(str(cm.exception), FIXED)
        long_text = "x" * 513
        with self.assertRaises(ValueError) as cm2:
            run_feature({"description": long_text})
        self.assertEqual(str(cm2.exception), FIXED)
        self.assertNotIn(long_text, str(cm2.exception))
        for bad in [123, 4.5, True, False, [], {}, ("a",), b"hi"]:
            with self.assertRaises(ValueError) as cm3:
                run_feature({"description": bad})
            self.assertEqual(str(cm3.exception), FIXED)

    def test_overlength_with_custom_budget(self):
        with self.assertRaises(ValueError) as cm:
            run_feature({"description": "Hi", "max_length": 1})
        self.assertEqual(str(cm.exception), FIXED)
        ok = run_feature({"description": "Hi", "max_length": 2})
        self.assertEqual(ok, {"description": "Hi", "declared": True})
        with self.assertRaises(ValueError):
            run_feature({"description": "Hello", "max_length": 4})
        ok2 = run_feature({"description": "Hello", "max_length": 5})
        self.assertEqual(ok2["description"], "Hello")

    def test_default_budget_boundary(self):
        edge = "y" * 512
        ok = run_feature({"description": edge})
        self.assertEqual(ok["description"], edge)
        self.assertIs(ok["declared"], True)
        with self.assertRaises(ValueError) as cm:
            run_feature({"description": edge + "y"})
        self.assertEqual(str(cm.exception), FIXED)

    def test_missing_extra_non_dict_raise_fixed(self):
        with self.assertRaises(ValueError) as cm:
            run_feature({})
        self.assertEqual(str(cm.exception), FIXED)
        with self.assertRaises(ValueError) as cm:
            run_feature({"max_length": 10})
        self.assertEqual(str(cm.exception), FIXED)
        with self.assertRaises(ValueError) as cm:
            run_feature({"description": "hi", "extra": 1})
        self.assertEqual(str(cm.exception), FIXED)
        with self.assertRaises(ValueError) as cm:
            run_feature({"description": "hi", "max_length": 4, "extra": 1})
        self.assertEqual(str(cm.exception), FIXED)
        for bad_payload in [None, [], "hi", 123, True, False]:
            with self.assertRaises(ValueError) as cm:
                run_feature(bad_payload)
            self.assertEqual(str(cm.exception), FIXED)

    def test_bad_budget_raises_fixed(self):
        for bad_budget in [True, False, 0, -1, -512, "4", 4.5, None, [], {}, (4,)]:
            with self.assertRaises(ValueError) as cm:
                run_feature({"description": "hi", "max_length": bad_budget})
            self.assertEqual(str(cm.exception), FIXED)

    def test_str_subclass_accepted_verbatim(self):
        class MyStr(str):
            pass
        value = MyStr("  Mixed CASE \n Om")
        payload = {"description": value}
        result = run_feature(payload)
        self.assertEqual(result["description"], "  Mixed CASE \n Om")
        self.assertIs(result["declared"], True)
        self.assertIsInstance(result["description"], str)
        self.assertEqual(payload["description"], value)
        self.assertIs(type(payload["description"]), MyStr)
        self.assertEqual(payload["description"], value)

    def test_deterministic_and_no_shared_mutable_refs(self):
        payload = {"description": "abc", "max_length": 10}
        before = {"description": "abc", "max_length": 10}
        r1 = run_feature(payload)
        r2 = run_feature(payload)
        self.assertEqual(r1, r2)
        self.assertIsNot(r1, r2)
        self.assertIsNot(r1, payload)
        self.assertEqual(payload, before)
        r1["description"] = "changed"
        r1["declared"] = False
        r3 = run_feature(payload)
        self.assertEqual(r3, {"description": "abc", "declared": True})
        self.assertEqual(payload, before)

    def test_error_does_not_echo_input(self):
        secret = "SuperSecretDescriptionXYZ"
        with self.assertRaises(ValueError) as cm:
            run_feature({"description": secret, "max_length": 2})
        self.assertEqual(str(cm.exception), FIXED)
        self.assertNotIn(secret, str(cm.exception))


if __name__ == "__main__":
    unittest.main()
