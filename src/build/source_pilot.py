#!/usr/bin/env python3
"""Read-only Reddit original-consumer pilot; never installs an admission.

Run in an isolated candidate with verified aapt2/apksigner on PATH.
Original APKs are copied into new scratch only. No network, merge, patch,
signing, publishing, receipt installation or repository-policy modification.
"""
import json
from pathlib import Path
import sys

import input_recipe
import source_fallback as fallback
import source_variant

EVIDENCE = 'docs/review/source-qualifications/reddit-2026.38.0-originals.json'


def inspect(root, raw, scratch, env):
    row = input_recipe.read_json(root, EVIDENCE)
    fallback.need(row['status'] == 'ORIGINALS_REVIEWED_NOT_ACTIVATED' and
                  row['qualification']['activation'] is False, 'pilot evidence state differs')
    t = fallback.target(root, row['target'])
    fallback.need(t['id'] == 'reddit' and t['package'] == row['package'], 'pilot target differs')
    policy_before = (root / fallback.POLICY).read_bytes()
    doc = fallback.policy(root)
    fallback.need(all(not x['admissions'] for x in doc['targets'].values()),
                  'pilot requires dormant all-target policy')
    a = {k: row[k] for k in ('source', 'version_name', 'version_code', 'container',
                            'certificate_sha256', 'mapping', 'variant')}
    fallback.mapping_ok(a['source'], a['mapping'], t['package'])
    source_variant.validate(a['variant'], a['source'], a['mapping'],
                            a['version_name'], t['min_sdk_ceiling'])
    fallback.need(not scratch.exists() and not scratch.is_symlink(), 'pilot scratch already exists')
    # Check the exact original before creating scratch or invoking Android tools.
    fallback.need(fallback.file_record(raw) == a['container'], 'pilot raw bytes differ')
    scratch.mkdir()
    proof = fallback.inspect_original(root, raw, t, a, fallback.source_inputs.clean_env(env), scratch)
    expected = [{k: p[k] for k in ('bytes', 'sha256')} for p in row['original_parts']]
    fallback.need(proof['splits'] == expected, 'pilot split bytes differ from reviewed evidence')
    fallback.need((root / fallback.POLICY).read_bytes() == policy_before, 'pilot changed policy')
    fallback.need(not (root / fallback.RECEIPT).exists(), 'pilot must not install receipt')
    result = {'schema': 1, 'status': 'CANDIDATE_ORIGINAL_CONSUMER_PASSED',
              'target': t['id'], 'version': a['version_name'], 'original': proof,
              'activation': False, 'patch': False, 'merge_splits': False,
              'sign': False, 'publish': False, 'device_test': False,
              'limits': ['Original-consumer pilot only; actual patch/output pilot remains pending']}
    (scratch / 'PILOT-RESULT.json').write_text(json.dumps(result, indent=2, sort_keys=True) + '\n')
    return result


if __name__ == '__main__':
    try:
        import os
        fallback.need(len(sys.argv) == 3, 'usage: source_pilot.py ORIGINAL_CONTAINER NEW_SCRATCH')
        result = inspect(Path.cwd().resolve(), Path(sys.argv[1]).resolve(),
                         Path(sys.argv[2]), dict(os.environ))
        print(json.dumps(result, sort_keys=True))
    except (ValueError, KeyError, TypeError, OSError, RuntimeError):
        print('SOURCE_ORIGINAL_PILOT_REFUSED', file=sys.stderr)
        sys.exit(1)
