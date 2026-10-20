import copy
import unittest

from npm_tarball_audit.entrypoints import compare_entrypoints

MSG = "Invalid entrypoint metadata"


class CompareEntrypointsTests(unittest.TestCase):
    def test_unchanged_counts_equal_fields(self):
        before = {"main": "index.js", "bin": {"t": "cli.js"}}
        after = {"main": "index.js", "bin": {"t": "cli.js"}}
        result = compare_entrypoints(before, after)
        self.assertEqual(result["added"], [])
        self.assertEqual(result["removed"], [])
        self.assertEqual(result["changed"], [])
        self.assertEqual(result["unchanged_count"], 2)
        self.assertEqual(set(result.keys()), {"added", "removed", "changed", "unchanged_count"})

    def test_absent_both_does_not_count(self):
        result = compare_entrypoints({}, {})
        self.assertEqual(result["unchanged_count"], 0)
        self.assertEqual(result["added"], [])

    def test_absence_differs_from_null(self):
        result = compare_entrypoints({}, {"main": None})
        self.assertEqual(len(result["added"]), 1)
        self.assertEqual(result["added"][0], {"field": "main", "value": None})
        result2 = compare_entrypoints({"main": None}, {})
        self.assertEqual(result2["removed"][0], {"field": "main", "value": None})
        result3 = compare_entrypoints({"main": None}, {"main": None})
        self.assertEqual(result3["unchanged_count"], 1)

    def test_named_arguments(self):
        result = compare_entrypoints(before={"main": "a"}, after={"main": "a"})
        self.assertEqual(result["unchanged_count"], 1)

    def test_field_order_added_removed_changed(self):
        before = {"exports": "a", "main": "x"}
        after = {"bin": "b", "main": "y"}
        result = compare_entrypoints(before, after)
        self.assertEqual([i["field"] for i in result["added"]], ["bin"])
        self.assertEqual([i["field"] for i in result["removed"]], ["exports"])
        self.assertEqual([i["field"] for i in result["changed"]], ["main"])
        before2 = {}
        after2 = {"exports": 1, "bin": 2, "main": 3}
        result2 = compare_entrypoints(before2, after2)
        self.assertEqual([i["field"] for i in result2["added"]], ["main", "bin", "exports"])

    def test_main_bin_order_insensitive(self):
        before = {"main": {"a": 1, "b": 2}}
        after = {"main": {"b": 2, "a": 1}}
        self.assertEqual(compare_entrypoints(before, after)["unchanged_count"], 1)
        before_n = {"bin": {"x": {"a": 1, "b": [1, 2]}}}
        after_n = {"bin": {"x": {"b": [1, 2], "a": 1}}}
        self.assertEqual(compare_entrypoints(before_n, after_n)["unchanged_count"], 1)

    def test_exports_order_sensitive(self):
        before = {"exports": {"a": 1, "b": 2}}
        after = {"exports": {"b": 2, "a": 1}}
        result = compare_entrypoints(before, after)
        self.assertEqual(result["unchanged_count"], 0)
        self.assertEqual(len(result["changed"]), 1)
        self.assertEqual(list(result["changed"][0]["before"].keys()), ["a", "b"])
        self.assertEqual(list(result["changed"][0]["after"].keys()), ["b", "a"])

    def test_nested_exports_order_sensitive(self):
        before = {"exports": {".": {"import": "a", "require": "b"}}}
        after = {"exports": {".": {"require": "b", "import": "a"}}}
        result = compare_entrypoints(before, after)
        self.assertEqual(len(result["changed"]), 1)

    def test_main_output_sorted(self):
        before = {"main": {"z": 1, "a": 2}}
        after = {"main": {"z": 9, "a": 2}}
        result = compare_entrypoints(before, after)
        self.assertEqual(list(result["changed"][0]["before"].keys()), ["a", "z"])
        self.assertEqual(list(result["changed"][0]["after"].keys()), ["a", "z"])
        result2 = compare_entrypoints({}, {"bin": {"z": 1, "a": 2}})
        self.assertEqual(list(result2["added"][0]["value"].keys()), ["a", "z"])

    def test_lists_order_sensitive(self):
        before = {"main": [1, 2]}
        after = {"main": [2, 1]}
        self.assertEqual(len(compare_entrypoints(before, after)["changed"]), 1)

    def test_scalar_types_significant(self):
        self.assertEqual(len(compare_entrypoints({"main": True}, {"main": 1})["changed"]), 1)
        self.assertEqual(len(compare_entrypoints({"main": 1}, {"main": 1.0})["changed"]), 1)
        self.assertEqual(len(compare_entrypoints({"main": 1}, {"main": True})["changed"]), 1)
        unchanged = compare_entrypoints({"main": 0.0}, {"main": -0.0})
        self.assertEqual(unchanged["unchanged_count"], 1)
        self.assertEqual(unchanged["changed"], [])

    def test_other_metadata_ignored(self):
        before = {"name": "x", "version": "1", "main": "a"}
        after = {"name": "y", "version": "2", "main": "a"}
        result = compare_entrypoints(before, after)
        self.assertEqual(result["unchanged_count"], 1)
        self.assertEqual(result["changed"], [])

    def test_outputs_are_fresh_and_unshared(self):
        before = {"main": {"a": [1]}}
        after = {"main": {"a": [2]}}
        snapshot_before = copy.deepcopy(before)
        snapshot_after = copy.deepcopy(after)
        result = compare_entrypoints(before, after)
        self.assertEqual(before, snapshot_before)
        self.assertEqual(after, snapshot_after)
        b_copy = result["changed"][0]["before"]
        a_copy = result["changed"][0]["after"]
        self.assertIsNot(b_copy, before["main"])
        self.assertIsNot(a_copy, after["main"])
        self.assertIsNot(b_copy["a"], before["main"]["a"])
        b_copy["a"].append(99)
        self.assertEqual(before, snapshot_before)
        self.assertIsNot(b_copy, a_copy)

    def test_invalid_top_level(self):
        for bad in (None, [], "x", {"main": "a", "x": 1} | {str(i): i for i in range(130)}):
            with self.assertRaises(ValueError) as ctx:
                compare_entrypoints(bad, {})
            self.assertEqual(str(ctx.exception), MSG)
        class MyDict(dict):
            pass
        with self.assertRaises(ValueError) as ctx:
            compare_entrypoints(MyDict(), {})
        self.assertEqual(str(ctx.exception), MSG)
        with self.assertRaises(ValueError) as ctx:
            compare_entrypoints({123: 1}, {})
        self.assertEqual(str(ctx.exception), MSG)
        with self.assertRaises(ValueError) as ctx:
            compare_entrypoints({"a" * 1025: 1}, {})
        self.assertEqual(str(ctx.exception), MSG)
        with self.assertRaises(ValueError) as ctx:
            compare_entrypoints({"\ud800": 1}, {})
        self.assertEqual(str(ctx.exception), MSG)

    def test_invalid_selected_types_and_ranges(self):
        class MyStr(str):
            pass
        for bad_value in (MyStr("a"), (1, 2), b"a", {"a"}, float("inf"), float("nan"), 2**53, -(2**53)):
            with self.assertRaises(ValueError) as ctx:
                compare_entrypoints({"main": bad_value}, {})
            self.assertEqual(str(ctx.exception), MSG)
        with self.assertRaises(ValueError) as ctx:
            compare_entrypoints({"main": {123: 1}}, {})
        self.assertEqual(str(ctx.exception), MSG)
        with self.assertRaises(ValueError) as ctx:
            compare_entrypoints({"main": "a" * 1025}, {})
        self.assertEqual(str(ctx.exception), MSG)
        with self.assertRaises(ValueError) as ctx:
            compare_entrypoints({"main": "\ud800"}, {})
        self.assertEqual(str(ctx.exception), MSG)
        # boundaries are valid
        compare_entrypoints({"main": 2**53 - 1}, {"main": 2**53 - 1})
        compare_entrypoints({"main": -(2**53 - 1)}, {"main": -(2**53 - 1)})
        compare_entrypoints({"main": "a" * 1024}, {"main": "a" * 1024})

    def test_invalid_budgets_and_cycles(self):
        big = list(range(3000))
        with self.assertRaises(ValueError) as ctx:
            compare_entrypoints({"main": big, "bin": big}, {})
        self.assertEqual(str(ctx.exception), MSG)
        deep: object = []
        for _ in range(17):
            deep = [deep]
        with self.assertRaises(ValueError) as ctx:
            compare_entrypoints({"main": deep}, {})
        self.assertEqual(str(ctx.exception), MSG)
        cycle: list = []
        cycle.append(cycle)
        with self.assertRaises(ValueError) as ctx:
            compare_entrypoints({"main": cycle}, {})
        self.assertEqual(str(ctx.exception), MSG)
        before = {"main": "x"}
        snapshot = copy.deepcopy(before)
        with self.assertRaises(ValueError):
            compare_entrypoints(before, {"main": cycle})
        self.assertEqual(before, snapshot)

    def test_no_echo_in_error(self):
        secret = "secret-marker-" + "x" * 2000
        try:
            compare_entrypoints({"main": secret}, {})
        except ValueError as exc:
            self.assertEqual(str(exc), MSG)
            self.assertNotIn("secret-marker", str(exc))
        else:
            self.fail("expected ValueError")


if __name__ == "__main__":
    unittest.main()
