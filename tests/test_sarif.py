"""Synthetic contract checks for sanitized, pure SARIF interchange."""

import copy
import json
import unittest
from unittest.mock import patch

from npm_tarball_audit.sarif import to_sarif


def report(findings=None, **changes):
    return {"schema": "npm-tarball-audit/v1", "status": "pass",
            "package_executed": False, "files_extracted": False,
            "findings": [] if findings is None else findings, **changes}


def finding(code="unsafe_path", level="error", **changes):
    return {"code": code, "level": level, "message": "Synthetic original detail", **changes}


def result_text(member):
    return to_sarif(report([finding(member=member)]))["runs"][0]["results"][0]["message"]["text"]


class SarifTests(unittest.TestCase):
    def test_empty_run_has_required_schema_and_offline_scope(self):
        document = to_sarif(report())
        self.assertEqual(set(document), {"$schema", "version", "runs"})
        self.assertEqual(document["version"], "2.1.0")
        self.assertEqual(document["$schema"],
                         "https://docs.oasis-open.org/sarif/sarif/v2.1.0/errata01/os/schemas/sarif-schema-2.1.0.json")
        self.assertEqual(len(document["runs"]), 1)
        run = document["runs"][0]
        self.assertEqual(run["tool"]["driver"], {"name": "npm-tarball-audit", "rules": []})
        self.assertEqual(run["results"], [])
        self.assertIs(run["properties"]["originalReportRequired"], True)
        self.assertIn("offline", run["properties"]["scope"])
        self.assertIn("not a malware verdict", run["properties"]["scope"])

    def test_rule_order_stable_ids_and_results_preserve_input_order(self):
        document = to_sarif(report([finding("z_check", "warning"), finding("a_check"),
                                    finding("z_check")], status="warning"))
        run = document["runs"][0]
        self.assertEqual([rule["id"] for rule in run["tool"]["driver"]["rules"]],
                         ["NTA/a_check", "NTA/z_check"])
        self.assertEqual([(item["ruleId"], item["ruleIndex"], item["level"])
                          for item in run["results"]],
                         [("NTA/z_check", 1, "warning"), ("NTA/a_check", 0, "error"),
                          ("NTA/z_check", 1, "error")])
        self.assertEqual(document, to_sarif(report([finding("z_check", "warning"),
                                                   finding("a_check"), finding("z_check")],
                                                  status="warning")))
        self.assertEqual(json.loads(json.dumps(document, ensure_ascii=True)), document)

    def test_unknown_valid_codes_and_status_are_not_reinterpreted(self):
        for status in ("pass", "warning", "fail"):
            with self.subTest(status=status):
                data = to_sarif(report([finding("future9_check2")], status=status))
                self.assertEqual(data["runs"][0]["results"][0]["ruleId"], "NTA/future9_check2")

    def test_original_messages_and_all_extra_metadata_are_absent(self):
        marker = "SYNTHETIC_PRIVATE_MARKER"
        original = report([finding(message=f"OSError: /home/{marker}/archive.tgz",
                                   detail={"url": f"https://{marker}.invalid"})],
                          archive=f"/tmp/{marker}", package={"name": marker},
                          inventory=[{"path": marker}], arbitrary=object())
        text = json.dumps(to_sarif(original))
        self.assertNotIn(marker, text)
        self.assertNotIn("OSError", text)
        self.assertNotIn("original detail", text)

    def test_no_locations_invocations_artifacts_or_untrusted_urls(self):
        data = to_sarif(report([finding(member="https://synthetic.invalid/path")]))
        prohibited = {"locations", "physicalLocation", "logicalLocations", "relatedLocations",
                      "artifacts", "artifactLocation", "uri", "uriBaseId",
                      "originalUriBaseIds", "invocations", "snippets", "markdown"}
        def check(value):
            if isinstance(value, dict):
                self.assertTrue(prohibited.isdisjoint(value))
                for item in value.values():
                    check(item)
            elif isinstance(value, list):
                for item in value:
                    check(item)
        check(data)
        self.assertNotIn("synthetic.invalid", json.dumps(data))

    def test_safe_canonical_paths_and_optional_single_trailing_slash(self):
        for path in ("package", "package/", "package/index.js", "package/sub/file.js/"):
            with self.subTest(path=path):
                self.assertIn(json.dumps(path, ensure_ascii=True), result_text(path))

    def test_unsafe_paths_use_fixed_omission_without_original_value(self):
        for path in ("", "/package/a", "../marker", "package/../marker", "package/./marker",
                     "package//marker", "package/marker//", "package2/marker", "package\\marker",
                     "package/marker:stream", "C:/package/marker", "file:///marker",
                     "package/marker\x00", "package/marker\n", "package/marker\x7f"):
            with self.subTest(path=repr(path)):
                text = result_text(path)
                self.assertTrue(text.endswith("Member: unsafe member omitted."))
                self.assertNotIn("marker", text)

    def test_unicode_bidi_formats_surrogates_and_sarif_syntax_are_ascii_escaped(self):
        path = "package/á\u202e\u2066\ud800<>&{}[]().js"
        text = result_text(path)
        self.assertTrue(text.isascii())
        for value in ("\\u00e1", "\\u202e", "\\u2066", "\\ud800"):
            self.assertIn(value, text)
        for character in "<>&{}[]()":
            self.assertNotIn(character, text)
            self.assertIn(f"\\u{ord(character):04x}", text)
        json.dumps(to_sarif(report([finding(member=path)])), ensure_ascii=True)

    def test_display_budget_is_after_quoting_escaping_and_oversize_first(self):
        exact = "package/" + "a" * 230
        self.assertEqual(len(json.dumps(exact)), 240)
        self.assertIn(json.dumps(exact), result_text(exact))
        for path in (exact + "a", "x" * 239, "package/" + "é" * 39,
                     "package/" + "[" * 39):
            with self.subTest(path=repr(path[:20])):
                self.assertTrue(result_text(path).endswith(
                    "Member: member omitted: display exceeds 240 characters."))
        self.assertTrue(result_text("x" * 238).endswith("Member: unsafe member omitted."))
        self.assertTrue(result_text("package/" + "a" * 1_000_000).endswith(
            "Member: member omitted: display exceeds 240 characters."))

    def test_inputs_are_unmodified_and_outputs_have_fresh_containers(self):
        original = report([finding(member="package/index.js")], extra={"nested": []})
        before = copy.deepcopy(original)
        first, second = to_sarif(original), to_sarif(original)
        self.assertEqual(original, before)
        first["runs"][0]["results"][0]["message"]["text"] = "Changed"
        first["runs"][0]["tool"]["driver"]["rules"].clear()
        first["runs"][0]["properties"].clear()
        self.assertEqual(original, before)
        self.assertEqual(second, to_sarif(original))

    def test_no_file_network_or_subprocess_effects(self):
        with patch("builtins.open", side_effect=AssertionError("file access")), \
                patch("socket.socket", side_effect=AssertionError("network access")), \
                patch("subprocess.Popen", side_effect=AssertionError("subprocess")):
            self.assertEqual(to_sarif(report([finding()]))["version"], "2.1.0")

    def test_required_report_types_and_values_are_not_coerced(self):
        invalid = [None, True, [], "{}", {}, report(schema="future/v2"), report(status=[]),
                   report(status="PASS"), report(package_executed=0), report(files_extracted=0),
                   report(package_executed=True), {**report(), "findings": None}, report(findings=()),
                   report(findings={})]
        for key in ("schema", "status", "package_executed", "files_extracted", "findings"):
            value = report()
            del value[key]
            invalid.append(value)
        for value in invalid:
            with self.subTest(value=repr(value)), self.assertRaises(ValueError):
                to_sarif(value)

    def test_invalid_finding_values_are_generic_value_errors(self):
        invalid = [None, [], "marker", {}, finding(level="note"), finding(level=[]),
                   finding(code=None), finding(code=2), finding(code=""), finding(code="_a"),
                   finding(code="a_"), finding(code="a__b"), finding(code="A"),
                   finding(code="á"), finding(code="a/b"), finding(code="a" * 65),
                   finding(message=""), finding(message=" \t\n"), finding(message=None),
                   finding(message=2), finding(member=None), finding(member=[]) ]
        for key in ("level", "code", "message"):
            value = finding()
            del value[key]
            invalid.append(value)
        for value in invalid:
            with self.subTest(value=repr(value)), self.assertRaises(ValueError) as failure:
                to_sarif(report([value], marker="SYNTHETIC_SECRET"))
            self.assertEqual(str(failure.exception), "Invalid or unbounded offline audit report")

    def test_finding_limit_is_inclusive_positive_integer_and_bool_is_rejected(self):
        data = report([finding(), finding()])
        self.assertEqual(len(to_sarif(data, max_findings=2)["runs"][0]["results"]), 2)
        with self.assertRaises(ValueError):
            to_sarif(data, max_findings=1)
        for limit in (True, False, 0, -1, 1.0, "2", None):
            with self.subTest(limit=limit), self.assertRaises(ValueError):
                to_sarif(report(), max_findings=limit)
        many = report([finding()] * 20000)
        self.assertEqual(len(to_sarif(many)["runs"][0]["results"]), 20000)
        many["findings"].append(finding())
        with self.assertRaises(ValueError):
            to_sarif(many)


if __name__ == "__main__":
    unittest.main()
