import unittest

try:
    from src.npm_tarball_audit.features.author_contributors_scan import run_feature
except ImportError:
    from npm_tarball_audit.features.author_contributors_scan import run_feature

ERR = "Invalid author scan payload or budget"

class TestAuthorContributorsScan(unittest.TestCase):
    def test_author_string_verbatim(self):
        payload = {"author": "Jane Doe", "contributors": None}
        result = run_feature(payload)
        self.assertEqual(result["count"], 1)
        self.assertEqual(result["persons"], [{"name": "Jane Doe", "email": None, "url": None, "source": "author"}])
        self.assertEqual(set(result.keys()), {"persons", "count"})
        self.assertEqual(set(result["persons"][0].keys()), {"name", "email", "url", "source"})

    def test_whitespace_case_preserved(self):
        payload = {"author": "  Ada  LOVELACE  ", "contributors": None}
        result = run_feature(payload)
        self.assertEqual(result["persons"][0]["name"], "  Ada  LOVELACE  ")
        self.assertEqual(result["count"], 1)

    def test_author_dict_plus_contributors_dict(self):
        payload = {"author": {"name": "Jane Doe", "email": "jane@example.com"}, "contributors": [{"name": "John Smith", "url": "https://example.com/john"}]}
        result = run_feature(payload)
        self.assertEqual(result["count"], 2)
        self.assertEqual(result["persons"][0], {"name": "Jane Doe", "email": "jane@example.com", "url": None, "source": "author"})
        self.assertEqual(result["persons"][1], {"name": "John Smith", "email": None, "url": "https://example.com/john", "source": "contributors"})

    def test_empty_inputs(self):
        payload = {"author": None, "contributors": []}
        r1 = run_feature(payload)
        self.assertEqual(r1, {"persons": [], "count": 0})
        r2 = run_feature(payload)
        self.assertIsNot(r1, r2)
        self.assertIsNot(r1["persons"], r2["persons"])

    def test_sorting_and_duplicates(self):
        payload = {"author": None, "contributors": ["bob", "Alice", "bob"]}
        result = run_feature(payload)
        names = [p["name"] for p in result["persons"]]
        self.assertEqual(names, ["Alice", "bob", "bob"])
        self.assertEqual(result["count"], 3)
        payload2 = {"author": None, "contributors": [{"name": "Sam", "url": "z"}, {"name": "Sam", "email": "a@x.com"}, {"name": "Sam"}]}
        result2 = run_feature(payload2)
        self.assertEqual(result2["persons"][0], {"name": "Sam", "email": None, "url": None, "source": "contributors"})
        self.assertEqual(result2["persons"][1], {"name": "Sam", "email": None, "url": "z", "source": "contributors"})
        self.assertEqual(result2["persons"][2], {"name": "Sam", "email": "a@x.com", "url": None, "source": "contributors"})

    def test_source_ordering(self):
        payload = {"author": "Zed", "contributors": ["Aaron"]}
        result = run_feature(payload)
        self.assertEqual([p["source"] for p in result["persons"]], ["author", "contributors"])

    def test_errors_fixed_message(self):
        with self.assertRaises(ValueError) as cm:
            run_feature({"author": None, "contributors": ["a"] * 33})
        self.assertEqual(str(cm.exception), ERR)
        with self.assertRaises(ValueError) as cm:
            run_feature({"author": "x" * 513, "contributors": None})
        self.assertEqual(str(cm.exception), ERR)
        with self.assertRaises(ValueError) as cm:
            run_feature({"author": None})
        self.assertEqual(str(cm.exception), ERR)
        with self.assertRaises(ValueError) as cm:
            run_feature({"author": None, "contributors": None, "extra": 1})
        self.assertEqual(str(cm.exception), ERR)
        with self.assertRaises(ValueError) as cm:
            run_feature({"author": None, "contributors": [{"email": "a@x.com"}]})
        self.assertEqual(str(cm.exception), ERR)
        with self.assertRaises(ValueError) as cm:
            run_feature({"author": None, "contributors": [{"name": "A", "nickname": "B"}]})
        self.assertEqual(str(cm.exception), ERR)
        with self.assertRaises(ValueError) as cm:
            run_feature({"author": "", "contributors": None})
        self.assertEqual(str(cm.exception), ERR)
        with self.assertRaises(ValueError) as cm:
            run_feature({"author": None, "contributors": None, "max_entries": True})
        self.assertEqual(str(cm.exception), ERR)
        with self.assertRaises(ValueError) as cm:
            run_feature({"author": None, "contributors": None, "max_length": 0})
        self.assertEqual(str(cm.exception), ERR)
        with self.assertRaises(ValueError) as cm:
            run_feature({"author": 123, "contributors": None})
        self.assertEqual(str(cm.exception), ERR)
        with self.assertRaises(ValueError) as cm:
            run_feature({"author": None, "contributors": [123]})
        self.assertEqual(str(cm.exception), ERR)

    def test_budgets_respected(self):
        payload = {"author": None, "contributors": ["a", "b"], "max_entries": 2, "max_length": 2}
        result = run_feature(payload)
        self.assertEqual(result["count"], 2)
        with self.assertRaises(ValueError) as cm:
            run_feature({"author": None, "contributors": ["a", "b", "c"], "max_entries": 2})
        self.assertEqual(str(cm.exception), ERR)
        with self.assertRaises(ValueError) as cm:
            run_feature({"author": "abc", "contributors": None, "max_length": 2})
        self.assertEqual(str(cm.exception), ERR)

    def test_str_subclass_no_coercion(self):
        class MyStr(str):
            pass
        name = MyStr("Alice")
        payload = {"author": name, "contributors": [MyStr("Bob")]}
        result = run_feature(payload)
        self.assertEqual(result["count"], 2)
        self.assertIsInstance(result["persons"][0]["name"], str)
        self.assertIsInstance(result["persons"][1]["name"], str)
        self.assertEqual(result["persons"][0]["name"], "Alice")
        self.assertEqual(result["persons"][1]["name"], "Bob")
        self.assertIsInstance(result["persons"][0]["name"], MyStr)

    def test_inputs_not_mutated_and_fresh(self):
        payload = {"author": {"name": "A", "email": "e@x.com"}, "contributors": [{"name": "B"}, "C"]}
        snapshot = {"author": {"name": "A", "email": "e@x.com"}, "contributors": [{"name": "B"}, "C"]}
        r1 = run_feature(payload)
        self.assertEqual(payload, snapshot)
        r2 = run_feature(payload)
        self.assertEqual(r1, r2)
        self.assertIsNot(r1, r2)
        self.assertIsNot(r1["persons"], r2["persons"])
        self.assertIsNot(r1["persons"][0], r2["persons"][0])
        self.assertIsNot(r1["persons"], payload["contributors"])
        r1["persons"].append({"name": "X", "email": None, "url": None, "source": "author"})
        self.assertEqual(r2["count"], 3 if False else len(r2["persons"]))
        self.assertNotEqual(len(r1["persons"]), len(r2["persons"]))

    def test_no_validation_url_email(self):
        payload = {"author": {"name": "N", "email": "not-an-email", "url": ":::not a url:::"}, "contributors": [{"name": "C", "email": "   ", "url": "http://[invalid"}]}
        result = run_feature(payload)
        self.assertEqual(result["count"], 2)
        by_name = {p["name"]: p for p in result["persons"]}
        self.assertEqual(by_name["N"]["email"], "not-an-email")
        self.assertEqual(by_name["N"]["url"], ":::not a url:::")
        self.assertEqual(by_name["C"]["email"], "   ")

if __name__ == "__main__":
    unittest.main()
