import unittest
try:
    from npm_tarball_audit.features.packagemanager_declaration_scan import run_feature
except ImportError:
    from src.npm_tarball_audit.features.packagemanager_declaration_scan import run_feature

_FIXED = "Invalid packageManager scan payload or budget"


class PackageManagerDeclarationScanTest(unittest.TestCase):
    def test_absent_returns_not_declared(self):
        payload = {"packageManager": None}
        before = {"packageManager": None}
        out = run_feature(payload)
        self.assertEqual(out, {"declared": False, "value": None})
        self.assertEqual(set(out.keys()), {"declared", "value"})
        self.assertEqual(payload, before)
        again = run_feature({"packageManager": None})
        self.assertEqual(again, out)
        self.assertIsNot(again, out)

    def test_present_preserves_verbatim(self):
        payload = {"packageManager": "npm@10.8.2"}
        before = {"packageManager": "npm@10.8.2"}
        out = run_feature(payload)
        self.assertEqual(out, {"declared": True, "value": "npm@10.8.2"})
        self.assertEqual(payload, before)

    def test_budget_respected(self):
        out = run_feature({"packageManager": "pnpm@9.1.0", "max_length": 256})
        self.assertEqual(out, {"declared": True, "value": "pnpm@9.1.0"})
        with self.assertRaises(ValueError) as ctx:
            run_feature({"packageManager": "x" * 257, "max_length": 256})
        self.assertEqual(str(ctx.exception), _FIXED)
        with self.assertRaises(ValueError) as ctx:
            run_feature({"packageManager": "pnpm@9.1.0", "max_length": 0})
        self.assertEqual(str(ctx.exception), _FIXED)
        with self.assertRaises(ValueError) as ctx:
            run_feature({"packageManager": "pnpm@9.1.0", "max_length": 4097})
        self.assertEqual(str(ctx.exception), _FIXED)

    def test_rejects_malformed_payloads(self):
        bad_payloads = [None, [], "npm@10.8.2", 1, True, {}, {"max_length": 256}, {"packageManager": "npm@1.0.0", "extra": 1}]
        for bad in bad_payloads:
            with self.subTest(bad=repr(bad)):
                with self.assertRaises(ValueError) as ctx:
                    run_feature(bad)
                self.assertEqual(str(ctx.exception), _FIXED)
        for bad_value in [1, 0, True, False, ["npm"], {"x": 1}, 1.5]:
            with self.subTest(bad_value=repr(bad_value)):
                with self.assertRaises(ValueError) as ctx:
                    run_feature({"packageManager": bad_value})
                self.assertEqual(str(ctx.exception), _FIXED)
        for bad_budget in [True, False, "256", 1.0, None, [], {}, 0, -1, 4097]:
            with self.subTest(bad_budget=repr(bad_budget)):
                with self.assertRaises(ValueError) as ctx:
                    run_feature({"packageManager": "npm@1.0.0", "max_length": bad_budget})
                self.assertEqual(str(ctx.exception), _FIXED)

    def test_character_and_length_rules(self):
        with self.assertRaises(ValueError) as ctx:
            run_feature({"packageManager": ""})
        self.assertEqual(str(ctx.exception), _FIXED)
        for bad in ["a\x00b", "a\x07b", "a\x1fb", "a\x08b", "\ud800", "\udc00"]:
            with self.subTest(bad=repr(bad)):
                with self.assertRaises(ValueError) as ctx:
                    run_feature({"packageManager": bad})
                self.assertEqual(str(ctx.exception), _FIXED)

    def test_lf_cr_tab_preserved(self):
        for text in ["a\nb", "a\rb", "a\tb", "a\n\r\tb"]:
            with self.subTest(text=repr(text)):
                payload = {"packageManager": text}
                before = {"packageManager": text}
                out = run_feature(payload)
                self.assertEqual(out, {"declared": True, "value": text})
                self.assertEqual(payload, before)

    def test_str_subclass_accepted(self):
        SubStr = type("SubStr", (str,), {})
        payload = {"packageManager": SubStr("yarn@4.0.0")}
        out = run_feature(payload)
        self.assertEqual(out, {"declared": True, "value": "yarn@4.0.0"})
        self.assertTrue(isinstance(out["value"], str))

    def test_pure_deterministic_fresh_containers(self):
        first = run_feature({"packageManager": "npm@10.8.2"})
        second = run_feature({"packageManager": "npm@10.8.2"})
        self.assertEqual(first, second)
        self.assertIsNot(first, second)
        first["declared"] = "mutated"
        self.assertNotEqual(first, second)
        third = run_feature({"packageManager": "npm@10.8.2"})
        self.assertEqual(third, second)

    def test_error_text_has_no_echo(self):
        with self.assertRaises(ValueError) as ctx:
            run_feature({"packageManager": 1})
        self.assertEqual(str(ctx.exception), _FIXED)
        with self.assertRaises(ValueError) as ctx:
            run_feature({"packageManager": True})
        self.assertEqual(str(ctx.exception), _FIXED)


if __name__ == "__main__":
    unittest.main()
