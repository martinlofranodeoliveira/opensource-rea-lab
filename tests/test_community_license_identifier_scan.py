import unittest

try:
    from npm_tarball_audit.features.license_identifier_scan import run_feature
except ImportError:
    from src.npm_tarball_audit.features.license_identifier_scan import run_feature

_ERROR = "Invalid license scan payload or budget"


class TestLicenseIdentifierScan(unittest.TestCase):
    def test_mit_valid(self):
        payload = {"license": "MIT"}
        before = {"license": "MIT"}
        result = run_feature(payload)
        self.assertEqual(result, {"valid": True, "kind": "string", "identifier": "MIT"})
        self.assertEqual(payload, before)
        second = run_feature({"license": "MIT"})
        self.assertEqual(second, result)
        self.assertIsNot(result, second)

    def test_apache_valid_preserves_case(self):
        result = run_feature({"license": "Apache-2.0"})
        self.assertEqual(result["valid"], True)
        self.assertEqual(result["kind"], "string")
        self.assertEqual(result["identifier"], "Apache-2.0")

    def test_isc_valid(self):
        result = run_feature({"license": "ISC"})
        self.assertEqual(result, {"valid": True, "kind": "string", "identifier": "ISC"})

    def test_none_absent(self):
        result = run_feature({"license": None})
        self.assertEqual(result, {"valid": False, "kind": "absent", "identifier": None})
        second = run_feature({"license": None})
        self.assertEqual(second, result)
        self.assertIsNot(result, second)

    def test_error_cases(self):
        bad_payloads = [
            {},
            {"licence": "MIT"},
            {"license": "MIT", "extra": 1},
            {"license": "MIT", "max_length": 64, "extra": 1},
            [],
            None,
            "MIT",
            123,
            {"license": 123},
            {"license": True},
            {"license": False},
            {"license": 3.14},
            {"license": ["MIT"]},
            {"license": {"x": 1}},
            {"license": b"MIT"},
            {"license": "MIT", "max_length": True},
            {"license": "MIT", "max_length": False},
            {"license": "MIT", "max_length": 0},
            {"license": "MIT", "max_length": -1},
            {"license": "MIT", "max_length": -64},
            {"license": "MIT", "max_length": "64"},
            {"license": "MIT", "max_length": 64.0},
            {"license": "MIT", "max_length": None},
            {"license": "MIT", "max_length": [64]},
            {"license": None, "max_length": 0},
            {"license": None, "max_length": True},
        ]
        for payload in bad_payloads:
            with self.subTest(payload=repr(payload)):
                with self.assertRaises(ValueError) as ctx:
                    run_feature(payload)
                self.assertEqual(str(ctx.exception), _ERROR)

    def test_invalid_strings(self):
        bad = [
            "",
            "-MIT",
            ".MIT",
            "+MIT",
            "MIT-",
            "MIT.",
            "MIT+",
            "-" ,
            ".",
            "MIT License",
            " MIT",
            "MIT ",
            " MIT ",
            "Apache 2.0",
            "MIT/Apache",
            "MIT:foo",
            "MIT;foo",
            "MIT_foo",
            "M\u00fcnich",
            "\u00c5BC",
            "\u65e5\u672c\u8a9e",
            "Apache-2.0/",
            "/MIT",
        ]
        for value in bad:
            with self.subTest(value=value):
                payload = {"license": value}
                snapshot = {"license": value}
                result = run_feature(payload)
                self.assertEqual(result, {"valid": False, "kind": "string", "identifier": None})
                self.assertEqual(payload, snapshot)

    def test_over_length(self):
        long_value = "A" * 65
        result = run_feature({"license": long_value})
        self.assertEqual(result, {"valid": False, "kind": "string", "identifier": None})
        result2 = run_feature({"license": "MIT", "max_length": 2})
        self.assertEqual(result2, {"valid": False, "kind": "string", "identifier": None})
        result3 = run_feature({"license": "MIT", "max_length": 3})
        self.assertEqual(result3["valid"], True)
        self.assertEqual(result3["identifier"], "MIT")

    def test_no_mutation_and_fresh_containers(self):
        payload = {"license": "MIT"}
        r1 = run_feature(payload)
        r2 = run_feature(payload)
        self.assertIsNot(r1, r2)
        self.assertEqual(r1, r2)
        r1["valid"] = "mutated"
        self.assertNotEqual(r1, r2)
        fresh = run_feature({"license": "MIT"})
        self.assertEqual(fresh["valid"], True)
        self.assertEqual(payload, {"license": "MIT"})

    def test_syntax_only_no_registry_claim(self):
        result = run_feature({"license": "NotASPDX-XYZ-123"})
        self.assertEqual(result["valid"], True)
        self.assertEqual(result["kind"], "string")
        self.assertEqual(result["identifier"], "NotASPDX-XYZ-123")
        single = run_feature({"license": "A"})
        self.assertEqual(single["valid"], True)


if __name__ == "__main__":
    unittest.main()
