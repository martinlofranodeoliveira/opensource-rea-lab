import copy
import unittest

try:
    from npm_tarball_audit.features.directories_declaration_scan import run_feature
except ImportError:
    from src.npm_tarball_audit.features.directories_declaration_scan import run_feature

EXPECTED = "Invalid directories scan payload or budget"


class TestDirectoriesDeclarationScan(unittest.TestCase):
    def test_absent_none(self):
        payload = {"directories": None}
        before = copy.deepcopy(payload)
        out = run_feature(payload)
        self.assertEqual(out, {"entries": None, "declared": False})
        self.assertIsNone(out["entries"])
        self.assertFalse(out["declared"])
        self.assertEqual(set(out.keys()), {"entries", "declared"})
        self.assertEqual(payload, before)

    def test_absent_none_with_budgets(self):
        payload = {"directories": None, "max_entries": 2, "max_length": 10}
        out = run_feature(payload)
        self.assertEqual(out, {"entries": None, "declared": False})

    def test_empty_dict(self):
        payload = {"directories": {}}
        out = run_feature(payload)
        self.assertEqual(out, {"entries": [], "declared": True})
        self.assertTrue(out["declared"])
        self.assertIsInstance(out["entries"], list)

    def test_empty_fresh_containers(self):
        payload = {"directories": {}}
        r1 = run_feature(payload)
        r2 = run_feature(payload)
        self.assertIsNot(r1, r2)
        self.assertIsNot(r1["entries"], r2["entries"])
        self.assertEqual(r1, r2)

    def test_valid_sorted_verbatim(self):
        payload = {"directories": {"lib": "lib", "doc": "docs"}}
        before = copy.deepcopy(payload)
        out = run_feature(payload)
        self.assertTrue(out["declared"])
        self.assertEqual(out["entries"], [{"key": "doc", "value": "docs"}, {"key": "lib", "value": "lib"}])
        self.assertEqual(set(out.keys()), {"entries", "declared"})
        for e in out["entries"]:
            self.assertEqual(set(e.keys()), {"key", "value"})
        self.assertEqual(payload, before)

    def test_verbatim_spacing_preserved(self):
        payload = {"directories": {"lib": "  lib/  "}}
        out = run_feature(payload)
        self.assertEqual(out["entries"], [{"key": "lib", "value": "  lib/  "}])

    def test_all_roles_sorted(self):
        payload = {"directories": {"test": "t", "example": "e", "doc": "d", "man": "m", "bin": "b", "lib": "l"}}
        out = run_feature(payload)
        keys = [e["key"] for e in out["entries"]]
        self.assertEqual(keys, ["bin", "doc", "example", "lib", "man", "test"])

    def test_case_sensitive_rejected(self):
        with self.assertRaises(ValueError) as cm:
            run_feature({"directories": {"Lib": "x"}})
        self.assertEqual(str(cm.exception), EXPECTED)

    def test_unknown_role_no_echo(self):
        evil = "EVILROLE999"
        with self.assertRaises(ValueError) as cm:
            run_feature({"directories": {evil: "x"}})
        self.assertEqual(str(cm.exception), EXPECTED)
        self.assertNotIn(evil, str(cm.exception))

    def test_non_string_value(self):
        for bad in (123, 0, 1, True, False, None, [], {}):
            with self.assertRaises(ValueError) as cm:
                run_feature({"directories": {"lib": bad}})
            self.assertEqual(str(cm.exception), EXPECTED)

    def test_empty_value(self):
        with self.assertRaises(ValueError) as cm:
            run_feature({"directories": {"lib": ""}})
        self.assertEqual(str(cm.exception), EXPECTED)

    def test_over_length_default(self):
        long_val = "a" * 513
        with self.assertRaises(ValueError) as cm:
            run_feature({"directories": {"lib": long_val}})
        self.assertEqual(str(cm.exception), EXPECTED)
        ok_val = "a" * 512
        ok = run_feature({"directories": {"lib": ok_val}})
        self.assertEqual(ok["entries"][0]["value"], ok_val)

    def test_custom_length_boundary(self):
        with self.assertRaises(ValueError) as cm:
            run_feature({"directories": {"lib": "abcd"}, "max_length": 3})
        self.assertEqual(str(cm.exception), EXPECTED)
        ok = run_feature({"directories": {"lib": "abc"}, "max_length": 3})
        self.assertEqual(ok["entries"], [{"key": "lib", "value": "abc"}])

    def test_over_count_custom(self):
        payload = {"directories": {"lib": "a", "doc": "b"}, "max_entries": 1}
        with self.assertRaises(ValueError) as cm:
            run_feature(payload)
        self.assertEqual(str(cm.exception), EXPECTED)

    def test_extra_keys(self):
        with self.assertRaises(ValueError) as cm:
            run_feature({"directories": None, "extra": 1})
        self.assertEqual(str(cm.exception), EXPECTED)

    def test_missing_key(self):
        with self.assertRaises(ValueError) as cm:
            run_feature({})
        self.assertEqual(str(cm.exception), EXPECTED)
        with self.assertRaises(ValueError) as cm2:
            run_feature({"max_entries": 8})
        self.assertEqual(str(cm2.exception), EXPECTED)

    def test_non_dict_payload(self):
        for bad in (None, [], "x", 123, 0, 1, True):
            with self.assertRaises(ValueError) as cm:
                run_feature(bad)
            self.assertEqual(str(cm.exception), EXPECTED)

    def test_bool_budgets_rejected(self):
        with self.assertRaises(ValueError) as cm:
            run_feature({"directories": None, "max_entries": True})
        self.assertEqual(str(cm.exception), EXPECTED)
        with self.assertRaises(ValueError) as cm2:
            run_feature({"directories": None, "max_length": False})
        self.assertEqual(str(cm2.exception), EXPECTED)

    def test_bad_budget_types(self):
        for bad in ("8", 8.0, None, [], {}):
            with self.assertRaises(ValueError) as cm:
                run_feature({"directories": None, "max_entries": bad})
            self.assertEqual(str(cm.exception), EXPECTED)
            with self.assertRaises(ValueError) as cm2:
                run_feature({"directories": None, "max_length": bad})
            self.assertEqual(str(cm2.exception), EXPECTED)

    def test_non_positive_budgets(self):
        for bad in (0, -1, -100):
            with self.assertRaises(ValueError) as cm:
                run_feature({"directories": None, "max_entries": bad})
            self.assertEqual(str(cm.exception), EXPECTED)
            with self.assertRaises(ValueError) as cm2:
                run_feature({"directories": None, "max_length": bad})
            self.assertEqual(str(cm2.exception), EXPECTED)

    def test_directories_wrong_types(self):
        for bad in ("lib", 0, 1, 123, True, False, ["lib"]):
            with self.assertRaises(ValueError) as cm:
                run_feature({"directories": bad})
            self.assertEqual(str(cm.exception), EXPECTED)

    def test_non_string_keys_rejected(self):
        for badkey in (123, 0, 1, True, None):
            with self.assertRaises(ValueError) as cm:
                run_feature({"directories": {badkey: "x"}})
            self.assertEqual(str(cm.exception), EXPECTED)

    def test_str_subclass_accepted(self):
        class S(str):
            pass
        payload = {"directories": {S("lib"): S("mydir")}}
        out = run_feature(payload)
        self.assertEqual(len(out["entries"]), 1)
        self.assertEqual(out["entries"][0]["key"], "lib")
        self.assertEqual(out["entries"][0]["value"], "mydir")

    def test_no_mutation_no_shared_refs(self):
        inner = {"lib": "lib", "doc": "docs"}
        payload = {"directories": inner}
        before = copy.deepcopy(payload)
        r1 = run_feature(payload)
        r2 = run_feature(payload)
        self.assertEqual(payload, before)
        self.assertIsNot(r1, r2)
        self.assertIsNot(r1["entries"], r2["entries"])
        self.assertIsNot(r1["entries"][0], r2["entries"][0])
        self.assertIsNot(r1["entries"], inner)
        r1["entries"].append({"key": "x", "value": "y"})
        self.assertEqual(len(payload["directories"]), 2)
        self.assertEqual(len(r2["entries"]), 2)

    def test_deterministic(self):
        payload = {"directories": {"lib": "lib", "doc": "docs"}}
        self.assertEqual(run_feature(payload), run_feature(payload))

    def test_error_no_echo(self):
        evil = "EVILSECRET123"
        with self.assertRaises(ValueError) as cm:
            run_feature({"directories": {evil: "x"}})
        self.assertEqual(str(cm.exception), EXPECTED)
        self.assertNotIn(evil, str(cm.exception))


if __name__ == "__main__":
    unittest.main()
