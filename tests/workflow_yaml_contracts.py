"""W16y-b: every workflow file must parse.

A plain YAML value that contains ': ' (for example an unquoted description) makes the whole
workflow invalid, and GitHub then refuses every run of it. The W16y-b provider-scan lane
shipped such a line in manual-patch.yml, which every build calls; it was caught before the
commit. This contract fails on that shape even where PyYAML is missing, and parses every
file fully when PyYAML is available.
"""
import glob
import os
import re
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
WF = sorted(glob.glob(os.path.join(ROOT, '.github', 'workflows', '*.yml')))
KEY = re.compile(r"^(\s*)(?:- )?[A-Za-z_][\w-]*:(?: (.*))?$")
BLOCK = re.compile(r"^[|>][-+]?\s*(#.*)?$")


def plain_colon_lines(text):
    """Return (line number, line) for unquoted plain values that contain ': '."""
    bad, block = [], None
    for no, raw in enumerate(text.splitlines(), 1):
        if block is not None:
            if raw.strip() == '' or len(raw) - len(raw.lstrip()) > block:
                continue
            block = None
        if raw.lstrip().startswith('#'):
            continue
        m = KEY.match(raw)
        if not m or m.group(2) is None:
            continue
        value = m.group(2)
        if BLOCK.match(value):
            block = len(m.group(1))
            continue
        if value[:1] in ('"', "'", '{', '[', '&', '*', '!', '|', '>'):
            continue
        value = re.sub(r"\s+#.*$", '', value)
        if ': ' in value or value.endswith(':'):
            bad.append((no, raw.strip()))
    return bad


class WorkflowYaml(unittest.TestCase):
    def test_files_exist(self):
        self.assertGreater(len(WF), 10)

    def test_no_unquoted_colon_values(self):
        problems = []
        for f in WF:
            with open(f, encoding='utf-8') as fh:
                text = fh.read()
            for no, line in plain_colon_lines(text):
                problems.append('%s:%d %s' % (os.path.basename(f), no, line[:100]))
        self.assertEqual(problems, [])

    def test_lint_catches_the_w16yb_line(self):
        sample = "on:\n  workflow_call:\n    inputs:\n      scan:\n        description: Smoke only: scan it\n"
        self.assertEqual(len(plain_colon_lines(sample)), 1)
        ok = "x:\n  description: 'Smoke only: scan it'\n  run: |\n    echo a: b\n"
        self.assertEqual(plain_colon_lines(ok), [])

    def test_full_parse_when_available(self):
        try:
            import yaml  # noqa: F401
        except ImportError:
            self.skipTest('PyYAML not installed; the plain-value lint above still ran')
        for f in WF:
            with open(f, encoding='utf-8') as fh:
                yaml.safe_load(fh)


if __name__ == '__main__':
    unittest.main()
