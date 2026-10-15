#!/usr/bin/env python3
"""Review payment evidence, integer precision and independently retained byte fields."""
import argparse
import json

from check import load
from precision_payment import review as precision_review
from bytes_review import review as byte_review, expectations

MAX_OUTPUT = 100_000


def render(report):
    text = json.dumps(report, indent=2, ensure_ascii=True, allow_nan=False) + '\n'
    if len(text.encode('ascii')) > MAX_OUTPUT:
        raise ValueError('payment byte report exceeds 100000 bytes')
    return text


def review(sample, policy, client, expected_domain, primary_type, expected_digest,
           expected_bytes):
    """All gates are mandatory; no incoming field can choose its expectations."""
    expectations(expected_bytes)  # None must never disable the byte comparison.
    exact = precision_review(sample, policy, client, expected_domain, primary_type,
                             expected_digest)
    byte_report = byte_review(client, expected_bytes, expected_digest)
    alerts = list(exact['alerts'])
    if not byte_report['byteExpectationsMatch']:
        alerts.append('independent_byte_expectations_mismatch')
    result = {
        'accepted': exact['accepted'] and byte_report['checksPass'] is True,
        'state': 'payment_and_byte_review_match' if not alerts else 'review_required',
        'alerts': alerts,
        'paymentReview': exact,
        'byteReview': byte_report,
        'authorization': 'Historical evidence review only; no signing or payment authorization.'}
    render(result)
    return result


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('transcript')
    parser.add_argument('policy')
    parser.add_argument('client')
    parser.add_argument('--chain-id', required=True)
    parser.add_argument('--name', required=True)
    parser.add_argument('--version', required=True)
    parser.add_argument('--primary-type', required=True)
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument('--verifier')
    group.add_argument('--no-verifier', action='store_true')
    parser.add_argument('--salt')
    parser.add_argument('--expect-digest', required=True)
    parser.add_argument('--expect-bytes', required=True, help='independently retained complete byte expectations')
    args = parser.parse_args(argv)
    expected = {'chainId': args.chain_id, 'name': args.name, 'version': args.version}
    if args.verifier is not None:
        expected['verifyingContract'] = args.verifier
    if args.salt is not None:
        expected['salt'] = args.salt
    try:
        result = review(load(args.transcript), load(args.policy), load(args.client),
                        expected, args.primary_type, args.expect_digest, load(args.expect_bytes))
        print(render(result), end='')
        return 0 if result['accepted'] else 1
    except (ValueError, OSError, TypeError, KeyError, RecursionError):
        print('{"accepted":false,"state":"input_error"}')
        return 2


if __name__ == '__main__':
    raise SystemExit(main())
