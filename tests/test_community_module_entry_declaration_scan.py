import unittest

try:
    from src.npm_tarball_audit.features.module_entry_declaration_scan import run_feature
except ImportError:
    from npm_tarball_audit.features.module_entry_declaration_scan import run_feature


class TestCommunityModuleEntryDeclarationScan(unittest.TestCase):
    FIXED = "Invalid module entry scan payload or budget"

    def assertFixedError(self, payload):
        with self.assertRaises(ValueError) as ctx:
            run_feature(payload)
        self.assertEqual(str(ctx.exception), self.FIXED)

    def test_absent_none(self):
        payload = {"module": None}
        snapshot = dict(payload)
        result = run_feature(payload)
        self.assertEqual(result, {"declared": False, "value": None})
        self.assertEqual(set(result.keys()), {"declared", "value"})
        self.assertIs(result["declared"], False)
        self.assertIsNone(result["value"])
        self.assertEqual(payload, snapshot)

    def test_present_string_verbatim(self):
        for text in ["dist/esm/index.js", "Dist/ESM/Index.JS", "  lib/module.js  ", "lib/MODULE.js"]:
            with self.subTest(text=text):
                payload = {"module": text}
                snapshot = dict(payload)
                result = run_feature(payload)
                self.assertEqual(result, {"declared": True, "value": text})
                self.assertIs(result["declared"], True)
                self.assertEqual(result["value"], text)
                self.assertIs(type(result["value"]), str)
                self.assertEqual(payload, snapshot)

    def test_contract_examples(self):
        self.assertEqual(run_feature({"module": None}), {"declared": False, "value": None})
        self.assertEqual(run_feature({"module": "dist/esm/index.js"}), {"declared": True, "value": "dist/esm/index.js"})
        self.assertEqual(run_feature({"max_length": 512, "module": "lib/module.js"}), {"declared": True, "value": "lib/module.js"})

    def test_custom_max_length_enforced(self):
        self.assertEqual(run_feature({"module": "abc", "max_length": 3}), {"declared": True, "value": "abc"})
        self.assertEqual(run_feature({"module": None, "max_length": 10}), {"declared": False, "value": None})
        self.assertEqual(run_feature({"module": "a", "max_length": 1}), {"declared": True, "value": "a"})
        long_value = "x" * 1024
        self.assertEqual(run_feature({"module": long_value, "max_length": 1024}), {"declared": True, "value": long_value})
        self.assertFixedError({"module": "abcd", "max_length": 3})
        self.assertFixedError({"module": "ab", "max_length": 1})

    def test_wrong_budget_types_and_range(self):
        for bad in [True, False, 0, -1, 1025, 2048, 1.0, 512.0, "512", None, [], {}, (512,)]:
            with self.subTest(bad=bad):
                self.assertFixedError({"module": "a", "max_length": bad})
                self.assertFixedError({"module": None, "max_length": bad})

    def test_non_dict_missing_extra(self):
        for bad in [None, [], {}, "module", 123, 1.5, True, ("module",)]:
            with self.subTest(bad=bad):
                self.assertFixedError(bad)
        self.assertFixedError({})
        self.assertFixedError({"max_length": 10})
        self.assertFixedError({"module": None, "extra": 1})
        self.assertFixedError({"module": "a", "max_length": 10, "extra": 1})
        self.assertFixedError({"module": None, "max_length": 10, "other": None})
        self.assertFixedError({"MODULE": "a"})

    def test_non_string_module_types(self):
        for bad in [0, 1, True, False, 1.5, [], {}, ("a",), 123]:
            with self.subTest(bad=bad):
                self.assertFixedError({"module": bad})

    def test_empty_and_overlength(self):
        self.assertFixedError({"module": ""})
        self.assertFixedError({"module": "a" * 513})
        self.assertFixedError({"module": "a" * 1025, "max_length": 1024})
        ok = "b" * 512
        result = run_feature({"module": ok})
        self.assertEqual(result["value"], ok)

    def test_fresh_dict_no_sharing(self):
        payload = {"module": "lib/module.js"}
        r1 = run_feature(payload)
        r2 = run_feature(payload)
        self.assertIsNot(r1, r2)
        self.assertEqual(r1, r2)
        self.assertEqual(set(r1.keys()), {"declared", "value"})
        self.assertEqual(set(r2.keys()), {"declared", "value"})
        self.assertIsNot(r1, payload)
        payload2 = {"module": None}
        n1 = run_feature(payload2)
        n2 = run_feature(payload2)
        self.assertIsNot(n1, n2)
        self.assertEqual(n1, n2)

    def test_str_subclass_accepted_as_plain(self):
        class Sub(str):
            pass
        original = Sub("dist/esm/index.js")
        payload = {"module": original}
        result = run_feature(payload)
        self.assertTrue(result["declared"])
        self.assertEqual(result["value"], "dist/esm/index.js")
        self.assertIs(type(result["value"]), str)
        self.assertIsNot(type(result["value"]), Sub)
        self.assertIs(type(payload["module"]), Sub)
        padded = Sub("  Keep/Case.JS  ")
        result2 = run_feature({"module": padded})
        self.assertEqual(result2["value"], "  Keep/Case.JS  ")
        self.assertIs(type(result2["value"]), str)

    def test_error_does_not_echo_input(self):
        evil = "SECRET-EVIL-VALUE-12345"
        with self.assertRaises(ValueError) as ctx:
            run_feature({"module": evil, "max_length": 3})
        msg = str(ctx.exception)
        self.assertEqual(msg, self.FIXED)
        self.assertNotIn(evil, msg)
        with self.assertRaises(ValueError) as ctx2:
            run_feature({"module": "", "extra-evil": evil})
        self.assertNotIn(evil, str(ctx2.exception))


if __name__ == "__main__":
    unittest.main()
