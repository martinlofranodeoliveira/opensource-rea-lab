import ast
import copy
import pathlib
import unittest

try:
    from src.npm_tarball_audit.features.engines_declaration_scan import run_feature
except ImportError:
    from npm_tarball_audit.features.engines_declaration_scan import run_feature

FIXED = "Invalid engines scan payload or budget"

def _source_path():
    here = pathlib.Path(__file__).resolve()
    cand = here.parent.parent / "src" / "npm_tarball_audit" / "features" / "engines_declaration_scan.py"
    if cand.is_file():
        return cand
    return pathlib.Path("src/npm_tarball_audit/features/engines_declaration_scan.py")

class TestCommunityEnginesDeclarationScan(unittest.TestCase):
    def assertInvalid(self, payload, snapshot=None):
        with self.assertRaises(ValueError) as ctx:
            run_feature(payload)
        self.assertEqual(str(ctx.exception), FIXED)
        if snapshot:
            self.assertNotIn(snapshot, str(ctx.exception))

    def test_absent_none_and_empty(self):
        for payload in ({"engines": None}, {"engines": {}}, {"engines": None, "max_entries": 16, "max_length": 256}, {"engines": {}, "max_entries": 2, "max_length": 10}):
            before = copy.deepcopy(payload)
            out = run_feature(payload)
            self.assertEqual(out, {"engines": [], "count": 0})
            self.assertEqual(set(out.keys()), {"engines", "count"})
            self.assertEqual(payload, before)

    def test_examples_from_contract(self):
        out = run_feature({"engines": {"node": ">=18", "npm": ">=9"}})
        self.assertEqual(out["count"], 2)
        self.assertEqual(out["engines"], [{"name": "node", "range": ">=18"}, {"name": "npm", "range": ">=9"}])
        self.assertEqual(run_feature({"engines": None}), {"engines": [], "count": 0})
        self.assertEqual(run_feature({"engines": {}, "max_entries": 16, "max_length": 256}), {"engines": [], "count": 0})

    def test_unsorted_sorted_verbatim_whitespace(self):
        payload = {"engines": {"npm": ">=9", "node": ">=18", "YARN": " 1.x "}}
        before = copy.deepcopy(payload)
        out = run_feature(payload)
        self.assertEqual([d["name"] for d in out["engines"]], ["YARN", "node", "npm"])
        self.assertEqual(out["engines"][0], {"name": "YARN", "range": " 1.x "})
        self.assertEqual(out["count"], 3)
        for entry in out["engines"]:
            self.assertEqual(set(entry.keys()), {"name", "range"})
        self.assertEqual(payload, before)
        out2 = run_feature({"engines": {"b": "2", "a": "2"}})
        self.assertEqual([d["name"] for d in out2["engines"]], ["a", "b"])
        out3 = run_feature({"engines": {"a": "2"}})
        self.assertEqual(out3["count"], 1)

    def test_sort_by_range_then_name(self):
        out = run_feature({"engines": {"node": ">=20", "npm": ">=9", "node2": ">=18"}})
        names = [(d["name"], d["range"]) for d in out["engines"]]
        self.assertEqual(names, sorted(names))

    def test_missing_extra_wrong_payload_types(self):
        self.assertInvalid({})
        self.assertInvalid({"max_entries": 16})
        self.assertInvalid({"engines": None, "extra": 1}, "extra")
        self.assertInvalid({"engines": None, "max_entries": 16, "oops": 1}, "oops")
        for bad in (None, [], "x", 123, 1.5, True):
            self.assertInvalid(bad)
        self.assertInvalid({"engines": ["node"]}, "node")
        self.assertInvalid({"engines": "node"}, "node")
        self.assertInvalid({"engines": 123})
        self.assertInvalid({"engines": True})

    def test_nonstring_names_ranges_and_lengths(self):
        self.assertInvalid({"engines": {123: ">=18"}}, "123")
        self.assertInvalid({"engines": {None: ">=18"}})
        self.assertInvalid({"engines": {"node": 18}}, "18")
        self.assertInvalid({"engines": {"node": None}})
        self.assertInvalid({"engines": {"node": True}})
        self.assertInvalid({"engines": {True: ">=18"}})
        self.assertInvalid({"engines": {"": ">=18"}})
        self.assertInvalid({"engines": {"node": ""}})
        ok = run_feature({"engines": {"a": "b"}, "max_length": 1, "max_entries": 16})
        self.assertEqual(ok, {"engines": [{"name": "a", "range": "b"}], "count": 1})
        self.assertInvalid({"engines": {"ab": "b"}, "max_length": 1, "max_entries": 16}, "ab")
        self.assertInvalid({"engines": {"a": "bc"}, "max_length": 1, "max_entries": 16}, "bc")
        long_name = "n" * 257
        self.assertInvalid({"engines": {long_name: "x"}}, long_name[:10])
        long_range = "r" * 300
        self.assertInvalid({"engines": {"node": long_range}}, long_range[:10])
        over = {"e" + str(i): "1" for i in range(17)}
        self.assertInvalid({"engines": over}, "e0")
        self.assertInvalid({"engines": {"a": "1", "b": "2"}, "max_entries": 1})

    def test_bad_budgets(self):
        for bad in (True, False, 0, -1, -16, 1.5, "16", None, [], {}):
            self.assertInvalid({"engines": None, "max_entries": bad})
            self.assertInvalid({"engines": None, "max_length": bad})
        self.assertInvalid({"engines": None, "max_entries": 16, "max_length": True})

    def test_str_subclass_no_coercion_no_transform(self):
        class S(str):
            pass
        k = S("  Node ")
        v = S(">=18")
        out = run_feature({"engines": {k: v}})
        self.assertEqual(out["count"], 1)
        self.assertEqual(out["engines"][0]["name"], "  Node ")
        self.assertEqual(out["engines"][0]["range"], ">=18")
        self.assertIs(type(out["engines"][0]["name"]), S)
        self.assertIs(type(out["engines"][0]["range"]), S)
        upper = run_feature({"engines": {"NPM": ">=9"}})
        self.assertEqual(upper["engines"][0]["name"], "NPM")
        weird = run_feature({"engines": {"node": "not-a-range!!!"}})
        self.assertEqual(weird["engines"][0]["range"], "not-a-range!!!")
        a = run_feature({"engines": {"e\u0301": "1"}})
        b = run_feature({"engines": {"\u00e9": "1"}})
        self.assertNotEqual(a["engines"][0]["name"], b["engines"][0]["name"])

    def test_repeated_calls_independent_no_mutation(self):
        payload = {"engines": {"npm": ">=9", "node": ">=18"}}
        before = copy.deepcopy(payload)
        first = run_feature(payload)
        second = run_feature(payload)
        self.assertEqual(first, second)
        self.assertIsNot(first, second)
        self.assertIsNot(first["engines"], second["engines"])
        self.assertIsNot(first["engines"][0], second["engines"][0])
        first["engines"].append({"name": "x", "range": "1"})
        first["engines"][0]["name"] = "MUT"
        self.assertNotEqual(first, second)
        third = run_feature(payload)
        self.assertEqual(third, second)
        self.assertEqual(payload, before)

    def test_core_static_constraints(self):
        text = _source_path().read_text(encoding="utf-8")
        tree = ast.parse(text)
        allowed = {"math", "re", "json", "unicodedata"}
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for a in node.names:
                    self.assertIn(a.name.split(".")[0], allowed)
            if isinstance(node, ast.ImportFrom):
                self.assertIn((node.module or "").split(".")[0], allowed)
            if isinstance(node, (ast.ClassDef, ast.AsyncFunctionDef)):
                self.fail("forbidden def")
            if isinstance(node, (ast.Global, ast.Nonlocal)):
                self.fail("forbidden scope")
            if isinstance(node, (ast.Yield, ast.YieldFrom, ast.Await)):
                self.fail("forbidden async/gen")
        for node in tree.body:
            if isinstance(node, ast.FunctionDef):
                self.assertEqual(len(node.decorator_list), 0)
                for d in node.args.defaults:
                    self.assertNotIsInstance(d, (ast.List, ast.Dict, ast.Set))
        forbidden_calls = {"eval", "exec", "compile", "open", "getattr", "setattr", "delattr", "__import__", "globals", "locals", "vars", "input", "print"}
        for node in ast.walk(tree):
            if isinstance(node, ast.Call):
                f = node.func
                if isinstance(f, ast.Name) and f.id in forbidden_calls:
                    self.fail("forbidden call " + f.id)
            if isinstance(node, ast.Assign):
                for t in node.targets:
                    if isinstance(t, ast.Attribute):
                        self.fail("attribute assignment")
            if isinstance(node, ast.Delete):
                for t in node.targets:
                    if isinstance(t, ast.Attribute):
                        self.fail("attribute deletion")

if __name__ == "__main__":
    unittest.main()
