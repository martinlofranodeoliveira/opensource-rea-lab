import copy
import unittest


def _load_run_feature():
    try:
        from src.npm_tarball_audit.features.funding_declaration_scan import run_feature as f
        return f
    except ImportError:
        pass
    from npm_tarball_audit.features.funding_declaration_scan import run_feature as f
    return f


run_feature = _load_run_feature()
ERROR = "Invalid funding scan payload or budget"


class CommunityFundingDeclarationScanTest(unittest.TestCase):
    def test_absent_none(self):
        payload = {"funding": None}
        before = copy.deepcopy(payload)
        out = run_feature(payload)
        self.assertEqual(out, {"entries": [], "count": 0})
        self.assertEqual(set(out.keys()), {"entries", "count"})
        self.assertEqual(payload, before)

    def test_absent_empty_list(self):
        payload = {"funding": []}
        snapshot = copy.deepcopy(payload)
        out = run_feature(payload)
        self.assertEqual(out["entries"], [])
        self.assertEqual(out["count"], 0)
        self.assertEqual(set(out.keys()), {"entries", "count"})
        self.assertEqual(payload, snapshot)

    def test_contract_examples(self):
        self.assertEqual(run_feature({"funding": None}), {"entries": [], "count": 0})
        self.assertEqual(run_feature({"funding": "https://example.com/sponsor"}), {"entries": [{"type": None, "url": "https://example.com/sponsor"}], "count": 1})
        out = run_feature({"funding": [{"type": "github", "url": "https://example.com/fund"}, {"url": "https://example.com/other"}]})
        self.assertEqual(out["count"], 2)
        self.assertEqual(out["entries"][0], {"type": "github", "url": "https://example.com/fund"})
        self.assertEqual(out["entries"][1], {"type": None, "url": "https://example.com/other"})

    def test_shorthand_verbatim(self):
        url = "  HTTPS://Example.COM/Sponsor?q=1  "
        out = run_feature({"funding": url})
        self.assertEqual(out["count"], 1)
        entry = out["entries"][0]
        self.assertEqual(set(entry.keys()), {"type", "url"})
        self.assertIsNone(entry["type"])
        self.assertEqual(entry["url"], url)

    def test_shorthand_subclass(self):
        class S(str):
            pass
        val = S("https://example.com/sponsor")
        out = run_feature({"funding": val})
        self.assertEqual(out["count"], 1)
        self.assertIsNone(out["entries"][0]["type"])
        self.assertEqual(out["entries"][0]["url"], "https://example.com/sponsor")
        self.assertIs(type(out["entries"][0]["url"]), str)

    def test_single_dict(self):
        out = run_feature({"funding": {"type": "github", "url": "https://example.com/fund"}})
        self.assertEqual(out, {"entries": [{"type": "github", "url": "https://example.com/fund"}], "count": 1})
        out1 = run_feature({"funding": {"type": "github"}})
        self.assertEqual(out1["entries"][0], {"type": "github", "url": None})
        out2 = run_feature({"funding": {"url": "https://example.com/other"}})
        self.assertEqual(out2["entries"][0], {"type": None, "url": "https://example.com/other"})

    def test_list_ordered_mixed(self):
        payload = {"funding": ["https://example.com/a", {"type": "T", "url": "https://example.com/b"}, {"url": "https://example.com/c"}]}
        snapshot = copy.deepcopy(payload)
        out = run_feature(payload)
        self.assertEqual(out["count"], 3)
        self.assertEqual(out["entries"][0], {"type": None, "url": "https://example.com/a"})
        self.assertEqual(out["entries"][1], {"type": "T", "url": "https://example.com/b"})
        self.assertEqual(out["entries"][2], {"type": None, "url": "https://example.com/c"})
        self.assertEqual(payload, snapshot)

    def test_custom_budgets(self):
        out = run_feature({"funding": ["ab", "cd"], "max_entries": 2, "max_length": 2})
        self.assertEqual(out["count"], 2)
        with self.assertRaises(ValueError) as ctx:
            run_feature({"funding": ["ab", "cd"], "max_entries": 1})
        self.assertEqual(str(ctx.exception), ERROR)
        with self.assertRaises(ValueError) as ctx2:
            run_feature({"funding": "abcd", "max_length": 3})
        self.assertEqual(str(ctx2.exception), ERROR)

    def test_invalid_fixed_message_no_echo(self):
        sentinel = "SENTINEL_XYZ_987"
        bad = [{}, {"funding": None, "extra": 1}, {"max_entries": 16}, None, [], "x", {"funding": 123}, {"funding": True}, {"funding": ""}, {"funding": "x" * 513}, {"funding": {}}, {"funding": {"other": sentinel}}, {"funding": {"type": "a", "url": "b", "extra": "c"}}, {"funding": {"type": 123}}, {"funding": {"url": ""}}, {"funding": {"url": "x" * 513}}, {"funding": [sentinel * 100]}, {"funding": ["ok", 123]}, {"funding": ["ok", None]}, {"funding": ["https://example.com/" + sentinel] * 17}, {"funding": None, "max_entries": True}, {"funding": None, "max_entries": 0}, {"funding": None, "max_entries": -1}, {"funding": None, "max_entries": "16"}, {"funding": None, "max_length": False}, {"funding": None, "max_length": 0}, {"funding": None, "max_length": 1.5}, {"funding": ("a",)}]
        for p in bad:
            with self.subTest(payload=p):
                with self.assertRaises(ValueError) as ctx:
                    run_feature(p)
                msg = str(ctx.exception)
                self.assertEqual(msg, ERROR)
                self.assertNotIn(sentinel, msg)

    def test_fresh_containers_no_shared_refs(self):
        payload = {"funding": [{"type": "github", "url": "https://example.com/fund"}]}
        out1 = run_feature(payload)
        out2 = run_feature(payload)
        self.assertEqual(out1, out2)
        self.assertIsNot(out1, out2)
        self.assertIsNot(out1["entries"], out2["entries"])
        self.assertIsNot(out1["entries"][0], out2["entries"][0])
        self.assertIsNot(out1["entries"], payload["funding"])
        self.assertIsNot(out1["entries"][0], payload["funding"][0])
        out1["entries"][0]["url"] = "mutated"
        self.assertNotEqual(out1, out2)
        out3 = run_feature({"funding": "https://example.com/sponsor"})
        out4 = run_feature({"funding": "https://example.com/sponsor"})
        self.assertIsNot(out3["entries"][0], out4["entries"][0])

    def test_input_never_mutated(self):
        payload = {"funding": ["https://example.com/a", {"type": "g", "url": "https://example.com/b"}]}
        snapshot = copy.deepcopy(payload)
        run_feature(payload)
        self.assertEqual(payload, snapshot)
        single = {"funding": {"type": "g", "url": "https://example.com/b"}}
        snap2 = copy.deepcopy(single)
        run_feature(single)
        self.assertEqual(single, snap2)


if __name__ == "__main__":
    unittest.main()
