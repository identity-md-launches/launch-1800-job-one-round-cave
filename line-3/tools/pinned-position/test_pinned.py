import contextlib
import hashlib
import importlib.util
import io
import json
from pathlib import Path
import unittest
from unittest.mock import patch

HERE = Path(__file__).parent
spec = importlib.util.spec_from_file_location('pin_review', HERE / 'pinned.py')
g = importlib.util.module_from_spec(spec)
spec.loader.exec_module(g)
EVIDENCE = HERE.parent / 'tx-position' / 'live-evidence.json'


class PinnedTests(unittest.TestCase):
    def setUp(self):
        self.raw = EVIDENCE.read_bytes()
        self.policy = g.p.policy(g.p.DEMO_TX, 12, True)
        self.scratch = Path('test/scratch/pinned-position')
        self.scratch.mkdir(parents=True, exist_ok=True)

    def review(self, raw=None, pin=None):
        return g.review_bytes(self.raw if raw is None else raw,
                              g.DEMO_PIN if pin is None else pin, self.policy)

    def test_historical_real_zto(self):
        result = self.review()
        self.assertTrue(result['accepted'])
        self.assertTrue(result['exactBytesMatch'])
        self.assertEqual(result['positionReview']['transactionIndex'], 181)
        self.assertEqual(result['positionReview']['transactionCount'], 498)

    def test_whitespace_replacement(self):
        result = self.review(self.raw + b'\n')
        self.assertFalse(result['accepted'])
        self.assertEqual(result['state'], 'evidence_pin_mismatch')
        self.assertNotIn('positionReview', result)

    def test_mismatch_never_parses(self):
        with patch.object(g.p.s, 'strict_json', side_effect=AssertionError('parsed')):
            self.assertFalse(self.review(b'not json')['accepted'])

    def test_matching_hash_still_rejects_wrong_position(self):
        sample = json.loads(self.raw)
        sample['reads'][8]['result']['transactionIndex'] = '0xb6'
        raw = json.dumps(sample).encode()
        result = self.review(raw, hashlib.sha256(raw).hexdigest())
        self.assertTrue(result['exactBytesMatch'])
        self.assertFalse(result['accepted'])
        self.assertIn('transaction_missing_at_receipt_index', result['positionReview']['alerts'])

    def test_matching_hash_still_requires_independent_policy(self):
        self.policy['minimumConfirmations'] = 13
        with self.assertRaises(g.Error):
            self.review()

    def test_matching_hash_rejects_duplicate_keys(self):
        raw = b'{"version":1,"version":1}'
        with self.assertRaises(g.Error):
            self.review(raw, hashlib.sha256(raw).hexdigest())

    def test_matching_hash_rejects_invalid_json(self):
        for raw in (b'not json', b'{"x":NaN}', b'\xff'):
            with self.subTest(raw=raw), self.assertRaises(g.Error):
                self.review(raw, hashlib.sha256(raw).hexdigest())

    def test_extra_read_with_new_pin_rejects(self):
        sample = json.loads(self.raw)
        sample['reads'].append(sample['reads'][-1])
        raw = json.dumps(sample).encode()
        with self.assertRaises(g.Error):
            self.review(raw, hashlib.sha256(raw).hexdigest())

    def test_bad_pin_before_open(self):
        for value in (None, True, 'A'*64, 'b'*63, '0x'+'b'*64):
            with self.subTest(value=value), patch.object(g, 'load_bytes', side_effect=AssertionError('opened')):
                with self.assertRaises(g.Error):
                    g.review_file('missing', value, self.policy)

    def test_bad_policy_before_open(self):
        self.policy['requireFinalized'] = 1
        with patch.object(g, 'load_bytes', side_effect=AssertionError('opened')):
            with self.assertRaises(g.Error):
                g.review_file('missing', g.DEMO_PIN, self.policy)

    def test_read_exact_bytes(self):
        path = self.scratch / 'evidence.json'
        path.write_bytes(self.raw)
        self.assertEqual(g.load_bytes(path), self.raw)
        self.assertTrue(g.review_file(path, g.DEMO_PIN, self.policy)['accepted'])

    def test_file_limit(self):
        path = self.scratch / 'large.json'
        path.write_bytes(b' ' * g.LIMIT)
        self.assertEqual(len(g.load_bytes(path)), g.LIMIT)
        path.write_bytes(b' ' * (g.LIMIT + 1))
        with self.assertRaises(g.Error):
            g.load_bytes(path)

    def test_bytes_limit_and_type(self):
        for value in (bytearray(self.raw), 'text', b' '*(g.LIMIT+1)):
            with self.subTest(kind=type(value)), self.assertRaises(g.Error):
                self.review(value)

    def test_unsafe_paths(self):
        for path in ('/etc/passwd', '../x', '.git/config', 'test//x', 'test/./x', 'test/../x', 'test\\x'):
            with self.subTest(path=path), self.assertRaises(g.Error):
                g.load_bytes(path)

    def test_symlink_file_and_parent(self):
        path = self.scratch / 'link.json'
        if path.is_symlink():
            path.unlink()
        path.symlink_to(EVIDENCE.resolve())
        with self.assertRaises(g.Error):
            g.load_bytes(path)
        directory = self.scratch / 'linked-dir'
        if directory.is_symlink():
            directory.unlink()
        directory.symlink_to(EVIDENCE.parent.resolve(), target_is_directory=True)
        with self.assertRaises(g.Error):
            g.load_bytes(directory / 'live-evidence.json')

    def test_directory_and_fifo(self):
        with self.assertRaises(g.Error):
            g.load_bytes(self.scratch)
        import os
        fifo = self.scratch / 'pipe'
        if not fifo.exists():
            os.mkfifo(fifo)
        with self.assertRaises(g.Error):
            g.load_bytes(fifo)

    def test_demo_no_network_and_no_mutation(self):
        output = io.StringIO()
        with patch.object(g.p.s.RPC, 'call', side_effect=AssertionError('network')), contextlib.redirect_stdout(output):
            self.assertEqual(g.main(['--demo']), 0)
        self.assertTrue(json.loads(output.getvalue())['accepted'])
        self.assertEqual(EVIDENCE.read_bytes(), self.raw)

    def test_cli_mismatch_and_input_error(self):
        path = self.scratch / 'cli.json'
        path.write_bytes(self.raw + b'\n')
        for args, expected in ((['--evidence', str(path), '--sha256', g.DEMO_PIN, '--tx', g.p.DEMO_TX], 1),
                               (['--evidence', str(path)], 2),
                               (['--demo', '--sha256', g.DEMO_PIN], 2)):
            with self.subTest(args=args), contextlib.redirect_stdout(io.StringIO()) as output:
                self.assertEqual(g.main(args), expected)
                self.assertFalse(json.loads(output.getvalue())['accepted'])


if __name__ == '__main__':
    unittest.main()
