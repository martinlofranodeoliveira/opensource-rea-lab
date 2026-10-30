import copy
import unittest
try:
    from npm_tarball_audit.features.claim_evidence_presence_check import run_feature
except ImportError:
    from src.npm_tarball_audit.features.claim_evidence_presence_check import run_feature
PAYLOAD_ERROR = "Invalid entry presence payload or budget"
CLAIM_ERROR = "Invalid entrypoint claim declaration"
EVIDENCE_ERROR = "Invalid inventory evidence declaration"
class CommunityClaimEvidencePresenceCheckTest(unittest.TestCase):
    def test_rejects_non_dict_payload(self):
        for bad in [None, True, False, 0, 3.5, "x", [], ["a"], ("a",)]:
            with self.assertRaises(ValueError) as ctx:
                run_feature(bad)
            self.assertEqual(str(ctx.exception), PAYLOAD_ERROR)
    def test_rejects_missing_and_extra_keys(self):
        with self.assertRaises(ValueError) as ctx:
            run_feature({"targets": []})
        self.assertEqual(str(ctx.exception), PAYLOAD_ERROR)
        with self.assertRaises(ValueError) as ctx:
            run_feature({"inventory": []})
        self.assertEqual(str(ctx.exception), PAYLOAD_ERROR)
        with self.assertRaises(ValueError) as ctx:
            run_feature({})
        self.assertEqual(str(ctx.exception), PAYLOAD_ERROR)
        with self.assertRaises(ValueError) as ctx:
            run_feature({"targets": [], "inventory": [], "extra": 1})
        self.assertEqual(str(ctx.exception), PAYLOAD_ERROR)
        self.assertNotIn("extra", str(ctx.exception))
    def test_rejects_bad_budgets(self):
        bad_values = [True, False, 0, -1, 65, 100, 1.0, 32.0, "32", [], {}, None]
        for bad in bad_values:
            with self.assertRaises(ValueError) as ctx:
                run_feature({"targets": [], "inventory": [], "max_targets": bad})
            self.assertEqual(str(ctx.exception), PAYLOAD_ERROR)
        bad_files = [True, False, 0, -5, 2001, 5000, 1.5, "1000", [], {}, None]
        for bad in bad_files:
            with self.assertRaises(ValueError) as ctx:
                run_feature({"targets": [], "inventory": [], "max_files": bad})
            self.assertEqual(str(ctx.exception), PAYLOAD_ERROR)
        with self.assertRaises(ValueError) as ctx:
            run_feature({"targets": [], "inventory": [], "max_targets": 0})
        self.assertEqual(str(ctx.exception), PAYLOAD_ERROR)
        self.assertNotIn("0", str(ctx.exception))
    def test_accepts_empty_targets(self):
        payload = {"targets": [], "inventory": ["package/index.js"]}
        before = copy.deepcopy(payload)
        result = run_feature(payload)
        self.assertEqual(payload, before)
        self.assertEqual(list(result.keys()), ["total", "present_count", "missing_count", "present", "missing", "is_complete"])
        self.assertEqual(result["total"], 0)
        self.assertEqual(result["present_count"], 0)
        self.assertEqual(result["missing_count"], 0)
        self.assertEqual(result["present"], [])
        self.assertEqual(result["missing"], [])
        self.assertIs(result["is_complete"], True)
        self.assertIs(type(result["total"]), int)
    def test_reports_present_and_missing_sorted(self):
        payload = {"targets": ["package/index.js", "package/cli.js"], "inventory": ["package/README.md", "package/cli.js", "package/index.js"]}
        result = run_feature(payload)
        self.assertEqual(result["total"], 2)
        self.assertEqual(result["present"], ["package/cli.js", "package/index.js"])
        self.assertEqual(result["present_count"], 2)
        self.assertEqual(result["missing"], [])
        self.assertEqual(result["missing_count"], 0)
        self.assertIs(result["is_complete"], True)
        payload2 = {"targets": ["package/index.js", "package/missing.js"], "inventory": ["package/index.js"]}
        result2 = run_feature(payload2)
        self.assertEqual(result2["total"], 2)
        self.assertEqual(result2["present"], ["package/index.js"])
        self.assertEqual(result2["present_count"], 1)
        self.assertEqual(result2["missing"], ["package/missing.js"])
        self.assertEqual(result2["missing_count"], 1)
        self.assertIs(result2["is_complete"], False)
    def test_rejects_non_string_and_lengths(self):
        for bad in [123, None, True, 3.5, [], {}, b"x"]:
            with self.assertRaises(ValueError) as ctx:
                run_feature({"targets": [bad], "inventory": []})
            self.assertEqual(str(ctx.exception), CLAIM_ERROR)
            with self.assertRaises(ValueError) as ctx2:
                run_feature({"targets": [], "inventory": [bad]})
            self.assertEqual(str(ctx2.exception), EVIDENCE_ERROR)
        with self.assertRaises(ValueError) as ctx:
            run_feature({"targets": [""] , "inventory": []})
        self.assertEqual(str(ctx.exception), CLAIM_ERROR)
        with self.assertRaises(ValueError) as ctx:
            run_feature({"targets": [], "inventory": [""]})
        self.assertEqual(str(ctx.exception), EVIDENCE_ERROR)
        long_value = "a" * 257
        with self.assertRaises(ValueError) as ctx:
            run_feature({"targets": [long_value], "inventory": []})
        self.assertEqual(str(ctx.exception), CLAIM_ERROR)
        with self.assertRaises(ValueError) as ctx:
            run_feature({"targets": [], "inventory": [long_value]})
        self.assertEqual(str(ctx.exception), EVIDENCE_ERROR)
        with self.assertRaises(ValueError) as ctx:
            run_feature({"targets": "package/index.js", "inventory": []})
        self.assertEqual(str(ctx.exception), CLAIM_ERROR)
        with self.assertRaises(ValueError) as ctx:
            run_feature({"targets": [], "inventory": "package/index.js"})
        self.assertEqual(str(ctx.exception), EVIDENCE_ERROR)
    def test_rejects_duplicates(self):
        with self.assertRaises(ValueError) as ctx:
            run_feature({"targets": ["a.js", "a.js"], "inventory": []})
        self.assertEqual(str(ctx.exception), CLAIM_ERROR)
        with self.assertRaises(ValueError) as ctx:
            run_feature({"targets": [], "inventory": ["a.js", "a.js"]})
        self.assertEqual(str(ctx.exception), EVIDENCE_ERROR)
    def test_preserves_input_fresh_and_deterministic(self):
        payload = {"targets": ["b.js", "A.js", "a.js"], "inventory": ["a.js", "b.js", "A.js", "extra.js"]}
        snapshot = copy.deepcopy(payload)
        first = run_feature(payload)
        second = run_feature(payload)
        self.assertEqual(payload, snapshot)
        self.assertEqual(first, second)
        self.assertIsNot(first, second)
        self.assertIsNot(first["present"], second["present"])
        self.assertIsNot(first["missing"], second["missing"])
        self.assertEqual(first["present"], ["A.js", "a.js", "b.js"])
        for item in first["present"] + first["missing"]:
            self.assertIs(type(item), str)
        first["present"].append("mutated.js")
        third = run_feature(payload)
        self.assertNotIn("mutated.js", third["present"])
    def test_exact_case_sensitive_no_trimming(self):
        result = run_feature({"targets": ["Package/Index.js"], "inventory": ["package/index.js"]})
        self.assertEqual(result["present"], [])
        self.assertEqual(result["missing"], ["Package/Index.js"])
        self.assertIs(result["is_complete"], False)
        result2 = run_feature({"targets": [" package/index.js"], "inventory": ["package/index.js"]})
        self.assertEqual(result2["missing"], [" package/index.js"])
        result3 = run_feature({"targets": ["*.js"], "inventory": ["package/index.js"]})
        self.assertEqual(result3["missing"], ["*.js"])
        self.assertIs(result3["is_complete"], False)
if __name__ == "__main__":
    unittest.main()
