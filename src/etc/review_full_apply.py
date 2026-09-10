#!/usr/bin/env python3
"""Compatibility entry point; both lists are handled by the shared writer."""
import sys
from selection_writer import main
try:
    main('full')
except (ValueError, KeyError, OSError, IndexError) as e:
    print('ABORT: ' + str(e), file=sys.stderr)
    sys.exit(1)
