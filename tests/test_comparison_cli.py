"""CLI behavior fixed independently before implementation/publication."""
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

from npm_tarball_audit import __main__ as cli

REPO = Path(__file__).resolve().parents[1]


def report(entries=None, **kwargs):
    return dict(schema='npm-tarball-audit/v1', status='pass',
                package_executed=False, files_extracted=False,
                inventory=entries or [], **kwargs)


def entry(path, digest='0', size=1):
    return dict(path='package/' + path, bytes=size, sha256=digest * 64)


class ComparisonCLI(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.before = self.root / 'before.json'
        self.after = self.root / 'after.json'
        self.before.write_text(json.dumps(report([entry('old.js'), entry('same.js'), entry('change.js')])) )
        self.after.write_text(json.dumps(report([entry('new.js'), entry('same.js'), entry('change.js', '1')])))

    def run_cli(self, *args):
        env = {'PATH': '/usr/bin:/bin', 'LANG': 'C.UTF-8', 'PYTHONPATH': str(REPO / 'src'),
               'PYTHONDONTWRITEBYTECODE': '1', 'PYTHONNOUSERSITE': '1'}
        return subprocess.run([sys.executable, '-m', 'npm_tarball_audit', *map(str, args)],
                              cwd=REPO, env=env, capture_output=True, text=True, timeout=5)

    def test_diff_exit_and_machine_shape(self):
        result = self.run_cli('--compare', self.before, self.after, '--json')
        self.assertEqual(result.returncode, 1, result.stderr)
        self.assertEqual(result.stderr, '')
        data = json.loads(result.stdout)
        self.assertEqual(set(data), {'added', 'removed', 'changed', 'unchanged_count'})
        self.assertEqual(data['added'], [entry('new.js')])
        self.assertEqual(data['removed'], [entry('old.js')])
        self.assertEqual(data['changed'][0]['path'], 'package/change.js')
        self.assertEqual(data['unchanged_count'], 1)

    def test_equal_inventory_exit_and_warning_status(self):
        self.after.write_text(json.dumps({**json.loads(self.before.read_text()), 'status': 'warning'}))
        result = self.run_cli('--compare', self.before, self.after, '--json')
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(json.loads(result.stdout), dict(added=[], removed=[], changed=[], unchanged_count=3))

    def test_failed_audits_missing_inventory_and_invalid_text_do_not_emit_partial_output(self):
        invalid = ['{', '{"secret-synthetic":NaN}',
                   json.dumps({**report(), 'status': 'fail'}),
                   json.dumps({key: value for key, value in report().items() if key != 'inventory'}),
                   json.dumps({**report([entry('a')]), 'inventory': [entry('a'), entry('a')]}),
                   json.dumps(report())[:-1] + ',"secret-synthetic":1,"secret-synthetic":2}',
                   json.dumps(report())[:-1] + ',"unknown":' + '[' * 1000 + '0' + ']' * 1000 + '}']
        for text in invalid:
            self.after.write_text(text)
            with self.subTest(text=text[:40]):
                result = self.run_cli('--compare', self.before, self.after, '--json')
                self.assertEqual(result.returncode, 2)
                self.assertEqual(result.stdout, '')
                self.assertNotIn('secret-synthetic', result.stderr)
                self.assertNotIn(str(self.root), result.stderr)
                self.assertNotIn('Traceback', result.stderr)
        self.after.write_bytes(b'\xff')
        self.assertEqual(self.run_cli('--compare', self.before, self.after).returncode, 2)

    def test_files_are_bounded_and_special_files_never_block(self):
        # Exercise exact/excess boundaries without a large on-disk test fixture.
        with patch.object(cli, 'MAX_REPORT_BYTES', 64):
            self.after.write_bytes(b' ' * 64)
            self.assertEqual(cli._read_report(str(self.after)), ' ' * 64)
            self.after.write_bytes(b' ' * 65)
            with self.assertRaises(ValueError):
                cli._read_report(str(self.after))
        fifo = self.root / 'fifo'
        os.mkfifo(fifo)
        link = self.root / 'report-link'
        link.symlink_to(self.before)
        for path in [fifo, link, self.root, self.root / 'missing']:
            with self.subTest(path=path.name):
                result = self.run_cli('--compare', self.before, path)
                self.assertEqual(result.returncode, 2)
                self.assertEqual(result.stdout, '')
                self.assertNotIn(str(self.root), result.stderr)

    def test_audit_options_and_archive_cannot_be_mixed_with_comparison(self):
        for extra in [['archive.tgz'], ['--expected-name', 'name'], ['--include-inventory'],
                      ['--expected-version', '1.0.0'], ['--integrity', 'synthetic']]:
            with self.subTest(extra=extra):
                result = self.run_cli('--compare', self.before, self.after, *extra)
                self.assertEqual(result.returncode, 2)
                self.assertEqual(result.stdout, '')

    def test_human_output_escapes_unicode_control_like_characters(self):
        self.before.write_text(json.dumps(report()))
        self.after.write_text(json.dumps(report([entry('visible\u202e.js')])))
        result = self.run_cli('--compare', self.before, self.after)
        self.assertEqual(result.returncode, 1)
        self.assertNotIn('\u202e', result.stdout)
        self.assertIn('\\u202e', result.stdout)


if __name__ == '__main__':
    unittest.main()
