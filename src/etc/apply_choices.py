#!/usr/bin/env python3
"""Compatibility entry point; undecided and absent names preserve state."""
import sys
from selection_writer import main
try:
    main('chooser')
except (ValueError, KeyError, OSError, IndexError) as e:
    print('ABORT: ' + str(e), file=sys.stderr)
    sys.exit(1)
