import unittest
from npm_tarball_audit.features.integrity_token_scan import run_feature

VALID_TOKEN = "sha512-ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/ABCDEFGHIJKLMNOPQRSTUV=="
ERROR_TEXT = "Invalid integrity scan payload or budget"

class IntegrityTokenScanCommunityTest(unittest.TestCase):
    def test_absent_none_default_leaves_input_unchanged(self):
        payload = {"integrity": None}
        snapshot = dict(payload)
        result = run_feature(payload)
        self.assertEqual(result, {"valid": False, "kind": "absent", "token": None})
        self.assertEqual(set(result.keys()), {"valid", "kind", "token"})
        self.assertEqual(payload, snapshot)

    def test_valid_token_verbatim(self):
        self.assertEqual(len(VALID_TOKEN), 95)
        result = run_feature({"integrity": VALID_TOKEN})
        self.assertEqual(result, {"valid": True, "kind": "string", "token": VALID_TOKEN})
        self.assertEqual(set(result.keys()), {"valid", "kind", "token"})

    def test_valid_str_subclass(self):
        class MyStr(str):
            pass
        token = MyStr(VALID_TOKEN)
        result = run_feature({"integrity": token})
        self.assertEqual(result["valid"], True)
        self.assertEqual(result["kind"], "string")
        self.assertEqual(result["token"], VALID_TOKEN)
        self.assertEqual(set(result.keys()), {"valid", "kind", "token"})

    def test_invalid_strings_without_error(self):
        cases = [
            {"integrity": "sha384-abc"},
            {"integrity": "sha512-abc"},
            {"integrity": ""},
            {"integrity": "x" * 129},
            {"integrity": "sha512-" + "A" * 87 + "="},
            {"integrity": VALID_TOKEN + " "},
            {"integrity": " " + VALID_TOKEN},
            {"integrity": VALID_TOKEN + "\n"},
            {"integrity": "sha512-" + "A" * 85 + "!" + "=="},
            {"integrity": "sha512-" + "A" * 86 + "="},
            {"integrity": "\u00e9" + VALID_TOKEN[1:]},
        ]
        for payload in cases:
            with self.subTest(payload=repr(payload)[0:40]):
                result = run_feature(dict(payload))
                self.assertEqual(result["valid"], False)
                self.assertEqual(result["kind"], "string")
                self.assertIsNone(result["token"])
                self.assertEqual(set(result.keys()), {"valid", "kind", "token"})

    def test_over_length_with_small_budget(self):
        result = run_feature({"integrity": VALID_TOKEN, "max_length": 10})
        self.assertEqual(result, {"valid": False, "kind": "string", "token": None})

    def test_invalid_payloads_raise_fixed_error(self):
        bad_payloads = [
            {},
            {"max_length": 128},
            {"integrity": None, "extra": 1},
            {"integrity": VALID_TOKEN, "max_length": 128, "x": 1},
            None,
            [],
            "x",
            123,
            True,
            {"integrity": 123},
            {"integrity": True},
            {"integrity": 3.14},
            {"integrity": []},
            {"integrity": {}},
            {"integrity": None, "max_length": 0},
            {"integrity": None, "max_length": -1},
            {"integrity": None, "max_length": True},
            {"integrity": None, "max_length": False},
            {"integrity": None, "max_length": "128"},
            {"integrity": None, "max_length": 1.5},
            {"integrity": None, "max_length": None},
            {"integrity": VALID_TOKEN, "max_length": 0},
        ]
        for payload in bad_payloads:
            with self.subTest(payload=repr(payload)[0:40]):
                with self.assertRaises(ValueError) as ctx:
                    run_feature(payload)
                self.assertEqual(str(ctx.exception), ERROR_TEXT)

    def test_repeated_calls_equal_and_fresh(self):
        first = run_feature({"integrity": VALID_TOKEN})
        second = run_feature({"integrity": VALID_TOKEN})
        self.assertEqual(first, second)
        self.assertIsNot(first, second)
        self.assertEqual(set(first.keys()), {"valid", "kind", "token"})
        first["valid"] = not first["valid"]
        third = run_feature({"integrity": VALID_TOKEN})
        self.assertEqual(third, second)
        absent_first = run_feature({"integrity": None})
        absent_second = run_feature({"integrity": None})
        self.assertEqual(absent_first, absent_second)
        self.assertIsNot(absent_first, absent_second)

if __name__ == "__main__":
    unittest.main()
