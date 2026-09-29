#!/bin/bash
# Kept as an entry point. The old reader passed a GitHub URL to list-patches and got no
# names for any provider (Nightly #99, 28 Sep 2026); this now runs the exact-bundle
# checker, which prints names and headroom together.
set -uo pipefail
exec python3 src/etc/selection_names.py "$@"
