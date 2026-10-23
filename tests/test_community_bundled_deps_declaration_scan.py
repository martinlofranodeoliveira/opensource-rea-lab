import unittest

try:
    from src.npm_tarball_audit.features.bundled_deps_declaration_scan import run_feature
except ImportError:
    from npm_tarball_audit.features.bundled_deps_declaration_scan import run_feature

_ERROR = 'Invalid bundled dependencies scan payload or budget'

class TestBundledDepsDeclarationScan(unittest.TestCase):
    def test_absent_none(self):
        payload = {'bundled': None}
        first = run_feature(payload)
        second = run_feature(payload)
        self.assertEqual(first, {'declared': False, 'entries': None})
        self.assertEqual(payload, {'bundled': None})
        self.assertIsNot(first, second)
        self.assertFalse(first['declared'])
        self.assertIsNone(first['entries'])
        self.assertEqual(set(first.keys()), {'declared', 'entries'})

    def test_empty_list(self):
        payload = {'bundled': []}
        result = run_feature(payload)
        self.assertEqual(result, {'declared': True, 'entries': []})
        self.assertTrue(result['declared'])
        self.assertEqual(result['entries'], [])
        self.assertIsNot(result['entries'], payload['bundled'])
        result['entries'].append('x')
        self.assertEqual(payload, {'bundled': []})
        again = run_feature(payload)
        self.assertEqual(again, {'declared': True, 'entries': []})

    def test_sorted_verbatim(self):
        payload = {'bundled': ['react', '@scope/pkg']}
        result = run_feature(payload)
        self.assertEqual(result, {'declared': True, 'entries': ['@scope/pkg', 'react']})
        self.assertEqual(payload, {'bundled': ['react', '@scope/pkg']})
        payload2 = {'bundled': ['apple', 'Zebra', '@scope/pkg', 'react']}
        result2 = run_feature(payload2)
        self.assertEqual(result2['entries'], ['@scope/pkg', 'Zebra', 'apple', 'react'])
        self.assertIsNot(result2['entries'], payload2['bundled'])
        self.assertEqual(payload2, {'bundled': ['apple', 'Zebra', '@scope/pkg', 'react']})

    def test_case_preserved(self):
        payload = {'bundled': ['React', 'react', 'REACT']}
        result = run_feature(payload)
        self.assertEqual(result['entries'], ['REACT', 'React', 'react'])
        again = run_feature(payload)
        self.assertEqual(again, result)
        self.assertIsNot(again, result)
        self.assertIsNot(again['entries'], result['entries'])

    def test_allowed_tab_lf_cr(self):
        for code in [9, 10, 13]:
            good = 'a' + chr(code) + 'b'
            result = run_feature({'bundled': [good]})
            self.assertEqual(result['entries'], [good])

    def test_reject_non_dict_missing_extra(self):
        for bad in [None, [], 'x', 0, 1, True, False, 123, 3.5, ('a',)]:
            with self.assertRaises(ValueError) as ctx:
                run_feature(bad)
            self.assertEqual(str(ctx.exception), _ERROR)
        with self.assertRaises(ValueError) as ctx:
            run_feature({})
        self.assertEqual(str(ctx.exception), _ERROR)
        with self.assertRaises(ValueError) as ctx:
            run_feature({'max_entries': 64})
        self.assertEqual(str(ctx.exception), _ERROR)
        with self.assertRaises(ValueError) as ctx:
            run_feature({'bundled': None, 'extra': 1})
        self.assertEqual(str(ctx.exception), _ERROR)
        with self.assertRaises(ValueError) as ctx:
            run_feature({'bundled': [], 'foo': 'bar'})
        self.assertEqual(str(ctx.exception), _ERROR)

    def test_reject_wrong_budgets(self):
        for bad in [True, False, 0, -1, 129, 200, 1.5, '64', None, [], {}]:
            with self.assertRaises(ValueError) as ctx:
                run_feature({'bundled': [], 'max_entries': bad})
            self.assertEqual(str(ctx.exception), _ERROR)
        for bad in [True, False, 0, -5, 215, 1000, 2.5, '214', None, [], {}]:
            with self.assertRaises(ValueError) as ctx:
                run_feature({'bundled': [], 'max_length': bad})
            self.assertEqual(str(ctx.exception), _ERROR)
        self.assertEqual(run_feature({'bundled': [], 'max_entries': 1}), {'declared': True, 'entries': []})
        self.assertEqual(run_feature({'bundled': [], 'max_entries': 128}), {'declared': True, 'entries': []})
        self.assertEqual(run_feature({'bundled': [], 'max_length': 1}), {'declared': True, 'entries': []})
        self.assertEqual(run_feature({'bundled': [], 'max_length': 214}), {'declared': True, 'entries': []})

    def test_reject_non_list_bundled(self):
        for bad in ['react', '', 0, 1, True, False, 3.5, {}, {'a': 1}]:
            with self.assertRaises(ValueError) as ctx:
                run_feature({'bundled': bad})
            self.assertEqual(str(ctx.exception), _ERROR)

    def test_reject_bad_entries(self):
        with self.assertRaises(ValueError) as ctx:
            run_feature({'bundled': ['']})
        self.assertEqual(str(ctx.exception), _ERROR)
        for bad in [123, None, True, False, 0, 1.5, {}, []]:
            with self.assertRaises(ValueError) as ctx:
                run_feature({'bundled': [bad]})
            self.assertEqual(str(ctx.exception), _ERROR)
        with self.assertRaises(ValueError) as ctx:
            run_feature({'bundled': ['react', 'react']})
        self.assertEqual(str(ctx.exception), _ERROR)
        with self.assertRaises(ValueError) as ctx:
            run_feature({'bundled': ['a', 'A', 'a']})
        self.assertEqual(str(ctx.exception), _ERROR)
        with self.assertRaises(ValueError) as ctx:
            run_feature({'bundled': ['a', 'b', 'c'], 'max_entries': 2})
        self.assertEqual(str(ctx.exception), _ERROR)
        with self.assertRaises(ValueError) as ctx:
            run_feature({'bundled': ['abcd'], 'max_length': 3})
        self.assertEqual(str(ctx.exception), _ERROR)

    def test_reject_c0_and_surrogates(self):
        for code in [0, 1, 2, 8, 11, 12, 14, 31]:
            bad = 'a' + chr(code) + 'b'
            with self.assertRaises(ValueError) as ctx:
                run_feature({'bundled': [bad]})
            self.assertEqual(str(ctx.exception), _ERROR)
        for bad in [chr(55296), chr(56319), chr(56320), chr(57343), chr(55296) + 'x', 'x' + chr(55296)]:
            with self.assertRaises(ValueError) as ctx:
                run_feature({'bundled': [bad]})
            self.assertEqual(str(ctx.exception), _ERROR)
        paired = chr(55296) + chr(56320)
        result = run_feature({'bundled': [paired]})
        self.assertEqual(result['entries'], [paired])

    def test_no_mutation_and_fresh(self):
        payload = {'bundled': ['b', 'a']}
        first = run_feature(payload)
        self.assertEqual(payload, {'bundled': ['b', 'a']})
        self.assertEqual(first['entries'], ['a', 'b'])
        first['entries'].append('zzz')
        second = run_feature(payload)
        self.assertEqual(second['entries'], ['a', 'b'])
        self.assertEqual(payload, {'bundled': ['b', 'a']})
        self.assertIsNot(first['entries'], second['entries'])
        self.assertIsNot(first, second)

    def test_error_message_exact_no_echo(self):
        try:
            run_feature({'bundled': ['good', 'good']})
            self.fail('expected ValueError')
        except ValueError as exc:
            self.assertEqual(str(exc), _ERROR)

    def test_deterministic(self):
        payload = {'bundled': ['c', 'b', 'a']}
        first = run_feature(payload)
        second = run_feature(payload)
        self.assertEqual(first, second)
        self.assertEqual(first, {'declared': True, 'entries': ['a', 'b', 'c']})

if __name__ == '__main__':
    unittest.main()
