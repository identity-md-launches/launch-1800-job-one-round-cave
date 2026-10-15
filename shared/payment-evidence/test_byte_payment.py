"""Mandatory cross-line gates over the retained real ZTO payment fixture."""
import contextlib
import copy
import io
import json
from pathlib import Path
import unittest
from unittest.mock import patch

import byte_payment as b
from check import load, check

HERE = Path(__file__).resolve().parent
DOMAIN = {'name': 'Read-only Payment Evidence', 'version': '1', 'chainId': 1}
DIGEST = '0x41d9999db383e39c78be45661d68307592ad1b8da2fcace128efcfa5e4e29d2c'


class BytePaymentTests(unittest.TestCase):
    def setUp(self):
        self.sample = load(HERE/'example.transcript.json')
        self.policy = load(HERE/'example.policy.json')
        self.client = load(HERE/'example.typed-data.json')
        self.wanted = load(HERE/'example.bytes-expectations.json')

    def review(self, digest=DIGEST, domain=DOMAIN):
        return b.review(self.sample, self.policy, self.client, domain,
                        'PaymentEvidence', digest, self.wanted)

    def test_saved_real_zto(self):
        result = self.review()
        self.assertTrue(result['accepted'])
        self.assertEqual(result['byteReview']['byteFieldCount'], 2)
        self.assertFalse(result['paymentReview']['providerAuthenticated'])

    def test_expectation_substitution_rejects_despite_payment_match(self):
        self.wanted['fields']['/message/transactionHash']['value'] = self.policy['tx'][:-2]+'f8'
        result = self.review()
        self.assertTrue(result['paymentReview']['accepted'])
        self.assertFalse(result['accepted'])
        self.assertEqual(result['alerts'], ['independent_byte_expectations_mismatch'])

    def test_client_substitution_rejects(self):
        self.client['message']['transactionHash'] = self.policy['tx'][:-2]+'f8'
        result = self.review()
        self.assertFalse(result['accepted'])
        self.assertFalse(result['byteReview']['checksPass'])

    def test_missing_expectation_rejects(self):
        del self.wanted['fields']['/message/transcriptHash']
        self.assertFalse(self.review()['accepted'])

    def test_absent_field_rejects(self):
        self.wanted['fields']['/message/absent'] = self.wanted['fields']['/message/transcriptHash']
        self.assertFalse(self.review()['accepted'])

    def test_null_cannot_disable_gate(self):
        self.wanted = None
        with self.assertRaises(ValueError): self.review()

    def test_digest_cannot_be_omitted(self):
        with self.assertRaises(ValueError): self.review(digest=None)

    def test_nonbyte_change_cannot_bypass_full_commitment(self):
        self.client['message']['minimumRaw'] = str(int(self.policy['minimum_raw'])+1)
        result = self.review()
        self.assertTrue(result['byteReview']['byteExpectationsMatch'])
        self.assertFalse(result['accepted'])

    def test_unsafe_integer_form_still_rejects(self):
        self.client['message']['minimumRaw'] = int(self.policy['minimum_raw'])
        result = self.review()
        self.assertTrue(result['byteReview']['checksPass'])
        self.assertFalse(result['accepted'])

    def test_independent_domain_still_required(self):
        result = self.review(domain={**DOMAIN, 'chainId': 2})
        self.assertTrue(result['byteReview']['checksPass'])
        self.assertFalse(result['accepted'])

    def test_matching_client_cannot_bypass_payment_shortfall(self):
        self.policy['minimum_raw'] = str(int(self.policy['minimum_raw'])+1)
        self.sample['policy'] = copy.deepcopy(self.policy)
        evidence = check(self.sample, self.policy)
        self.client = evidence['typedData']
        self.wanted['fields']['/message/transcriptHash']['value'] = self.client['message']['transcriptHash']
        result = self.review(digest=evidence['commitment']['digest'])
        self.assertTrue(result['byteReview']['checksPass'])
        self.assertFalse(result['paymentReview']['paymentAccepted'])
        self.assertFalse(result['accepted'])

    def test_policy_substitution_rejects(self):
        self.sample['policy']['minimum_raw'] = '1'
        with self.assertRaises(ValueError): self.review()

    def test_no_network_or_mutation(self):
        before = copy.deepcopy((self.sample, self.policy, self.client, self.wanted))
        with patch('urllib.request.OpenerDirector.open', side_effect=AssertionError('network')):
            self.assertTrue(self.review()['accepted'])
        self.assertEqual(before, (self.sample, self.policy, self.client, self.wanted))

    def test_bound_has_no_partial_output(self):
        with patch.object(b, 'MAX_OUTPUT', 10), self.assertRaises(ValueError): self.review()

    def test_hex_case_equivalent(self):
        for f in self.wanted['fields'].values(): f['value'] = '0x'+f['value'][2:].upper()
        self.assertTrue(self.review()['accepted'])

    def test_cli(self):
        args = [str(HERE/'example.transcript.json'),str(HERE/'example.policy.json'),
                str(HERE/'example.typed-data.json'),'--chain-id','1','--name',DOMAIN['name'],
                '--version','1','--primary-type','PaymentEvidence','--no-verifier',
                '--expect-digest',DIGEST,'--expect-bytes',str(HERE/'example.bytes-expectations.json')]
        with contextlib.redirect_stdout(io.StringIO()) as out:
            self.assertEqual(b.main(args),0)
        self.assertTrue(json.loads(out.getvalue())['accepted'])
        del self.wanted['fields']['/message/transcriptHash']
        with patch.object(b,'load',side_effect=[self.sample,self.policy,self.client,self.wanted]), contextlib.redirect_stdout(io.StringIO()) as out:
            self.assertEqual(b.main(args),1)
        self.assertFalse(json.loads(out.getvalue())['accepted'])
        with patch.object(b,'load',side_effect=[self.sample,self.policy,self.client,None]), contextlib.redirect_stdout(io.StringIO()) as out:
            self.assertEqual(b.main(args),2)
        self.assertEqual(json.loads(out.getvalue()),{'accepted':False,'state':'input_error'})


if __name__ == '__main__':
    unittest.main(verbosity=2)
