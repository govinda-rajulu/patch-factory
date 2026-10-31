#!/usr/bin/env python3
"""W15g: does this patcher jar offer --unsigned? Read-only, never runs patches.

Evidence, either is enough: the `patch --help` text (on stdin) names the option, or the jar's
PatchCommand class carries the option string. Morphe Desktop's `patch` command has no help
option of its own (official source, v1.20.0), so its help text may arrive as a usage error;
the class read does not depend on that. Neither found: exit 1, and the build stops.
"""
import re
import sys
import zipfile

OPTION = re.compile(r'(?:^|[\s,\[])--unsigned(?![\w-])', re.M)


def supports(jar, help_text):
    if OPTION.search(help_text or ''):
        return 'help'
    try:
        with zipfile.ZipFile(jar) as z:
            for name in z.namelist():
                # A class-file constant: tag 1 (UTF-8), length 10, then exactly '--unsigned'.
                if name.endswith('/PatchCommand.class') and b'\x01\x00\x0a--unsigned' in z.read(name):
                    return 'class'
    except (OSError, zipfile.BadZipFile):
        return None
    return None


if __name__ == '__main__':
    via = supports(sys.argv[1], sys.stdin.read(1 << 20)) if len(sys.argv) == 2 else None
    if via is None:
        sys.exit(1)
    print('UNSIGNED_SUPPORTED via ' + via)
