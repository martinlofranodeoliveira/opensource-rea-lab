import copy
import unittest

try:
    from npm_tarball_audit.features.findings_tally_scan import run_feature
except ImportError:
    from src.npm_tarball_audit.features.findings_tally_scan import run_feature

_PAYLOAD_MSG = "Invalid findings payload or budget"
_RECORD_MSG = "Invalid finding record"


class FindingsTallyScanTest(unittest.TestCase):
    def test_empty_findings(self):
        payload = {"findings": []}
        before = copy.deepcopy(payload)
        out = run_feature(payload)
        self.assertEqual(payload, before)
        self.assertEqual(out["total"], 0)
        self.assertEqual(out["errors"], 0)
        self.assertEqual(out["warnings"], 0)
        self.assertEqual(out["by_code"], [])
        self.assertEqual(list(out.keys()), ["total", "errors", "warnings", "by_code"])
        self.assertIs(type(out["total"]), int)
        self.assertIs(type(out["errors"]), int)
        self.assertIs(type(out["warnings"]), int)
        self.assertIs(type(out["by_code"]), list)
        out2 = run_feature({"findings": []})
        self.assertIsNot(out, out2)
        self.assertIsNot(out["by_code"], out2["by_code"])

    def test_mixed_severities_same_code(self):
        payload = {"findings": [{"code": "manifest_identity", "severity": "error"}, {"code": "manifest_identity", "severity": "warning"}]}
        before = copy.deepcopy(payload)
        out = run_feature(payload)
        self.assertEqual(payload, before)
        self.assertEqual(out["total"], 2)
        self.assertEqual(out["errors"], 1)
        self.assertEqual(out["warnings"], 1)
        self.assertEqual(len(out["by_code"]), 1)
        entry = out["by_code"][0]
        self.assertEqual(list(entry.keys()), ["code", "count", "errors", "warnings"])
        self.assertEqual(entry["code"], "manifest_identity")
        self.assertIs(type(entry["code"]), str)
        self.assertEqual(entry["count"], 2)
        self.assertEqual(entry["errors"], 1)
        self.assertEqual(entry["warnings"], 1)

    def test_multiple_codes_sorted_ascii(self):
        payload = {"findings": [{"code": "manifest_version", "severity": "error"}, {"code": "identity_mismatch", "severity": "warning"}, {"code": "manifest_identity", "severity": "error"}], "max_entries": 256}
        before = copy.deepcopy(payload)
        out = run_feature(payload)
        self.assertEqual(payload, before)
        self.assertEqual(out["total"], 3)
        self.assertEqual(out["errors"], 2)
        self.assertEqual(out["warnings"], 1)
        codes = [e["code"] for e in out["by_code"]]
        self.assertEqual(codes, ["identity_mismatch", "manifest_identity", "manifest_version"])
        self.assertEqual(codes, sorted(codes))
        for e in out["by_code"]:
            self.assertEqual(e["count"], e["errors"] + e["warnings"])
        m = {e["code"]: e for e in out["by_code"]}
        self.assertEqual(m["identity_mismatch"]["warnings"], 1)
        self.assertEqual(m["identity_mismatch"]["errors"], 0)
        self.assertEqual(m["manifest_identity"]["errors"], 1)

    def test_payload_errors(self):
        good = {"code": "a", "severity": "error"}
        cases = []
        cases.append([])
        cases.append(None)
        cases.append("x")
        cases.append(42)
        cases.append({})
        cases.append({"max_entries": 10})
        cases.append({"findings": [], "max_entries": 10, "extra": 1})
        cases.append({"findings": [], "unknown": 1})
        cases.append({"findings": [good], "max_entries": True})
        cases.append({"findings": [good], "max_entries": False})
        cases.append({"findings": [good], "max_entries": 1.0})
        cases.append({"findings": [good], "max_entries": "10"})
        cases.append({"findings": [good], "max_entries": None})
        cases.append({"findings": [good], "max_entries": []})
        cases.append({"findings": [good], "max_entries": {}})
        cases.append({"findings": [good], "max_entries": 0})
        cases.append({"findings": [good], "max_entries": 501})
        cases.append({"findings": [good], "max_entries": -1})
        cases.append({"findings": "nope"})
        cases.append({"findings": {}})
        cases.append({"findings": [good, good], "max_entries": 1})
        for p in cases:
            with self.assertRaises(ValueError) as cm:
                run_feature(p)
            self.assertEqual(str(cm.exception), _PAYLOAD_MSG)

    def test_payload_string_subclass_budget_rejected(self):
        class MyStr(str):
            pass
        good = {"code": "a", "severity": "error"}
        with self.assertRaises(ValueError) as cm:
            run_feature({"findings": [good], "max_entries": MyStr("10")})
        self.assertEqual(str(cm.exception), _PAYLOAD_MSG)

    def test_record_errors(self):
        def expect_record(rec):
            with self.assertRaises(ValueError) as cm:
                run_feature({"findings": [rec]})
            self.assertEqual(str(cm.exception), _RECORD_MSG)
        expect_record([])
        expect_record(None)
        expect_record("x")
        expect_record({"code": "a"})
        expect_record({"severity": "error"})
        expect_record({"code": "a", "severity": "error", "extra": 1})
        expect_record({"code": 1, "severity": "error"})
        expect_record({"code": None, "severity": "error"})
        expect_record({"code": "", "severity": "error"})
        expect_record({"code": "x" * 65, "severity": "error"})
        expect_record({"code": "bad code!", "severity": "error"})
        expect_record({"code": "/lead", "severity": "error"})
        expect_record({"code": "trail/", "severity": "error"})
        expect_record({"code": "a//b", "severity": "error"})
        expect_record({"code": "a", "severity": "Error"})
        expect_record({"code": "a", "severity": "WARNING"})
        expect_record({"code": "a", "severity": "error "})
        expect_record({"code": "a", "severity": 1})
        expect_record({"code": "a", "severity": None})
        class MyStr(str):
            pass
        with self.assertRaises(ValueError) as cm:
            run_feature({"findings": [{"code": "a", "severity": MyStr("error")}]})
        self.assertEqual(str(cm.exception), _RECORD_MSG)

    def test_code_subclass_accepted_as_plain_str(self):
        class MyStr(str):
            pass
        payload = {"findings": [{"code": MyStr("ok_code-1/a"), "severity": "warning"}]}
        out = run_feature(payload)
        self.assertEqual(out["total"], 1)
        self.assertEqual(out["by_code"][0]["code"], "ok_code-1/a")
        self.assertIs(type(out["by_code"][0]["code"]), str)

    def test_preserves_input_and_fresh_outputs(self):
        payload = {"findings": [{"code": "b", "severity": "error"}, {"code": "a", "severity": "warning"}]}
        before = copy.deepcopy(payload)
        out1 = run_feature(payload)
        self.assertEqual(payload, before)
        self.assertEqual(list(out1.keys()), ["total", "errors", "warnings", "by_code"])
        for e in out1["by_code"]:
            self.assertEqual(list(e.keys()), ["code", "count", "errors", "warnings"])
        out2 = run_feature(payload)
        self.assertEqual(out1, out2)
        self.assertIsNot(out1, out2)
        self.assertIsNot(out1["by_code"], out2["by_code"])
        self.assertIsNot(out1["by_code"][0], out2["by_code"][0])
        out1["by_code"][0]["count"] = 999
        out1["by_code"].append({"code": "z", "count": 1, "errors": 1, "warnings": 0})
        out3 = run_feature(payload)
        self.assertEqual(out3, out2)
        self.assertEqual(payload, before)
        bad = {"findings": [{"code": "x", "severity": "nope"}]}
        bad_before = copy.deepcopy(bad)
        with self.assertRaises(ValueError):
            run_feature(bad)
        self.assertEqual(bad, bad_before)


if __name__ == "__main__":
    unittest.main()
