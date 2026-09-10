#!/usr/bin/env python3
"""Compatibility entry point; current policy is checked before writing."""
import sys
from selection_writer import main
try:
    main('unreviewed')
except (ValueError, KeyError, OSError, IndexError) as e:
    print('ABORT: ' + str(e), file=sys.stderr)
    sys.exit(1)
