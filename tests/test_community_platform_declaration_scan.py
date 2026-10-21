import unittest

try:
    from npm_tarball_audit.features.platform_declaration_scan import run_feature
except ImportError:
    from src.npm_tarball_audit.features.platform_declaration_scan import run_feature

_MSG = "Invalid platform scan payload or budget"

class CommunityPlatformDeclarationScanTest(unittest.TestCase):
    def test_valid_sorted_count_and_no_mutation(self):
        payload = {"os": ["linux", "darwin"], "cpu": ["x64"]}
        snapshot = {"os": ["linux", "darwin"], "cpu": ["x64"]}
        result = run_feature(payload)
        self.assertEqual(result, {"os": ["darwin", "linux"], "cpu": ["x64"], "count": 3})
        self.assertEqual(payload, snapshot)
        self.assertIsNot(result["os"], payload["os"])
        self.assertIsNot(result["cpu"], payload["cpu"])

    def test_none_os_verbatim_bang_sort(self):
        result = run_feature({"os": None, "cpu": ["arm64", "!x32"]})
        self.assertEqual(result, {"os": [], "cpu": ["!x32", "arm64"], "count": 2})

    def test_none_both_empty(self):
        result = run_feature({"os": None, "cpu": None})
        self.assertEqual(result, {"os": [], "cpu": [], "count": 0})

    def test_invalid_shapes_raise_fixed_message(self):
        bad = []
        bad.append(None)
        bad.append([])
        bad.append("x")
        bad.append(123)
        bad.append({})
        bad.append({"os": ["linux"]})
        bad.append({"cpu": ["x64"]})
        bad.append({"os": None, "cpu": None, "extra": 1})
        bad.append({"os": "linux", "cpu": None})
        bad.append({"os": None, "cpu": "x64"})
        bad.append({"os": ("linux",), "cpu": None})
        bad.append({"os": [123], "cpu": None})
        bad.append({"os": [None], "cpu": None})
        bad.append({"os": [""], "cpu": None})
        bad.append({"os": ["a" * 65], "cpu": None})
        bad.append({"os": ["linux"] * 33, "cpu": None})
        bad.append({"os": None, "cpu": ["x64"] * 33})
        bad.append({"os": None, "cpu": None, "max_entries": 0})
        bad.append({"os": None, "cpu": None, "max_length": -1})
        bad.append({"os": None, "cpu": None, "max_entries": True})
        bad.append({"os": None, "cpu": None, "max_length": False})
        bad.append({"os": None, "cpu": None, "max_entries": "32"})
        bad.append({"os": None, "cpu": None, "max_length": 64.0})
        for payload in bad:
            with self.assertRaises(ValueError) as ctx:
                run_feature(payload)
            self.assertEqual(str(ctx.exception), _MSG)

    def test_subclass_duplicates_case_bang_preserved(self):
        class S(str):
            pass
        payload = {"os": [S("Linux"), S("linux"), S("linux"), S("!linux")], "cpu": [S("X64"), S("x64")]}
        result = run_feature(payload)
        self.assertEqual(result["os"], ["!linux", "Linux", "linux", "linux"])
        self.assertEqual(result["cpu"], ["X64", "x64"])
        self.assertEqual(result["count"], 6)
        self.assertTrue(isinstance(result["os"][1], S))
        self.assertTrue(isinstance(result["cpu"][0], S))

    def test_custom_budgets_enforced(self):
        ok = run_feature({"os": ["ab", "cd"], "cpu": ["ef"], "max_entries": 2, "max_length": 2})
        self.assertEqual(ok["count"], 3)
        with self.assertRaises(ValueError) as ctx1:
            run_feature({"os": ["ab", "cd", "ef"], "cpu": [], "max_entries": 2, "max_length": 10})
        self.assertEqual(str(ctx1.exception), _MSG)
        with self.assertRaises(ValueError) as ctx2:
            run_feature({"os": ["abcd"], "cpu": [], "max_entries": 32, "max_length": 3})
        self.assertEqual(str(ctx2.exception), _MSG)

    def test_repeated_calls_fresh_containers(self):
        payload = {"os": ["linux", "darwin"], "cpu": ["x64"]}
        first = run_feature(payload)
        second = run_feature(payload)
        self.assertEqual(first, second)
        self.assertIsNot(first, second)
        self.assertIsNot(first["os"], second["os"])
        self.assertIsNot(first["cpu"], second["cpu"])
        self.assertIsNot(first["os"], payload["os"])
        first["os"].append("mut")
        first["cpu"].append("mut")
        self.assertEqual(second, {"os": ["darwin", "linux"], "cpu": ["x64"], "count": 3})
        self.assertEqual(payload, {"os": ["linux", "darwin"], "cpu": ["x64"]})

if __name__ == "__main__":
    unittest.main()
