import unittest

try:
    from npm_tarball_audit.features.workspaces_declaration_scan import run_feature
except ImportError:
    from src.npm_tarball_audit.features.workspaces_declaration_scan import run_feature

FIXED = "Invalid workspaces scan payload or budget"


class TestWorkspacesDeclarationScan(unittest.TestCase):
    def test_absent_none(self):
        payload = {"workspaces": None}
        snapshot = {"workspaces": None}
        result = run_feature(payload)
        self.assertEqual(result, {"entries": None, "declared": False})
        self.assertEqual(payload, snapshot)
        self.assertIsNone(result["entries"])
        self.assertFalse(result["declared"])
        self.assertEqual(set(result.keys()), {"entries", "declared"})

    def test_empty_list_fresh_containers(self):
        first = run_feature({"workspaces": []})
        second = run_feature({"workspaces": []})
        self.assertEqual(first, {"entries": [], "declared": True})
        self.assertEqual(second, {"entries": [], "declared": True})
        self.assertEqual(first, second)
        self.assertIsNot(first, second)
        self.assertIsNot(first["entries"], second["entries"])

    def test_unsorted_sorted_verbatim(self):
        payload = {"workspaces": ["packages/*", "apps/web"]}
        result = run_feature(payload)
        self.assertEqual(result, {"entries": ["apps/web", "packages/*"], "declared": True})
        self.assertEqual(payload, {"workspaces": ["packages/*", "apps/web"]})

    def test_spacing_and_case_preserved(self):
        payload = {"workspaces": ["apple", "Zebra", "  spaced  "]}
        result = run_feature(payload)
        self.assertEqual(result["entries"], ["  spaced  ", "Zebra", "apple"])
        self.assertTrue(result["declared"])
        mixed = {"workspaces": ["Foo", "foo", "FOO"]}
        mixed_result = run_feature(mixed)
        self.assertEqual(mixed_result["entries"], ["FOO", "Foo", "foo"])

    def test_allowed_controls_and_subclass(self):
        payload = {"workspaces": ["a\tb", "a\nb", "a\rb"]}
        result = run_feature(payload)
        self.assertEqual(len(result["entries"]), 3)
        self.assertTrue(result["declared"])
        class S(str):
            pass
        sub_payload = {"workspaces": [S("b"), S("a")]}
        sub_result = run_feature(sub_payload)
        self.assertEqual(sub_result["entries"], ["a", "b"])
        self.assertTrue(sub_result["declared"])

    def test_wrong_types_empty_and_controls_raise(self):
        bad_workspaces = [
            "packages/*",
            0,
            1,
            123,
            True,
            False,
            {},
            ("a",),
            {"a": 1},
            b"a",
            1.5,
        ]
        for bad in bad_workspaces:
            with self.subTest(bad=repr(bad)):
                with self.assertRaises(ValueError) as ctx:
                    run_feature({"workspaces": bad})
                self.assertEqual(str(ctx.exception), FIXED)
        bad_lists = [
            [""],
            [["a"]],
            [[]],
            [[None]],
            [None],
            [123],
            [True],
            [False],
            [{}],
            [("a",)],
            [b"a"],
            ["a", None],
            ["ok", 5],
            ["ok", ""],
            ["a\x00b"],
            ["a\x01b"],
            ["a\x07b"],
            ["a\x08b"],
            ["a\x0bb"],
            ["a\x0cb"],
            ["a\x1fb"],
            ["\x00"],
            ["\x1f"],
            ["\ud800"],
            ["a\udfffb"],
        ]
        for bad in bad_lists:
            with self.subTest(bad=repr(bad)):
                with self.assertRaises(ValueError) as ctx:
                    run_feature({"workspaces": bad})
                self.assertEqual(str(ctx.exception), FIXED)

    def test_over_budget_counts_and_lengths_raise(self):
        many = ["a" for _ in range(33)]
        with self.assertRaises(ValueError) as ctx:
            run_feature({"workspaces": many})
        self.assertEqual(str(ctx.exception), FIXED)
        long_value = "x" * 257
        with self.assertRaises(ValueError) as ctx:
            run_feature({"workspaces": [long_value]})
        self.assertEqual(str(ctx.exception), FIXED)
        with self.assertRaises(ValueError) as ctx:
            run_feature({"workspaces": ["a", "b", "c"], "max_entries": 2})
        self.assertEqual(str(ctx.exception), FIXED)
        with self.assertRaises(ValueError) as ctx:
            run_feature({"workspaces": ["abc"], "max_length": 2})
        self.assertEqual(str(ctx.exception), FIXED)

    def test_missing_extra_nondict_invalid_budget(self):
        with self.assertRaises(ValueError) as ctx:
            run_feature({})
        self.assertEqual(str(ctx.exception), FIXED)
        with self.assertRaises(ValueError) as ctx:
            run_feature({"workspaces": None, "extra": 1})
        self.assertEqual(str(ctx.exception), FIXED)
        for bad_payload in [None, [], "x", 123, 0, True, False]:
            with self.subTest(payload=repr(bad_payload)):
                with self.assertRaises(ValueError) as ctx:
                    run_feature(bad_payload)
                self.assertEqual(str(ctx.exception), FIXED)
        bad_budgets = [
            {"workspaces": [], "max_entries": True},
            {"workspaces": [], "max_entries": False},
            {"workspaces": [], "max_entries": "32"},
            {"workspaces": [], "max_entries": 32.0},
            {"workspaces": [], "max_entries": None},
            {"workspaces": [], "max_entries": 0},
            {"workspaces": [], "max_entries": 257},
            {"workspaces": [], "max_length": True},
            {"workspaces": [], "max_length": "256"},
            {"workspaces": [], "max_length": 1.5},
            {"workspaces": [], "max_length": 0},
            {"workspaces": [], "max_length": 1025},
            {"workspaces": None, "max_entries": 0},
            {"workspaces": None, "max_length": 1025},
        ]
        for payload in bad_budgets:
            with self.subTest(payload=payload):
                with self.assertRaises(ValueError) as ctx:
                    run_feature(payload)
                self.assertEqual(str(ctx.exception), FIXED)
                self.assertNotIn("extra", str(ctx.exception))

    def test_custom_budgets_accepted(self):
        result = run_feature({"workspaces": ["a", "b", "c"], "max_entries": 3})
        self.assertEqual(result["entries"], ["a", "b", "c"])
        long_ok = "y" * 1024
        result2 = run_feature({"workspaces": [long_ok], "max_length": 1024})
        self.assertEqual(result2["entries"], [long_ok])
        result3 = run_feature({"workspaces": None, "max_entries": 10, "max_length": 10})
        self.assertEqual(result3, {"entries": None, "declared": False})

    def test_no_mutation_and_independent_outputs(self):
        payload = {"workspaces": ["b", "a"]}
        before = {"workspaces": ["b", "a"]}
        first = run_feature(payload)
        second = run_feature(payload)
        self.assertEqual(payload, before)
        self.assertEqual(first, second)
        self.assertIsNot(first, second)
        self.assertIsNot(first["entries"], second["entries"])
        first["entries"].append("injected")
        self.assertEqual(second["entries"], ["a", "b"])
        self.assertEqual(payload["workspaces"], ["b", "a"])
        payload["workspaces"].append("c")
        self.assertEqual(first["entries"], ["a", "b", "injected"])
        self.assertEqual(second["entries"], ["a", "b"])
        none_first = run_feature({"workspaces": None})
        none_second = run_feature({"workspaces": None})
        self.assertEqual(none_first, none_second)
        self.assertIsNot(none_first, none_second)


if __name__ == "__main__":
    unittest.main()
