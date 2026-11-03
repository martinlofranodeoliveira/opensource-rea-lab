import unittest

try:
    from npm_tarball_audit.features.libc_declaration_scan import run_feature
except ImportError:
    from src.npm_tarball_audit.features.libc_declaration_scan import run_feature

PAYLOAD_ERROR = "Invalid libc payload or budget"
DECLARATION_ERROR = "Invalid libc declaration"


class LibcDeclarationScanTest(unittest.TestCase):
    def test_absent_none(self):
        payload = {"libc": None}
        result = run_feature(payload)
        self.assertEqual(payload, {"libc": None})
        self.assertEqual(result["present"], False)
        self.assertEqual(result["kind"], "absent")
        self.assertEqual(result["total"], 0)
        self.assertEqual(result["valid_count"], 0)
        self.assertEqual(result["invalid_count"], 0)
        self.assertEqual(result["entries"], [])
        self.assertEqual(list(result.keys()), ["present", "kind", "total", "valid_count", "invalid_count", "entries"])
        self.assertIs(type(result["kind"]), str)

    def test_empty_list(self):
        payload = {"libc": []}
        result = run_feature(payload)
        self.assertEqual(payload, {"libc": []})
        self.assertEqual(result["present"], True)
        self.assertEqual(result["kind"], "empty")
        self.assertEqual(result["total"], 0)
        self.assertEqual(result["valid_count"], 0)
        self.assertEqual(result["invalid_count"], 0)
        self.assertEqual(result["entries"], [])

    def test_valid_sorted(self):
        result = run_feature({"libc": ["musl", "glibc"]})
        self.assertEqual(result["present"], True)
        self.assertEqual(result["kind"], "listed")
        self.assertEqual(result["total"], 2)
        self.assertEqual(result["valid_count"], 2)
        self.assertEqual(result["invalid_count"], 0)
        self.assertEqual([e["value"] for e in result["entries"]], ["glibc", "musl"])
        for e in result["entries"]:
            self.assertEqual(e["valid"], True)
            self.assertEqual(e["reasons"], [])
            self.assertIs(type(e["value"]), str)
            self.assertEqual(list(e.keys()), ["value", "valid", "reasons"])

    def test_mixed_syntax_example(self):
        result = run_feature({"libc": ["glibc", "Glibc", "a/b"]})
        self.assertEqual(result["total"], 3)
        self.assertEqual(result["valid_count"], 1)
        self.assertEqual(result["invalid_count"], 2)
        self.assertEqual([e["value"] for e in result["entries"]], ["Glibc", "a/b", "glibc"])
        by_value = {e["value"]: e for e in result["entries"]}
        self.assertEqual(by_value["glibc"]["valid"], True)
        self.assertEqual(by_value["glibc"]["reasons"], [])
        self.assertEqual(by_value["Glibc"]["reasons"], ["value_syntax"])
        self.assertEqual(by_value["a/b"]["reasons"], ["value_syntax"])

    def test_length_and_syntax_reasons(self):
        long_ok = "a" * 33
        r1 = run_feature({"libc": [long_ok]})
        self.assertEqual(r1["entries"][0]["reasons"], ["value_length"])
        self.assertEqual(r1["entries"][0]["valid"], False)
        both = "A" * 33
        r2 = run_feature({"libc": [both]})
        self.assertEqual(r2["entries"][0]["reasons"], ["value_length", "value_syntax"])
        r3 = run_feature({"libc": [""]})
        self.assertEqual(r3["entries"][0]["reasons"], ["value_length"])
        self.assertEqual(run_feature({"libc": ["-abc"]})["entries"][0]["reasons"], ["value_syntax"])
        self.assertEqual(run_feature({"libc": ["a b"]})["entries"][0]["reasons"], ["value_syntax"])
        self.assertEqual(run_feature({"libc": ["a:b"]})["entries"][0]["reasons"], ["value_syntax"])
        self.assertEqual(run_feature({"libc": ["a" + chr(92) + "b"]})["entries"][0]["reasons"], ["value_syntax"])
        good = run_feature({"libc": ["a-b_c1", "0abc"]})
        self.assertEqual(good["valid_count"], 2)
        self.assertEqual(good["invalid_count"], 0)

    def test_payload_violations(self):
        bad = [None, [], "x", {}, {"max_entries": 8}, {"libc": None, "extra": 1}, {"libc": None, "max_entries": True}, {"libc": None, "max_entries": False}, {"libc": None, "max_entries": 0}, {"libc": None, "max_entries": 17}, {"libc": None, "max_entries": 8.0}, {"libc": None, "max_entries": "8"}, {"libc": None, "max_entries": None}, {"libc": None, "max_entries": [8]}, {"libc": None, "max_value_length": 0}, {"libc": None, "max_value_length": 65}, {"libc": None, "max_value_length": True}, {"libc": None, "max_value_length": 32.0}, {"libc": None, "max_value_length": "32"}]
        for p in bad:
            with self.subTest(payload=p):
                try:
                    run_feature(p)
                except ValueError as exc:
                    self.assertEqual(str(exc), PAYLOAD_ERROR)
                else:
                    self.fail("expected ValueError")
        try:
            run_feature({"libc": None, "extra": "UNIQUEPAYLOAD999"})
        except ValueError as exc:
            self.assertEqual(str(exc), PAYLOAD_ERROR)
            self.assertNotIn("UNIQUEPAYLOAD999", str(exc))
        else:
            self.fail("expected ValueError")

    def test_declaration_violations(self):
        bad = [{"libc": "glibc"}, {"libc": 123}, {"libc": True}, {"libc": 1.5}, {"libc": {"a": 1}}, {"libc": ["ok", 123]}, {"libc": ["ok", None]}, {"libc": ["ok", True]}, {"libc": ["a", "b", "c"], "max_entries": 2}, {"libc": ["a"] * 9}]
        for p in bad:
            with self.subTest(payload=p):
                try:
                    run_feature(p)
                except ValueError as exc:
                    self.assertEqual(str(exc), DECLARATION_ERROR)
                else:
                    self.fail("expected ValueError")
        try:
            run_feature({"libc": "UNIQUEDECL999"})
        except ValueError as exc:
            self.assertEqual(str(exc), DECLARATION_ERROR)
            self.assertNotIn("UNIQUEDECL999", str(exc))
        else:
            self.fail("expected ValueError")

    def test_fresh_deterministic(self):
        payload = {"libc": ["musl", "glibc"]}
        first = run_feature(payload)
        second = run_feature(payload)
        self.assertEqual(first, second)
        self.assertEqual(payload, {"libc": ["musl", "glibc"]})
        self.assertIsNot(first, second)
        self.assertIsNot(first["entries"], second["entries"])
        self.assertIsNot(first["entries"][0], second["entries"][0])
        self.assertIsNot(first["entries"][0]["reasons"], second["entries"][0]["reasons"])
        self.assertIsNot(first["kind"], second["kind"])
        first["entries"][0]["reasons"].append("mut")
        first["entries"].append({"value": "x", "valid": True, "reasons": []})
        self.assertEqual(second["entries"][0]["reasons"], [])
        self.assertEqual(len(second["entries"]), 2)
        custom = {"libc": ["b", "a"], "max_entries": 4, "max_value_length": 10}
        res = run_feature(custom)
        self.assertEqual([e["value"] for e in res["entries"]], ["a", "b"])

    def test_subclass_plain_copy(self):
        class S(str):
            pass
        payload = {"libc": [S("musl"), S("glibc")]}
        result = run_feature(payload)
        self.assertEqual(result["valid_count"], 2)
        for e in result["entries"]:
            self.assertIs(type(e["value"]), str)
            for r in e["reasons"]:
                self.assertIs(type(r), str)
        self.assertIs(type(result["kind"]), str)


if __name__ == "__main__":
    unittest.main()
