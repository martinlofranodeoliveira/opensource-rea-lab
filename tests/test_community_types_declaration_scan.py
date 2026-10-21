import unittest

try:
    from src.npm_tarball_audit.features.types_declaration_scan import run_feature
except ImportError:
    from npm_tarball_audit.features.types_declaration_scan import run_feature

FIXED = "Invalid types scan payload or budget"


class TestTypesDeclarationScan(unittest.TestCase):
    def test_both_none(self):
        payload = {"types": None, "typings": None}
        result = run_feature(payload)
        self.assertEqual(result, {"types": None, "typings": None, "declared": False})
        self.assertEqual(set(result.keys()), {"types", "typings", "declared"})
        self.assertIsNone(result["types"])
        self.assertIsNone(result["typings"])
        self.assertIs(result["declared"], False)
        self.assertEqual(payload, {"types": None, "typings": None})
        self.assertIsNot(result, payload)

    def test_types_present_verbatim(self):
        value = "  ./Dist/INDEX.d.TS  "
        payload = {"types": value, "typings": None}
        result = run_feature(payload)
        self.assertEqual(result["types"], value)
        self.assertIsNone(result["typings"])
        self.assertIs(result["declared"], True)
        self.assertEqual(payload, {"types": value, "typings": None})

    def test_typings_present_verbatim(self):
        value = "./lib/main.d.ts"
        payload = {"types": None, "typings": value}
        result = run_feature(payload)
        self.assertIsNone(result["types"])
        self.assertEqual(result["typings"], value)
        self.assertIs(result["declared"], True)
        self.assertEqual(payload, {"types": None, "typings": value})

    def test_both_present(self):
        payload = {"types": "./dist/index.d.ts", "typings": "./lib/main.d.ts"}
        result = run_feature(payload)
        self.assertEqual(result["types"], "./dist/index.d.ts")
        self.assertEqual(result["typings"], "./lib/main.d.ts")
        self.assertIs(result["declared"], True)
        self.assertEqual(payload, {"types": "./dist/index.d.ts", "typings": "./lib/main.d.ts"})

    def test_contract_examples(self):
        self.assertEqual(
            run_feature({"types": "./dist/index.d.ts", "typings": None}),
            {"types": "./dist/index.d.ts", "typings": None, "declared": True},
        )
        self.assertEqual(
            run_feature({"types": None, "typings": None}),
            {"types": None, "typings": None, "declared": False},
        )
        self.assertEqual(
            run_feature({"types": None, "typings": "./lib/main.d.ts"}),
            {"types": None, "typings": "./lib/main.d.ts", "declared": True},
        )

    def test_rejects_bad_payloads(self):
        long_value = "x" * 513
        bad = [
            None,
            [],
            "x",
            123,
            True,
            False,
            {},
            {"types": None},
            {"typings": None},
            {"types": None, "typings": None, "extra": 1},
            {"types": None, "typings": None, "max_length": 512, "extra": None},
            {"types": 0, "typings": None},
            {"types": 1, "typings": None},
            {"types": True, "typings": None},
            {"types": False, "typings": None},
            {"types": 123, "typings": None},
            {"types": [], "typings": None},
            {"types": {}, "typings": None},
            {"types": None, "typings": 0},
            {"types": None, "typings": 1},
            {"types": None, "typings": True},
            {"types": None, "typings": ["x"]},
            {"types": None, "typings": {}},
            {"types": "", "typings": None},
            {"types": None, "typings": ""},
            {"types": long_value, "typings": None},
            {"types": None, "typings": long_value},
            {"types": None, "typings": None, "max_length": 0},
            {"types": None, "typings": None, "max_length": -1},
            {"types": None, "typings": None, "max_length": True},
            {"types": None, "typings": None, "max_length": False},
            {"types": None, "typings": None, "max_length": "512"},
            {"types": None, "typings": None, "max_length": 1.5},
            {"types": None, "typings": None, "max_length": None},
            {"types": None, "typings": None, "max_length": []},
        ]
        for index in range(len(bad)):
            payload = bad[index]
            with self.subTest(index=index):
                with self.assertRaises(ValueError) as ctx:
                    run_feature(payload)
                self.assertEqual(str(ctx.exception), FIXED)

    def test_error_does_not_echo_input(self):
        secret = "SECRET-UNIQUE-VALUE-XYZ"
        with self.assertRaises(ValueError) as ctx:
            run_feature({"types": secret, "typings": None, "max_length": 1})
        self.assertEqual(str(ctx.exception), FIXED)
        self.assertNotIn(secret, str(ctx.exception))
        with self.assertRaises(ValueError) as ctx2:
            run_feature({"types": None, "typings": None, "max_length": 0})
        self.assertEqual(str(ctx2.exception), FIXED)

    def test_custom_budget(self):
        self.assertEqual(
            run_feature({"types": "abcde", "typings": None, "max_length": 5})["types"],
            "abcde",
        )
        with self.assertRaises(ValueError) as ctx:
            run_feature({"types": "abcdef", "typings": None, "max_length": 5})
        self.assertEqual(str(ctx.exception), FIXED)

    def test_str_subclass_no_coercion(self):
        class MyStr(str):
            pass
        value = MyStr("./dist/custom.d.ts")
        payload = {"types": value, "typings": None}
        result = run_feature(payload)
        self.assertEqual(result["types"], "./dist/custom.d.ts")
        self.assertIsInstance(result["types"], str)
        self.assertIs(result["declared"], True)
        self.assertIs(payload["types"], value)
        self.assertEqual(payload["types"], "./dist/custom.d.ts")
        value2 = MyStr("./lib/other.d.ts")
        result2 = run_feature({"types": None, "typings": value2})
        self.assertEqual(result2["typings"], "./lib/other.d.ts")
        self.assertIsInstance(result2["typings"], str)
        self.assertIs(result2["declared"], True)

    def test_fresh_containers_and_no_mutation(self):
        payload = {"types": "./a.d.ts", "typings": None}
        first = run_feature(payload)
        second = run_feature(payload)
        self.assertEqual(payload, {"types": "./a.d.ts", "typings": None})
        self.assertIsNot(first, second)
        self.assertEqual(first, second)
        first["types"] = "mutated"
        self.assertNotEqual(first, second)
        self.assertEqual(payload, {"types": "./a.d.ts", "typings": None})
        self.assertEqual(second, {"types": "./a.d.ts", "typings": None, "declared": True})

    def test_whitespace_case_preserved(self):
        value = " \t./A/B.D.TS\n "
        result = run_feature({"types": value, "typings": None})
        self.assertEqual(result["types"], value)
        self.assertEqual(len(result["types"]), len(value))


if __name__ == "__main__":
    unittest.main()
