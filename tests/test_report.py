import json
import unittest

from npm_tarball_audit.report import parse_inventory_report


def report(entries=None, **changes):
    return {"schema": "npm-tarball-audit/v1", "status": "pass",
            "package_executed": False, "files_extracted": False,
            "inventory": [] if entries is None else entries, **changes}


def entry(path="package/index.js", digest="A" * 64):
    return {"path": path, "bytes": 1, "sha256": digest}


class ReportTests(unittest.TestCase):
    def test_inventory_is_sorted_normalized_and_separated_from_metadata(self):
        original = report([entry("package/z"), entry("package/a")],
                          findings=[{"message": "inspect separately"}])
        text = json.dumps(original)
        result = parse_inventory_report(text)
        self.assertEqual(result, [entry("package/a", "a" * 64), entry("package/z", "a" * 64)])
        self.assertEqual(original["inventory"][0]["sha256"], "A" * 64)
        result[0]["bytes"] = 100
        self.assertEqual(parse_inventory_report(text)[0]["bytes"], 1)

    def test_required_report_metadata_and_partial_inventory_policy(self):
        self.assertEqual(parse_inventory_report(json.dumps(report(status="warning"))), [])
        for changes in ({"status": "fail"}, {"schema": "future/v2"},
                        {"package_executed": 0}, {"files_extracted": True},
                        {"inventory": None}):
            with self.subTest(changes=changes), self.assertRaises(ValueError):
                parse_inventory_report(json.dumps(report(**changes)))
        missing = report()
        del missing["inventory"]
        with self.assertRaises(ValueError):
            parse_inventory_report(json.dumps(missing))

    def test_strict_json_checks_ignored_metadata_too(self):
        prefix = json.dumps(report())[:-1]
        for suffix in (',"extra":{"a":1,"a":2}}', ',"extra":NaN}',
                       ',"extra":Infinity}', ',"extra":1e9999}', ',"extra":-1e9999}'):
            with self.subTest(suffix=suffix), self.assertRaises(ValueError):
                parse_inventory_report(prefix + suffix)
        for text in ("", "null", "[]", "{", "{} trailing", "\ud800"):
            with self.subTest(text=repr(text)), self.assertRaises(ValueError):
                parse_inventory_report(text)

    def test_utf8_and_depth_budgets_have_exact_boundaries(self):
        text = json.dumps(report([entry()], note="é"), ensure_ascii=False)
        size = len(text.encode("utf-8"))
        self.assertEqual(len(parse_inventory_report(text, max_bytes=size, max_depth=3)), 1)
        for budget in ({"max_bytes": size - 1}, {"max_depth": 2}):
            with self.subTest(budget=budget), self.assertRaises(ValueError):
                parse_inventory_report(text, **budget)
        strings = json.dumps(report(note='[[ {{ \\" \\ "] }}}'))
        self.assertEqual(parse_inventory_report(strings, max_depth=2), [])

    def test_entry_budget_and_existing_comparator_rules_apply(self):
        text = json.dumps(report([entry("package/a"), entry("package/b")]))
        self.assertEqual(len(parse_inventory_report(text, max_entries=2)), 2)
        with self.assertRaises(ValueError):
            parse_inventory_report(text, max_entries=1)
        for entries in ([entry(), entry()], [entry("package/../escape")],
                        [{**entry(), "bytes": True}], [{**entry(), "extra": "discard me"}]):
            with self.subTest(entries=entries), self.assertRaises(ValueError):
                parse_inventory_report(json.dumps(report(entries)))

    def test_types_and_budget_values_are_not_coerced(self):
        for text in (b"{}", None, {}, True):
            with self.subTest(text=text), self.assertRaises(ValueError):
                parse_inventory_report(text)
        for key in ("max_bytes", "max_depth", "max_entries"):
            for value in (True, 0, -1, "10", 10.0):
                with self.subTest(key=key, value=value), self.assertRaises(ValueError):
                    parse_inventory_report(json.dumps(report()), **{key: value})

    def test_errors_do_not_echo_report_values(self):
        marker = "SYNTHETIC_PRIVATE_MARKER"
        for data in (report(status=marker), report([entry(marker)])):
            with self.assertRaises(ValueError) as failure:
                parse_inventory_report(json.dumps(data))
            self.assertNotIn(marker, str(failure.exception))


if __name__ == "__main__":
    unittest.main()
