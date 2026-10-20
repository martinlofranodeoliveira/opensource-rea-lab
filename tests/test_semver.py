"""Synthetic regression fixtures for the bounded, data-only SemVer parser."""

import unittest

from npm_tarball_audit.semver import parse_semver


class PlainVersionString(str):
    pass


class PlainLength(int):
    pass


class RefuseCoercion:
    def __str__(self):
        raise AssertionError("The parser must not coerce arbitrary objects")


class SemverTests(unittest.TestCase):
    def assert_invalid(self, text, **kwargs):
        with self.assertRaises(ValueError) as raised:
            parse_semver(text, **kwargs)
        error = raised.exception
        self.assertEqual(str(error), "Invalid semantic version or length budget")
        self.assertIsNone(error.__cause__)
        if not error.__suppress_context__:
            self.assertIsNone(error.__context__)

    def test_core_fields_are_exact_decimal_strings(self):
        for text, components in (("0.0.0", ["0", "0", "0"]),
                                 ("12.34.56", ["12", "34", "56"]),
                                 ("100.200.300", ["100", "200", "300"])):
            with self.subTest(version=text):
                result = parse_semver(text)
                self.assertEqual(result, dict(zip(
                    ("major", "minor", "patch", "prerelease", "build"),
                    components + [[], []])))
                self.assertTrue(all(type(result[key]) is str
                                    for key in ("major", "minor", "patch")))

    def test_extensions_keep_case_spelling_and_identifier_order(self):
        result = parse_semver("12.34.56-RC.2.preview+Build.0007.AMD64")
        self.assertEqual(result, {"major": "12", "minor": "34", "patch": "56",
            "prerelease": ["RC", "2", "preview"], "build": ["Build", "0007", "AMD64"]})

    def test_hyphens_in_build_do_not_create_a_prerelease(self):
        for build in ("artifact-linux", "linux-x86-64", "-", "--", "01-nightly"):
            with self.subTest(build=build):
                result = parse_semver("2.4.6+" + build)
                self.assertEqual(result["prerelease"], [])
                self.assertEqual(result["build"], [build])
        result = parse_semver("2.4.6-a-b+x-y")
        self.assertEqual(result["prerelease"], ["a-b"])
        self.assertEqual(result["build"], ["x-y"])

    def test_identifier_alphabet_and_nonnumeric_leading_zeroes(self):
        alphabet = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789-"
        result = parse_semver("2.4.6-" + alphabet + ".00rc.03-.---+" + alphabet)
        self.assertEqual(result["prerelease"], [alphabet, "00rc", "03-", "---"])
        self.assertEqual(result["build"], [alphabet])

    def test_core_numbers_cannot_have_leading_zeroes(self):
        for text in ("02.4.6", "2.04.6", "2.4.06", "000.4.6", "0.00.6", "0.0.00"):
            with self.subTest(version=text):
                self.assert_invalid(text)

    def test_numeric_prerelease_and_build_have_different_zero_rules(self):
        result = parse_semver("2.4.6-0.21.308+00.021.000308")
        self.assertEqual(result["prerelease"], ["0", "21", "308"])
        self.assertEqual(result["build"], ["00", "021", "000308"])
        for suffix in ("01", "001", "preview.02", "03.preview", "x.000.x"):
            with self.subTest(prerelease=suffix):
                self.assert_invalid("2.4.6-" + suffix)

    def test_core_requires_exactly_three_unsigned_decimal_components(self):
        for text in ("", "2", "2.4", "2.4.6.8", ".4.6", "2..6", "2.4.",
                     "2.+4.6", "2.-4.6", "-2.4.6", "2.4e1.6", "2.0x4.6", "two.4.6"):
            with self.subTest(version=text):
                self.assert_invalid(text)

    def test_extensions_need_nonempty_identifiers_and_one_build_separator(self):
        for text in ("2.4.6-", "2.4.6+", "2.4.6-.preview", "2.4.6-preview.",
                     "2.4.6-preview..rc", "2.4.6+.linux", "2.4.6+linux.",
                     "2.4.6+linux..arm", "2.4.6-+linux", "2.4.6-rc+", "2.4.6+linux+arm"):
            with self.subTest(version=text):
                self.assert_invalid(text)
        for token in ("rc_1", "rc/1", "rc:1", "rc@1", "rc%31", "rc=1", "rc,1", "rc*1"):
            for separator in ("-", "+"):
                with self.subTest(token=token, separator=separator):
                    self.assert_invalid("2.4.6" + separator + token)

    def test_versions_are_not_tags_ranges_or_normalized_text(self):
        for text in ("v2.4.6", "V2.4.6", "latest", "next", "=2.4.6", "^2.4.6", "~2.4.6",
                     ">2.4.6", "2.4.x", "2.*.6", "2.4.6 || 3.0.0", "2.4.6 - 3.0.0",
                     " 2.4.6", "2.4.6 ", "\t2.4.6", "2.4.6\n", "2.4.6\r\n", "2.4.6-rc 1"):
            with self.subTest(version=repr(text)):
                self.assert_invalid(text)

    def test_only_ascii_digits_and_ascii_identifier_characters_are_allowed(self):
        for text in ("２.4.6", "2.٤.6", "2.4.𝟞", "2.4.6-²", "2.4.6+éclair",
                     "2.4.6-rc.１", "2.4.6+\u202dabc", "2.4.6-rc\0", "2.4.6+build\x7f",
                     "2.4.6-rc\t1", "2.4.6+build\n", "2.4.6-\ud800"):
            with self.subTest(version=repr(text)):
                self.assert_invalid(text)

    def test_input_types_are_checked_without_coercion(self):
        self.assertEqual(parse_semver(PlainVersionString("2.4.6")), parse_semver("2.4.6"))
        for value in (None, False, True, 246, 2.46, b"2.4.6", bytearray(b"2.4.6"),
                      ["2.4.6"], {"version": "2.4.6"}, RefuseCoercion()):
            with self.subTest(input_type=type(value).__name__):
                self.assert_invalid(value)

    def test_length_budget_is_positive_integer_keyword_only(self):
        self.assertEqual(parse_semver("2.4.6", max_length=PlainLength(5)), parse_semver("2.4.6"))
        for budget in (0, -10, False, True, 5.0, "5", None, [], RefuseCoercion()):
            with self.subTest(budget_type=type(budget).__name__):
                self.assert_invalid("2.4.6", max_length=budget)
                self.assert_invalid(None, max_length=budget)
        with self.assertRaises(TypeError):
            parse_semver("2.4.6", 5)

    def test_explicit_length_limit_is_inclusive(self):
        version = "2.4.6-preview.8+linux-arm"
        accepted = parse_semver(version, max_length=len(version))
        self.assertEqual(accepted["build"], ["linux-arm"])
        self.assert_invalid(version, max_length=len(version) - 1)
        self.assertEqual(parse_semver(version, max_length=len(version) + 1), accepted)

    def test_default_4096_limit_can_be_raised_explicitly(self):
        prefix = "2.4.6+"
        payload = "x" * (4096 - len(prefix))
        at_limit = prefix + payload
        self.assertEqual(len(at_limit), 4096)
        self.assertEqual(parse_semver(at_limit)["build"], [payload])
        self.assert_invalid(at_limit + "x")
        self.assertEqual(parse_semver(at_limit + "x", max_length=4097)["build"], [payload + "x"])

    def test_huge_numeric_strings_do_not_require_integer_conversion(self):
        major = "1" + "0" * 7999
        prerelease = "2" * 4500
        text = major + ".4.6-" + prerelease + "+000001"
        result = parse_semver(text, max_length=len(text))
        self.assertEqual(result["major"], major)
        self.assertEqual(result["prerelease"], [prerelease])
        self.assertEqual(result["build"], ["000001"])

    def test_many_identifiers_remain_in_original_order(self):
        prerelease = ["stage-" + str(number) for number in range(240)]
        build = ["build-" + str(number) for number in range(240, 280)]
        version = "2.4.6-" + ".".join(prerelease) + "+" + ".".join(build)
        result = parse_semver(version, max_length=len(version))
        self.assertEqual(result["prerelease"], prerelease)
        self.assertEqual(result["build"], build)

    def test_mutating_one_result_cannot_change_any_other_result(self):
        plain = parse_semver("2.4.6")
        self.assertIsNot(plain["prerelease"], plain["build"])
        plain["prerelease"].append("changed")
        plain["build"].append("changed")
        self.assertEqual(parse_semver("2.4.6")["prerelease"], [])
        self.assertEqual(parse_semver("2.4.6")["build"], [])
        left = parse_semver("2.4.6-rc.4+linux-arm")
        right = parse_semver("2.4.6-rc.4+linux-arm")
        self.assertIsNot(left, right)
        self.assertIsNot(left["prerelease"], right["prerelease"])
        self.assertIsNot(left["build"], right["build"])
        left["major"] = "changed"
        left["prerelease"][0] = "changed"
        left["build"].clear()
        self.assertEqual(right["major"], "2")
        self.assertEqual(right["prerelease"], ["rc", "4"])
        self.assertEqual(right["build"], ["linux-arm"])

    def test_invalid_inputs_and_budgets_have_redacted_errors(self):
        synthetic_marker = "SYNTHETIC_MARKER_DO_NOT_ECHO"
        self.assert_invalid("2.4.6+" + synthetic_marker)
        self.assert_invalid(synthetic_marker)
        self.assert_invalid("2.4.6", max_length=synthetic_marker)
        self.assert_invalid("2.4.6+ok", max_length=1)


if __name__ == "__main__":
    unittest.main()
