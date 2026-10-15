#!/usr/bin/env python3
"""Inspect and independently compare every reachable EIP-712 byte field offline."""
import argparse
import json
import sys

from typed_digest import (ARRAY, FIXED_BYTES, Encoder, TypedDataError, digest,
                          load_workspace_json, parse_hex, validate_tree)

MAX_REPORT_BYTES = 100_000


def render(report):
    text = json.dumps(report, ensure_ascii=True, indent=2) + '\n'
    if len(text.encode('ascii')) > MAX_REPORT_BYTES:
        raise TypedDataError('byte review exceeds 100000-byte output limit')
    return text


def expectations(policy):
    """Only literal typed-byte expectations; no embedded paths are opened."""
    validate_tree(policy)
    if not isinstance(policy, dict) or set(policy) != {'fields'}:
        raise TypedDataError('expectations require exactly a fields object')
    fields = policy['fields']
    if not isinstance(fields, dict):
        raise TypedDataError('fields must map JSON Pointer paths to type/value objects')
    result = {}
    for path, field in fields.items():
        if not isinstance(path, str) or not path.startswith(('/domain/', '/message/')):
            raise TypedDataError('byte expectation path must start /domain/ or /message/')
        if not isinstance(field, dict) or set(field) != {'type', 'value'}:
            raise TypedDataError('each byte expectation needs exactly type and value')
        kind = field['type']
        fixed = FIXED_BYTES.fullmatch(kind) if isinstance(kind, str) else None
        if kind != 'bytes' and not (fixed and 1 <= int(fixed.group(1)) <= 32):
            raise TypedDataError('expected type must be bytes or bytes1 through bytes32')
        raw = parse_hex(field['value'], int(fixed.group(1)) if fixed else None)
        result[path] = {'type': kind, 'value': '0x' + raw.hex()}
    return result


def review(data, policy=None, expected_digest=None):
    hashes = digest(data)  # Validate all types and values, not just byte fields.
    wanted = expectations(policy) if policy is not None else None
    expected = parse_hex(expected_digest, 32) if expected_digest is not None else None
    encoder = Encoder(data['types'])
    fields = []

    def visit(kind, value, path):
        array = ARRAY.fullmatch(kind)
        if array:
            for index, child in enumerate(value):
                visit(array.group(1), child, path + '/' + str(index))
        elif kind in data['types']:
            for field in data['types'][kind]:
                visit(field['type'], value[field['name']], path + '/' + field['name'])
        elif kind == 'bytes' or FIXED_BYTES.fullmatch(kind):
            raw = parse_hex(value)
            dynamic = kind == 'bytes'
            fields.append({
                'path': path, 'type': kind, 'value': '0x' + raw.hex(),
                'inputBytes': len(raw), 'encoding': 'keccak256_contents' if dynamic else 'right_zero_pad',
                'paddingBytes': 0 if dynamic else 32 - len(raw),
                'word': '0x' + encoder.value_word(kind, value).hex(),
                'zeroByteOffsets': [i for i, byte in enumerate(raw) if byte == 0],
                'empty': not raw,
            })
            render({'fields': fields})  # Fail closed, never omit a field.

    visit('EIP712Domain', data['domain'], '/domain')
    visit(data['primaryType'], data['message'], '/message')
    report = {
        'reviewVersion': 1, **hashes, 'fields': fields, 'byteFieldCount': len(fields),
        'expectationsProvided': wanted is not None,
        'digestExpectationProvided': expected is not None,
        'interpretation': 'Exact bytes and declared types are compared, never padded, trimmed or repaired '
                          'in the input. Matching byte fields does not pin non-byte values or the whole schema. '
                          'A matching digest is not signing approval, ownership or contract support.',
    }
    checks = []
    if wanted is not None:
        actual = {f['path']: {'type': f['type'], 'value': f['value']} for f in fields}
        missing = sorted(set(actual) - set(wanted))
        extra = sorted(set(wanted) - set(actual))
        for path in sorted(set(actual) & set(wanted)):
            checks.append({'path': path, 'typeMatches': actual[path]['type'] == wanted[path]['type'],
                           'bytesMatch': actual[path]['value'] == wanted[path]['value'],
                           'expected': wanted[path], 'actual': actual[path]})
        report.update(unpinnedPaths=missing, absentPaths=extra, checks=checks,
                      byteExpectationsMatch=not missing and not extra and
                      all(c['typeMatches'] and c['bytesMatch'] for c in checks))
    if expected is not None:
        report['digestMatchesExpected'] = expected.hex() == hashes['digest'][2:]
    report['checksPass'] = (None if wanted is None and expected is None else
                            report.get('byteExpectationsMatch', True) and
                            report.get('digestMatchesExpected', True))
    render(report)
    return report


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('input', help='typed-data JSON beneath cwd')
    parser.add_argument('--bytes-expect', help='independently prepared complete byte expectations beneath cwd')
    parser.add_argument('--digest-expect', help='independently obtained full 32-byte digest')
    args = parser.parse_args(argv)
    try:
        data = load_workspace_json(args.input)
        policy = load_workspace_json(args.bytes_expect) if args.bytes_expect is not None else None
        if args.bytes_expect is not None:
            expectations(policy)  # JSON null cannot silently disable requested checks.
        report = review(data, policy, args.digest_expect)
        print(render(report), end='')
        return 1 if report['checksPass'] is False else 0
    except (ValueError, OSError, RecursionError) as exc:
        print('bytes-review: ' + json.dumps(str(exc), ensure_ascii=True), file=sys.stderr)
        return 2


if __name__ == '__main__':
    sys.exit(main())
