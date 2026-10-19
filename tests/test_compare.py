import unittest

from npm_tarball_audit.compare import compare_inventories


def canonical_entry(path: str, size: int, digest: str) -> dict:
    return {"path": path, "bytes": size, "sha256": digest.lower()}


class CompareInventoriesTests(unittest.TestCase):
    def test_added_and_removed(self):
        before = [
            canonical_entry("package/a.js", 1, "a" * 64),
            canonical_entry("package/b.js", 2, "b" * 64),
        ]
        after = [
            canonical_entry("package/b.js", 2, "b" * 64),
            canonical_entry("package/c.js", 3, "c" * 64),
        ]

        result = compare_inventories(before, after)

        self.assertEqual(
            result,
            {
                "added": [canonical_entry("package/c.js", 3, "c" * 64)],
                "removed": [canonical_entry("package/a.js", 1, "a" * 64)],
                "changed": [],
                "unchanged_count": 1,
            },
        )

    def test_hash_only_change(self):
        before = [canonical_entry("package/a.js", 10, "a" * 64)]
        after = [canonical_entry("package/a.js", 10, "b" * 64)]

        result = compare_inventories(before, after)

        self.assertEqual(
            result,
            {
                "added": [],
                "removed": [],
                "changed": [
                    {
                        "path": "package/a.js",
                        "before": canonical_entry("package/a.js", 10, "a" * 64),
                        "after": canonical_entry("package/a.js", 10, "b" * 64),
                    }
                ],
                "unchanged_count": 0,
            },
        )

    def test_bytes_only_change(self):
        before = [canonical_entry("package/a.js", 10, "a" * 64)]
        after = [canonical_entry("package/a.js", 11, "a" * 64)]

        result = compare_inventories(before, after)

        self.assertEqual(
            result,
            {
                "added": [],
                "removed": [],
                "changed": [
                    {
                        "path": "package/a.js",
                        "before": canonical_entry("package/a.js", 10, "a" * 64),
                        "after": canonical_entry("package/a.js", 11, "a" * 64),
                    }
                ],
                "unchanged_count": 0,
            },
        )

    def test_unchanged_and_empty_results(self):
        before = [canonical_entry("package/a.js", 1, "a" * 64)]
        after = [canonical_entry("package/a.js", 1, "a" * 64)]

        result = compare_inventories(before, after)

        self.assertEqual(
            result,
            {
                "added": [],
                "removed": [],
                "changed": [],
                "unchanged_count": 1,
            },
        )

        empty_result = compare_inventories([], [])
        self.assertEqual(
            empty_result,
            {
                "added": [],
                "removed": [],
                "changed": [],
                "unchanged_count": 0,
            },
        )

    def test_deterministic_ordering(self):
        before = [
            canonical_entry("package/z.js", 1, "a" * 64),
            canonical_entry("package/w.js", 1, "a" * 64),
            canonical_entry("package/c.js", 2, "b" * 64),
            canonical_entry("package/a.js", 2, "b" * 64),
            canonical_entry("package/keep.js", 3, "c" * 64),
        ]
        after = [
            canonical_entry("package/y.js", 3, "c" * 64),
            canonical_entry("package/b.js", 4, "d" * 64),
            canonical_entry("package/c.js", 9, "b" * 64),
            canonical_entry("package/a.js", 2, "a" * 64),
            canonical_entry("package/keep.js", 3, "c" * 64),
        ]
        result = compare_inventories(before, after)
        self.assertEqual([entry["path"] for entry in result["added"]], ["package/b.js", "package/y.js"])
        self.assertEqual([entry["path"] for entry in result["removed"]], ["package/w.js", "package/z.js"])
        self.assertEqual([item["path"] for item in result["changed"]], ["package/a.js", "package/c.js"])
        self.assertEqual(result["unchanged_count"], 1)
        self.assertEqual(compare_inventories(before[::-1], after[::-1]), result)

    def test_digest_case_normalization(self):
        before = [{"path": "package/a.js", "bytes": 1, "sha256": "A" * 64}]
        after = [{"path": "package/a.js", "bytes": 1, "sha256": "a" * 64}]

        result = compare_inventories(before, after)

        self.assertEqual(
            result,
            {
                "added": [],
                "removed": [],
                "changed": [],
                "unchanged_count": 1,
            },
        )

    def test_no_input_mutation_or_output_aliasing(self):
        before = [{"path": "package/a.js", "bytes": 1, "sha256": "a" * 64}]
        after = [{"path": "package/a.js", "bytes": 2, "sha256": "b" * 64}]

        before_snapshot = [dict(entry) for entry in before]
        after_snapshot = [dict(entry) for entry in after]

        result = compare_inventories(before, after)

        self.assertEqual(before, before_snapshot)
        self.assertEqual(after, after_snapshot)

        changed = result["changed"][0]
        self.assertIsNot(changed["before"], before[0])
        self.assertIsNot(changed["after"], after[0])

        changed["before"]["bytes"] = 999
        changed["after"]["bytes"] = 999

        self.assertEqual(before[0]["bytes"], 1)
        self.assertEqual(after[0]["bytes"], 2)

    def test_duplicate_paths_rejected(self):
        before = [
            canonical_entry("package/a.js", 1, "a" * 64),
            canonical_entry("package/a.js", 1, "a" * 64),
        ]
        after = []

        with self.assertRaises(ValueError):
            compare_inventories(before, after)

    def test_malformed_entry_rejected(self):
        before = [{"path": "package/a.js", "bytes": 1}]
        after = []

        with self.assertRaises(ValueError):
            compare_inventories(before, after)

    def test_extra_field_rejected(self):
        before = [{"path": "package/a.js", "bytes": 1, "sha256": "a" * 64, "extra": 1}]
        after = []

        with self.assertRaises(ValueError):
            compare_inventories(before, after)

    def test_invalid_bytes_rejected(self):
        before = [{"path": "package/a.js", "bytes": True, "sha256": "a" * 64}]
        after = []

        with self.assertRaises(ValueError):
            compare_inventories(before, after)

    def test_negative_bytes_rejected(self):
        before = [{"path": "package/a.js", "bytes": -1, "sha256": "a" * 64}]
        after = []

        with self.assertRaises(ValueError):
            compare_inventories(before, after)

    def test_invalid_digest_rejected(self):
        before = [{"path": "package/a.js", "bytes": 1, "sha256": "a" * 63}]
        after = []

        with self.assertRaises(ValueError):
            compare_inventories(before, after)

    def test_non_string_path_rejected(self):
        before = [{"path": 1, "bytes": 1, "sha256": "a" * 64}]
        after = []

        with self.assertRaises(ValueError):
            compare_inventories(before, after)

    def test_unsafe_paths_rejected(self):
        unsafe_paths = [
            "package/",
            "package//a.js",
            "package/./a.js",
            "package/../a.js",
            "package/a.js/",
            "package\\a.js",
            "package/a:b.js",
            "/package/a.js",
            "package/a\x00.js",
            "package/a\x1f.js",
            "package/a\x7f.js",
            "package/a\x9f.js",
        ]

        for path in unsafe_paths:
            before = [{"path": path, "bytes": 1, "sha256": "a" * 64}]
            after = []

            with self.assertRaises(ValueError):
                compare_inventories(before, after)

    def test_non_list_inputs_rejected(self):
        with self.assertRaises(ValueError):
            compare_inventories({}, [])

        with self.assertRaises(ValueError):
            compare_inventories([], {})

    def test_exact_max_entries_allowed(self):
        before = [canonical_entry(f"package/{i}.js", i, "a" * 64) for i in range(3)]
        after = [canonical_entry(f"package/{i}.js", i, "a" * 64) for i in range(3)]

        result = compare_inventories(before, after, max_entries=3)

        self.assertEqual(result["unchanged_count"], 3)

    def test_over_max_entries_rejected(self):
        before = [canonical_entry(f"package/{i}.js", i, "a" * 64) for i in range(4)]
        after = []

        with self.assertRaises(ValueError):
            compare_inventories(before, after, max_entries=3)

    def test_per_side_max_entries_rejected(self):
        before = [canonical_entry(f"package/{i}.js", i, "a" * 64) for i in range(3)]
        after = [canonical_entry(f"package/{i}.js", i, "a" * 64) for i in range(4)]

        with self.assertRaises(ValueError):
            compare_inventories(before, after, max_entries=3)

    def test_invalid_max_entries_rejected(self):
        for invalid in (0, -1, True, False, 3.0, "3", None):
            with self.assertRaises(ValueError):
                compare_inventories([], [], max_entries=invalid)

    def test_default_max_entries(self):
        before = [canonical_entry(f"package/{i}.js", i, "a" * 64) for i in range(20000)]
        after = [canonical_entry(f"package/{i}.js", i, "a" * 64) for i in range(20000)]

        result = compare_inventories(before, after)

        self.assertEqual(result["unchanged_count"], 20000)

        before.append(canonical_entry("package/20000.js", 20000, "a" * 64))
        with self.assertRaises(ValueError):
            compare_inventories(before, after)


if __name__ == "__main__":
    unittest.main()
