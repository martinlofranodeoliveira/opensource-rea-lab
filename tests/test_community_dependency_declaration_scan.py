import unittest

try:
    from npm_tarball_audit.features.dependency_declaration_scan import run_feature
except ImportError:
    from src.npm_tarball_audit.features.dependency_declaration_scan import run_feature

EXPECTED = "Invalid dependency scan payload or budget"


class DependencyDeclarationScanTest(unittest.TestCase):
    def check_invalid(self, payload):
        try:
            run_feature(payload)
        except ValueError as err:
            self.assertEqual(str(err), EXPECTED)
            return
        self.fail("ValueError not raised")

    def check_invalid_no_echo(self, payload, marker):
        try:
            run_feature(payload)
        except ValueError as err:
            self.assertEqual(str(err), EXPECTED)
            self.assertNotIn(marker, str(err))
            return
        self.fail("ValueError not raised")

    def test_none_returns_empty(self):
        result = run_feature({"dependencies": None})
        self.assertEqual(result, {"dependencies": [], "count": 0})
        self.assertEqual(set(result), {"dependencies", "count"})

    def test_contract_examples(self):
        out = run_feature({"dependencies": {"lodash": "^4.17.21", "react": "18.2.0"}})
        self.assertEqual(out["count"], 2)
        self.assertEqual(out["dependencies"], [{"name": "lodash", "spec": "^4.17.21"}, {"name": "react", "spec": "18.2.0"}])
        self.assertEqual(run_feature({"dependencies": None}), {"dependencies": [], "count": 0})
        self.assertEqual(run_feature({"dependencies": {"left-pad": "1.3.0"}}), {"dependencies": [{"name": "left-pad", "spec": "1.3.0"}], "count": 1})

    def test_unsorted_sorted_verbatim(self):
        payload = {"dependencies": {"b": "2.0.0", "A": "1.0.0", "a": "^3.0.0", "React": "x"}}
        result = run_feature(payload)
        self.assertEqual(result["count"], 4)
        names = [r["name"] for r in result["dependencies"]]
        self.assertEqual(names, ["A", "React", "a", "b"])
        self.assertEqual(result["dependencies"][1], {"name": "React", "spec": "x"})

    def test_str_subclass_accepted(self):
        class S(str):
            pass
        payload = {"dependencies": {S("pkg"): S("^1.0.0")}}
        result = run_feature(payload)
        self.assertEqual(result["count"], 1)
        self.assertEqual(result["dependencies"][0]["name"], "pkg")

    def test_missing_extra_and_types(self):
        self.check_invalid({})
        self.check_invalid({"dependencies": {"a": "1"}, "extra": 1})
        self.check_invalid([])
        self.check_invalid(None)
        self.check_invalid("x")
        self.check_invalid({"dependencies": ["a"]})
        self.check_invalid({"dependencies": "a"})
        self.check_invalid({"dependencies": 123})
        self.check_invalid({"dependencies": {"a": 1}})
        self.check_invalid({"dependencies": {1: "1"}})
        self.check_invalid({"dependencies": {"": "1"}})
        self.check_invalid({"dependencies": {"a": ""}})
        self.check_invalid({"dependencies": {"a": None}})

    def test_budgets_rejected(self):
        self.check_invalid({"dependencies": {}, "max_entries": True})
        self.check_invalid({"dependencies": {}, "max_length": False})
        self.check_invalid({"dependencies": {}, "max_entries": 0})
        self.check_invalid({"dependencies": {}, "max_length": -1})
        self.check_invalid({"dependencies": {}, "max_entries": 1.5})
        self.check_invalid({"dependencies": {}, "max_length": "8"})
        self.check_invalid({"dependencies": {}, "max_entries": None})

    def test_over_length_rejected(self):
        self.check_invalid({"dependencies": {"abcd": "1"}, "max_length": 3})
        self.check_invalid({"dependencies": {"a": "abcd"}, "max_length": 3})
        long_name = "x" * 1025
        self.check_invalid({"dependencies": {long_name: "1"}})

    def test_max_entries_exceeded(self):
        self.check_invalid({"dependencies": {"a": "1", "b": "2"}, "max_entries": 1})

    def test_custom_budgets_accepted(self):
        result = run_feature({"dependencies": {"a": "1"}, "max_entries": 1, "max_length": 5})
        self.assertEqual(result["count"], 1)

    def test_input_not_mutated_and_fresh(self):
        payload = {"dependencies": {"b": "2", "a": "1"}}
        snapshot = {"dependencies": {"b": "2", "a": "1"}}
        r1 = run_feature(payload)
        self.assertEqual(payload, snapshot)
        r2 = run_feature(payload)
        self.assertEqual(r1, r2)
        self.assertIsNot(r1, r2)
        self.assertIsNot(r1["dependencies"], r2["dependencies"])
        self.assertIsNot(r1["dependencies"][0], r2["dependencies"][0])
        r1["dependencies"].append({"name": "evil", "spec": "9"})
        r1["count"] = 99
        r3 = run_feature(payload)
        self.assertEqual(r3["count"], 2)
        self.assertEqual(len(r3["dependencies"]), 2)
        none_payload = {"dependencies": None}
        n1 = run_feature(none_payload)
        n2 = run_feature(none_payload)
        self.assertIsNot(n1["dependencies"], n2["dependencies"])

    def test_error_no_echo(self):
        marker = "marker-xyz-123"
        self.check_invalid_no_echo({"dependencies": {marker: "1"}, "bogus": 1}, marker)
        self.check_invalid_no_echo({"dependencies": {marker: "1"}, "max_entries": 0}, marker)

    def test_deterministic(self):
        payload = {"dependencies": {"b": "2", "a": "1"}}
        first = run_feature(payload)
        second = run_feature(payload)
        self.assertEqual(first, second)


if __name__ == "__main__":
    unittest.main()
