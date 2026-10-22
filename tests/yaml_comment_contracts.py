"""W15e (22 Oct 2026, L069): an unquoted YAML value that contains ' #' loses everything after it.
'run-name: Onboarding review #${{ inputs.pr }}' became 'Onboarding review', so 11. Rule merge
never found the review of #207. Any workflow or action line whose comment part holds a
${{ }} expression is that bug: the expression was meant to be part of the value."""
import pathlib
import re
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
FILES = sorted(list((ROOT / '.github/workflows').glob('*.yml')) + list((ROOT / '.github/actions').glob('*/action.yml')))


def eaten(line):
    """The ${{ }} text YAML would treat as a comment on this line, or ''."""
    m = re.match(r'^\s*(?:- )?[A-Za-z0-9_-]+:\s+(.*)$', line)
    if not m:
        return ''
    value = m.group(1)
    if value[:1] in ('"', "'", '|', '>'):
        return ''
    cut = value.find(' #')
    if cut < 0:
        return ''
    rest = value[cut:]
    return rest if '${{' in rest else ''


class YamlComment(unittest.TestCase):
    def test_no_expression_after_an_unquoted_hash(self):
        bad = []
        for f in FILES:
            for n, line in enumerate(f.read_text(encoding='utf-8').splitlines(), 1):
                if eaten(line):
                    bad.append('%s:%d' % (f.relative_to(ROOT), n))
        self.assertEqual(bad, [])

    def test_the_detector_sees_the_207_bug(self):
        self.assertTrue(eaten('run-name: Onboarding review #${{ inputs.pr }}'))
        self.assertFalse(eaten('run-name: "Onboarding review #${{ inputs.pr }}"'))
        self.assertFalse(eaten('    - cron: "7 4 * * *"  # 09:37 IST daily'))
        self.assertFalse(eaten('        run: echo hi  # plain comment'))

    def test_onboarding_run_name_keeps_the_number(self):
        text = (ROOT / '.github/workflows/onboard-review.yml').read_text(encoding='utf-8')
        self.assertIn('run-name: "Onboarding review #${{ inputs.pr || github.event.pull_request.number }}"', text)


if __name__ == '__main__':
    unittest.main()
