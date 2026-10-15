#!/usr/bin/env python3
"""Compare two validated, bounded Ethereum JSON-RPC snapshots offline."""

import argparse
import json
from pathlib import Path
import runpy
import sys

B = runpy.run_path(str(Path(__file__).resolve().parents[1] /
                       'bounded-rpc-snapshot' / 'snapshot.py'))
MAX_CHANGES = 64
MAX_DEPTH = 64
MAX_OUTPUT = 100_000


class DiffError(ValueError):
    pass


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'),
                      ensure_ascii=True, allow_nan=False).encode('ascii')


def pointer(path):
    return '' if not path else '/' + '/'.join(
        str(part).replace('~', '~0').replace('/', '~1') for part in path)


def preview(value):
    rendered = canonical(value).decode('ascii')
    return rendered if len(rendered) <= 160 else rendered[:157] + '...'


def compare(before, after):
    """Return bounded differences; never claim agreement about Ethereum state."""
    if canonical(before['request']) != canonical(after['request']):
        raise DiffError('snapshots contain different JSON-RPC requests')
    left, right = before['response']['result'], after['response']['result']
    changes = []
    omitted = False

    def add(change):
        nonlocal omitted
        if len(changes) < MAX_CHANGES:
            changes.append(change)
        else:
            omitted = True

    def visit(a, b, path, depth):
        nonlocal omitted
        if omitted:
            return
        if depth > MAX_DEPTH:
            raise DiffError('result nesting exceeds 64 levels')
        if type(a) is dict and type(b) is dict:
            for key in sorted(a.keys() | b.keys()):
                if key not in a or key not in b:
                    add({'path': pointer(path + [key]),
                         'kind': 'removed' if key not in b else 'added',
                         'before': preview(a[key]) if key in a else None,
                         'after': preview(b[key]) if key in b else None})
                else:
                    visit(a[key], b[key], path + [key], depth + 1)
                if omitted:
                    return
        elif type(a) is list and type(b) is list:
            for index in range(max(len(a), len(b))):
                if index >= len(a) or index >= len(b):
                    add({'path': pointer(path + [index]),
                         'kind': 'removed' if index >= len(b) else 'added',
                         'before': preview(a[index]) if index < len(a) else None,
                         'after': preview(b[index]) if index < len(b) else None})
                else:
                    visit(a[index], b[index], path + [index], depth + 1)
                if omitted:
                    return
        elif canonical(a) != canonical(b):
            add({'path': pointer(path), 'kind': 'changed',
                 'before': preview(a), 'after': preview(b)})

    same = canonical(left) == canonical(right)
    if not same:
        visit(left, right, [], 0)
    result = {
        'schema': 'line1-generic-snapshot-diff-v1',
        'request': before['request'],
        'same_result': same,
        'changes': changes,
        'changes_truncated': omitted,
        'before': {'rpc_url': before['rpc_url'],
                   'captured_at_utc': before['captured_at_utc'],
                   'response_sha256': before['response_sha256']},
        'after': {'rpc_url': after['rpc_url'],
                  'captured_at_utc': after['captured_at_utc'],
                  'response_sha256': after['response_sha256']},
        'meaning': 'Comparison of saved provider responses; not a state proof, '
                   'a freshness check, or evidence that providers are independent.'
    }
    if len(canonical(result)) > MAX_OUTPUT:
        raise DiffError('comparison output exceeds 100000 bytes')
    return result


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('before', help='first saved bounded snapshot')
    parser.add_argument('after', help='second saved bounded snapshot')
    args = parser.parse_args(argv)
    try:
        before = B['verify_snapshot'](args.before)
        after = B['verify_snapshot'](args.after)
        report = compare(before, after)
        print(json.dumps(report, indent=2, sort_keys=True, ensure_ascii=True,
                         allow_nan=False))
        return 0
    except (DiffError, B['SnapshotError'], ValueError, OSError,
            RecursionError, TypeError) as exc:
        print('generic-snapshot-diff: ' + str(exc), file=sys.stderr)
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
