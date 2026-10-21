import copy
import unittest

try:
    from npm_tarball_audit.features.bugs_declaration_scan import run_feature
except ImportError:
    from src.npm_tarball_audit.features.bugs_declaration_scan import run_feature

FIXED = "Invalid bugs scan payload or budget"

class BugsDeclarationScanTest(unittest.TestCase):
    def check_invalid(self, payload):
        with self.assertRaises(ValueError) as ctx:
            run_feature(payload)
        self.assertEqual(str(ctx.exception), FIXED)

    def check_no_echo(self, payload, marker):
        with self.assertRaises(ValueError) as ctx:
            run_feature(payload)
        msg = str(ctx.exception)
        self.assertEqual(msg, FIXED)
        self.assertNotIn(marker, msg)

    def test_none_default(self):
        payload = {"bugs": None}
        before = copy.deepcopy(payload)
        result = run_feature(payload)
        self.assertEqual(result, {"url": None, "email": None, "declared": False})
        self.assertEqual(set(result.keys()), {"url", "email", "declared"})
        self.assertEqual(payload, before)
        second = run_feature({"bugs": None})
        self.assertEqual(result, second)
        self.assertIsNot(result, second)

    def test_shorthand_verbatim(self):
        value = "  HTTPS://Example.COM/issues?X=1  "
        payload = {"bugs": value}
        before = copy.deepcopy(payload)
        result = run_feature(payload)
        self.assertEqual(result["url"], value)
        self.assertIsNone(result["email"])
        self.assertTrue(result["declared"])
        self.assertEqual(set(result.keys()), {"url", "email", "declared"})
        self.assertEqual(payload, before)
        self.assertEqual(payload["bugs"], value)

    def test_shorthand_str_subclass(self):
        class S(str):
            pass
        value = S("https://example.com/issues")
        result = run_feature({"bugs": value})
        self.assertEqual(result, {"url": "https://example.com/issues", "email": None, "declared": True})

    def test_dict_both_orders(self):
        a = run_feature({"bugs": {"url": "https://example.com/issues", "email": "bugs@example.com"}})
        self.assertEqual(a, {"url": "https://example.com/issues", "email": "bugs@example.com", "declared": True})
        b = run_feature({"bugs": {"email": "bugs@example.com", "url": "https://example.com/issues"}})
        self.assertEqual(b, a)
        self.assertIsNot(a, b)

    def test_single_key_dicts(self):
        only_url = run_feature({"bugs": {"url": "https://example.com/issues"}})
        self.assertEqual(only_url, {"url": "https://example.com/issues", "email": None, "declared": True})
        only_email = run_feature({"bugs": {"email": "bugs@example.com"}})
        self.assertEqual(only_email, {"url": None, "email": "bugs@example.com", "declared": True})

    def test_reject_bad_bugs_shapes(self):
        self.check_invalid({"bugs": {}})
        self.check_no_echo({"bugs": {"url": "https://example.com/issues", "homepage": "ZZZ-ECHO-999"}}, "ZZZ-ECHO-999")
        self.check_invalid({"bugs": []})
        self.check_invalid({"bugs": 123})
        self.check_invalid({"bugs": True})
        self.check_invalid({"bugs": False})
        self.check_invalid({"bugs": {"url": 123}})
        self.check_invalid({"bugs": {"email": True}})
        self.check_invalid({"bugs": {"url": ["https://example.com"]}})
        self.check_invalid({"bugs": {"url": {"nested": "x"}}})
        self.check_invalid({"bugs": {"url": None}})
        self.check_no_echo({"bugs": {"url": "a", "email": "b", "ZZZ-ECHO-998": "c"}}, "ZZZ-ECHO-998")
        self.check_invalid({"bugs": 3.5})

    def test_reject_payload_problems(self):
        self.check_invalid({})
        self.check_invalid({"max_length": 10})
        self.check_no_echo({"bugs": None, "ZZZ-ECHO-997": 1}, "ZZZ-ECHO-997")
        self.check_invalid({"bugs": None, "max_length": True})
        self.check_invalid({"bugs": None, "max_length": False})
        self.check_invalid({"bugs": None, "max_length": 0})
        self.check_invalid({"bugs": None, "max_length": -5})
        self.check_invalid({"bugs": None, "max_length": "512"})
        self.check_invalid({"bugs": None, "max_length": 5.0})
        self.check_invalid({"bugs": None, "max_length": None})
        self.check_invalid([("bugs", None)])
        self.check_invalid(None)
        self.check_invalid("x")

    def test_reject_string_lengths(self):
        self.check_invalid({"bugs": ""})
        long_value = "Q" * 513 + "ZZZ-ECHO-996"
        self.check_no_echo({"bugs": long_value}, "ZZZ-ECHO-996")
        self.check_invalid({"bugs": "ab", "max_length": 1})
        self.check_invalid({"bugs": {"url": ""}})
        self.check_invalid({"bugs": {"email": "y" * 10}, "max_length": 2})
        ok = run_feature({"bugs": "abc", "max_length": 3})
        self.assertTrue(ok["declared"])
        self.assertEqual(ok["url"], "abc")

    def test_repeated_calls_distinct_no_mutation(self):
        payload = {"bugs": {"url": "https://example.com/issues", "email": "bugs@example.com"}}
        snapshot = copy.deepcopy(payload)
        first = run_feature(payload)
        second = run_feature(payload)
        self.assertEqual(first, second)
        self.assertIsNot(first, second)
        self.assertEqual(payload, snapshot)
        first["url"] = "mutated"
        self.assertNotEqual(first, second)
        self.assertEqual(second["url"], "https://example.com/issues")
        shorthand = {"bugs": "https://example.com/issues"}
        snap2 = copy.deepcopy(shorthand)
        r1 = run_feature(shorthand)
        r2 = run_feature(dict(shorthand))
        self.assertEqual(r1, r2)
        self.assertIsNot(r1, r2)
        self.assertEqual(shorthand, snap2)

    def test_examples(self):
        self.assertEqual(run_feature({"bugs": None}), {"url": None, "email": None, "declared": False})
        self.assertEqual(run_feature({"bugs": "https://example.com/issues"}), {"url": "https://example.com/issues", "email": None, "declared": True})
        self.assertEqual(run_feature({"bugs": {"email": "bugs@example.com", "url": "https://example.com/issues"}}), {"url": "https://example.com/issues", "email": "bugs@example.com", "declared": True})

if __name__ == "__main__":
    unittest.main()
