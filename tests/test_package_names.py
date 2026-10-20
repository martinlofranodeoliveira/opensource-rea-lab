import unittest

from npm_tarball_audit.names import parse_package_name


class TestParsePackageName(unittest.TestCase):
    def test_unscoped_simple(self):
        self.assertEqual(
            parse_package_name("example"), {"scope": None, "name": "example"}
        )

    def test_unscoped_allowed_chars(self):
        for valid in [
            "a",
            "0",
            "a1",
            "my-package",
            "my_package",
            "my.package",
            "abc123",
            "a-b_c.d",
            "0a",
            "a0",
        ]:
            with self.subTest(valid=valid):
                self.assertEqual(
                    parse_package_name(valid), {"scope": None, "name": valid}
                )

    def test_scoped_simple(self):
        self.assertEqual(
            parse_package_name("@my-scope/my-name"),
            {"scope": "my-scope", "name": "my-name"},
        )

    def test_result_is_fresh_plain_dict_with_exact_keys(self):
        result = parse_package_name("@scope/name")
        self.assertIs(type(result), dict)
        self.assertEqual(set(result.keys()), {"scope", "name"})
        self.assertEqual(result["scope"], "scope")
        self.assertEqual(result["name"], "name")
        self.assertFalse(result["scope"].startswith("@"))
        self.assertEqual(result, {"scope": "scope", "name": "name"})
        plain = parse_package_name("example")
        self.assertIs(type(plain), dict)
        self.assertEqual(set(plain.keys()), {"scope", "name"})
        self.assertIsNone(plain["scope"])
        self.assertEqual(plain["name"], "example")

    def test_fresh_dict_container_without_string_identity_checks(self):
        first = parse_package_name("example")
        second = parse_package_name("example")
        self.assertIsNot(first, second)
        self.assertEqual(first, second)
        first["name"] = "changed"
        self.assertEqual(second, {"scope": None, "name": "example"})
        first_scoped = parse_package_name("@scope/name")
        second_scoped = parse_package_name("@scope/name")
        self.assertIsNot(first_scoped, second_scoped)
        self.assertEqual(first_scoped, second_scoped)
        first_scoped["scope"] = "changed"
        self.assertEqual(second_scoped, {"scope": "scope", "name": "name"})

    def test_str_subclass_accepted_without_coercion(self):
        class S(str):
            pass

        self.assertEqual(
            parse_package_name(S("example")),
            {"scope": None, "name": "example"},
        )
        self.assertEqual(
            parse_package_name(S("@my-scope/my-name")),
            {"scope": "my-scope", "name": "my-name"},
        )

    def test_length_boundaries_include_at_and_slash(self):
        self.assertEqual(
            parse_package_name("a" * 214),
            {"scope": None, "name": "a" * 214},
        )
        self.assertEqual(parse_package_name("a"), {"scope": None, "name": "a"})
        with self.assertRaises(ValueError):
            parse_package_name("a" * 215)
        with self.assertRaises(ValueError):
            parse_package_name("")
        scoped_214 = "@" + "a" * 100 + "/" + "b" * 112
        self.assertEqual(len(scoped_214), 214)
        self.assertEqual(
            parse_package_name(scoped_214),
            {"scope": "a" * 100, "name": "b" * 112},
        )
        scoped_215 = scoped_214 + "c"
        self.assertEqual(len(scoped_215), 215)
        with self.assertRaises(ValueError):
            parse_package_name(scoped_215)
        over_scoped = "@" + "a" * 212 + "/b"
        self.assertEqual(len(over_scoped), 215)
        with self.assertRaises(ValueError):
            parse_package_name(over_scoped)

    def test_each_component_must_start_alphanumeric(self):
        for bad in [
            "-foo",
            "_foo",
            ".foo",
            "@-s/n",
            "@_s/n",
            "@.s/n",
            "@s/-n",
            "@s/_n",
            "@s/.n",
        ]:
            with self.subTest(bad=bad):
                with self.assertRaises(ValueError):
                    parse_package_name(bad)

    def test_rejects_uppercase_spaces_unicode_escapes(self):
        for bad in [
            "Example",
            "EXAMPLE",
            "@Scope/name",
            "@scope/Name",
            "has space",
            " trailing",
            "trailing ",
            "a/b",
            "a\\b",
            "caf\u00e9",
            "a\u00e9",
            "a\tb",
            "a\nb",
            "a:b",
            "a?b",
            "a*b",
            "a!b",
        ]:
            with self.subTest(bad=bad):
                with self.assertRaises(ValueError):
                    parse_package_name(bad)

    def test_rejects_malformed_scoped_shapes(self):
        for bad in [
            "@",
            "@/",
            "@scope",
            "@scope/",
            "@/name",
            "@scope/name/extra",
            "@s/n/",
            "/name",
            "@s//n",
            "@@s/n",
            "@s@n/n",
            "@s/n@",
            "name@",
            "@s",
            "@scope//",
        ]:
            with self.subTest(bad=bad):
                with self.assertRaises(ValueError):
                    parse_package_name(bad)

    def test_rejects_wrong_types_without_coercion(self):
        for bad in [
            None,
            123,
            1.5,
            True,
            False,
            b"example",
            ["example"],
            {"name": "x"},
            ("x",),
            bytearray(b"x"),
        ]:
            with self.subTest(bad=bad):
                with self.assertRaises(ValueError):
                    parse_package_name(bad)

    def test_error_message_exact_without_echo(self):
        secret = "@bad-Scope/Name With Space"
        try:
            parse_package_name(secret)
        except ValueError as exc:
            self.assertEqual(str(exc), "Invalid package name")
            self.assertNotIn(secret, str(exc))
            self.assertNotIn("bad", str(exc))
        else:
            self.fail("expected ValueError")
        try:
            parse_package_name(None)
        except ValueError as exc:
            self.assertEqual(str(exc), "Invalid package name")
        else:
            self.fail("expected ValueError")
        try:
            parse_package_name("")
        except ValueError as exc:
            self.assertEqual(str(exc), "Invalid package name")
        else:
            self.fail("expected ValueError")


if __name__ == "__main__":
    unittest.main()
