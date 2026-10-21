import unittest

try:
    from npm_tarball_audit.features.type_declaration_scan import run_feature
except ImportError:
    from src.npm_tarball_audit.features.type_declaration_scan import run_feature

FIXED = "Invalid type scan payload or budget"


class CommunityTypeDeclarationScanTest(unittest.TestCase):
    def assertInvalid(self, payload):
        with self.assertRaises(ValueError) as ctx:
            run_feature(payload)
        self.assertEqual(str(ctx.exception), FIXED)

    def test_module_declared_true_preserves_and_fresh(self):
        payload = {"type": "module"}
        snapshot = {"type": "module"}
        result = run_feature(payload)
        self.assertEqual(result, {"type": "module", "declared": True})
        self.assertEqual(set(result.keys()), {"type", "declared"})
        self.assertTrue(result["declared"] is True)
        self.assertEqual(payload, snapshot)
        second = run_feature(payload)
        self.assertEqual(second, result)
        self.assertIsNot(result, second)
        self.assertIsNot(result["type"], second["type"])
        self.assertIsNot(result["type"], payload["type"])
        self.assertEqual(payload, snapshot)

    def test_commonjs_preserves_verbatim(self):
        payload = {"type": "commonjs"}
        result = run_feature(payload)
        self.assertEqual(result, {"type": "commonjs", "declared": True})
        self.assertTrue(result["declared"] is True)
        self.assertEqual(result["type"], "commonjs")
        self.assertEqual(payload, {"type": "commonjs"})

    def test_none_denotes_absent(self):
        result = run_feature({"type": None})
        self.assertEqual(result, {"type": None, "declared": False})
        self.assertTrue(result["type"] is None)
        self.assertTrue(result["declared"] is False)
        self.assertEqual(set(result.keys()), {"type", "declared"})

    def test_explicit_budget_accepted(self):
        self.assertEqual(
            run_feature({"type": "commonjs", "max_length": 32}),
            {"type": "commonjs", "declared": True},
        )
        self.assertEqual(
            run_feature({"type": "module", "max_length": 32}),
            {"type": "module", "declared": True},
        )

    def test_invalid_shapes(self):
        self.assertInvalid(None)
        self.assertInvalid("module")
        self.assertInvalid(123)
        self.assertInvalid(True)
        self.assertInvalid([])
        self.assertInvalid({})
        self.assertInvalid({"max_length": 32})
        self.assertInvalid({"type": "module", "extra": 1})
        self.assertInvalid({"type": "module", "max_length": 32, "extra": 1})
        self.assertInvalid({"type": "module", "max_length": True})
        self.assertInvalid({"type": "module", "max_length": False})
        self.assertInvalid({"type": "module", "max_length": 0})
        self.assertInvalid({"type": "module", "max_length": -1})
        self.assertInvalid({"type": "module", "max_length": "32"})
        self.assertInvalid({"type": "module", "max_length": 32.0})
        self.assertInvalid({"type": "module", "max_length": None})
        self.assertInvalid({"type": ""})
        self.assertInvalid({"type": "Module"})
        self.assertInvalid({"type": "COMMONJS"})
        self.assertInvalid({"type": "esm"})
        self.assertInvalid({"type": " module"})
        self.assertInvalid({"type": "module "})
        self.assertInvalid({"type": 1})
        self.assertInvalid({"type": True})
        self.assertInvalid({"type": ["module"]})

    def test_budget_counts_code_points_inclusive(self):
        self.assertEqual(
            run_feature({"type": "module", "max_length": 6}),
            {"type": "module", "declared": True},
        )
        self.assertInvalid({"type": "module", "max_length": 5})
        self.assertEqual(
            run_feature({"type": "commonjs", "max_length": 8}),
            {"type": "commonjs", "declared": True},
        )
        self.assertInvalid({"type": "commonjs", "max_length": 7})

    def test_str_subclass_accepted_without_coercion(self):
        class Sub(str):
            pass
        value = Sub("module")
        payload = {"type": value}
        result = run_feature(payload)
        self.assertEqual(result["type"], "module")
        self.assertTrue(result["declared"] is True)
        self.assertIs(type(result["type"]), str)
        self.assertIsNot(result["type"], value)
        self.assertIs(payload["type"], value)
        self.assertIsInstance(payload["type"], Sub)

    def test_deterministic_no_shared_references(self):
        first = run_feature({"type": "module"})
        second = run_feature({"type": "module"})
        self.assertEqual(first, second)
        self.assertIsNot(first, second)
        self.assertIsNot(first["type"], second["type"])


if __name__ == "__main__":
    unittest.main()
