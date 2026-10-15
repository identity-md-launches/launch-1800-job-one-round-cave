import copy
import io
import json
from pathlib import Path
import unittest
from contextlib import redirect_stdout, redirect_stderr
from unittest.mock import patch

import bytes_review as br
from typed_digest import TypedDataError, digest, keccak256


def request(kind='bytes', value='0x1200'):
    return {'types': {'EIP712Domain': [], 'Packet': [{'name': 'payload', 'type': kind}]},
            'primaryType': 'Packet', 'domain': {}, 'message': {'payload': value}}


def policy(kind='bytes', value='0x1200'):
    return {'fields': {'/message/payload': {'type': kind, 'value': value}}}


class ByteReviewTests(unittest.TestCase):
    def test_dynamic_hashes_contents(self):
        f = br.review(request())['fields'][0]
        self.assertEqual(f['word'], '0x' + keccak256(b'\x12\x00').hex())
        self.assertEqual(f['zeroByteOffsets'], [1])
        self.assertEqual(f['inputBytes'], 2)
        self.assertEqual(f['encoding'], 'keccak256_contents')

    def test_fixed_right_padding(self):
        f = br.review(request('bytes2'))['fields'][0]
        self.assertEqual(f['word'], '0x1200' + '00' * 30)
        self.assertEqual(f['paddingBytes'], 30)

    def test_all_fixed_widths(self):
        for size in range(1, 33):
            raw = '0x' + 'a1' * size
            f = br.review(request('bytes' + str(size), raw))['fields'][0]
            self.assertEqual(f['word'], raw + '00' * (32-size))

    def test_empty_dynamic_known_vector(self):
        f = br.review(request(value='0x'))['fields'][0]
        self.assertTrue(f['empty'])
        self.assertEqual(f['word'], '0xc5d2460186f7233c927e7db2dcc703c0e500b653ca82273b7bfad8045d85a470')

    def test_zero_is_not_empty(self):
        a = br.review(request(value='0x'))
        b = br.review(request(value='0x00'))
        self.assertNotEqual(a['digest'], b['digest'])
        self.assertFalse(b['fields'][0]['empty'])

    def test_exact_match_and_case(self):
        self.assertTrue(br.review(request(value='0xAB00'), policy(value='0xab00'))['checksPass'])

    def test_byte_substitution(self):
        r = br.review(request(value='0x1201'), policy())
        self.assertFalse(r['checksPass'])
        self.assertFalse(r['checks'][0]['bytesMatch'])

    def test_type_substitution_even_same_word(self):
        r = br.review(request('bytes2'), policy('bytes3', '0x120000'))
        self.assertFalse(r['checksPass'])
        self.assertFalse(r['checks'][0]['typeMatches'])

    def test_complete_coverage_required(self):
        r = br.review(request(), {'fields': {}})
        self.assertEqual(r['unpinnedPaths'], ['/message/payload'])
        self.assertFalse(r['checksPass'])

    def test_absent_path(self):
        p = policy()
        p['fields']['/message/absent'] = {'type': 'bytes', 'value': '0x'}
        r = br.review(request(), p)
        self.assertEqual(r['absentPaths'], ['/message/absent'])
        self.assertFalse(r['checksPass'])

    def test_digest_expectation(self):
        data = request()
        self.assertTrue(br.review(data, policy(), digest(data)['digest'])['checksPass'])
        self.assertFalse(br.review(data, policy(), '0x' + 'ff'*32)['checksPass'])

    def test_inspection_has_no_acceptance(self):
        r = br.review(request())
        self.assertIsNone(r['checksPass'])
        self.assertFalse(r['expectationsProvided'])

    def test_domain_and_nested_arrays(self):
        data = {'types': {'EIP712Domain': [{'name': 'salt', 'type': 'bytes32'}],
                         'Packet': [{'name': 'children', 'type': 'Child[][1]'}],
                         'Child': [{'name': 'value', 'type': 'bytes'}]},
                'primaryType': 'Packet', 'domain': {'salt': '0x' + '12'*32},
                'message': {'children': [[{'value': '0x'}, {'value': '0xff'}]]}}
        r = br.review(data)
        self.assertEqual([f['path'] for f in r['fields']],
                         ['/domain/salt', '/message/children/0/0/value', '/message/children/0/1/value'])

    def test_empty_array_has_no_byte_values(self):
        r = br.review(request('bytes[]', []), {'fields': {}})
        self.assertTrue(r['checksPass'])
        self.assertEqual(r['byteFieldCount'], 0)

    def test_non_byte_values_still_validate(self):
        data = request()
        data['types']['Packet'].append({'name': 'amount', 'type': 'uint8'})
        data['message']['amount'] = 256
        with self.assertRaises(TypedDataError):
            br.review(data)

    def test_bad_hex_and_fixed_width(self):
        for kind, value in [('bytes', '0x1'), ('bytes', '0xgg'), ('bytes2', '0x00'),
                            ('bytes2', '0x000000'), ('bytes', 'abcd')]:
            with self.subTest(kind=kind, value=value), self.assertRaises(TypedDataError):
                br.review(request(kind, value))

    def test_invalid_policies(self):
        invalid = [None, [], {'fields': [],}, {'fields': {}, 'extra': 1},
                   {'fields': {'/other/x': {'type': 'bytes', 'value': '0x'}}},
                   policy('bytes0', '0x'), policy('bytes33', '0x'), policy('address', '0x'),
                   policy('bytes1', '0x'), {'fields': {'/message/payload': {'value': '0x'}}}]
        for p in invalid:
            with self.subTest(policy=p), self.assertRaises(TypedDataError):
                br.expectations(p)

    def test_no_mutation(self):
        data, p = request(), policy()
        before = copy.deepcopy((data, p))
        br.review(data, p)
        self.assertEqual((data, p), before)

    def test_report_bound(self):
        with patch.object(br, 'MAX_REPORT_BYTES', 20), self.assertRaises(TypedDataError):
            br.review(request())

    def test_cli_codes_and_null_policy(self):
        for data, p, expected_code in [(request(), policy(), 0),
                                       (request(value='0x12ff'), policy(), 1),
                                       (request(), None, 2)]:
            with patch.object(br, 'load_workspace_json', side_effect=[data, p]), \
                    redirect_stdout(io.StringIO()) as out, redirect_stderr(io.StringIO()):
                code = br.main(['input.json', '--bytes-expect', 'expect.json'])
            self.assertEqual(code, expected_code)
            if code == 2:
                self.assertEqual(out.getvalue(), '')
            else:
                json.loads(out.getvalue())

    def test_zto_historical_digest_and_byte_expectations(self):
        folder = Path(__file__).parent
        data = json.loads((folder/'zto-payment.json').read_text())
        p = json.loads((folder/'zto-bytes.json').read_text())
        r = br.review(data, p)
        self.assertTrue(r['checksPass'])
        self.assertEqual(r['byteFieldCount'], 2)
        self.assertEqual(r['digest'], '0xf33e2506e5c103f98dbfe3feb6d4b87d55f1fad4e423dbaa8462465ff4ab9774')


if __name__ == '__main__':
    unittest.main()
