"""Meaningful source-context regressions; filesystem fixtures live in scratch."""
import contextlib
import hashlib
import importlib.util
import io
import json
from pathlib import Path
import socket
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

spec = importlib.util.spec_from_file_location('source_context', Path(__file__).with_name('show.py'))
show = importlib.util.module_from_spec(spec)
spec.loader.exec_module(show)


class MemoryReader:
    def __init__(self, files):
        self.files, self.reads = files, []

    def read_bytes(self, name):
        self.reads.append(name)
        return self.files[name]


class ContextTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.reader, cls.source, cls.engine, cls.rules = show.dependencies()
        Path('test/scratch').mkdir(parents=True, exist_ok=True)

    def inspect(self, contract, document, **kwargs):
        files = {'contract.json': contract, 'document.json': document}
        reader = MemoryReader(files)
        result = show.inspect(reader, self.source, self.engine, self.rules,
                              'contract.json', 'document.json', **kwargs)
        self.assertEqual(reader.reads, ['contract.json', 'document.json'])
        return result

    def assert_excerpt_slices(self, ctx, raw):
        text = raw.decode('utf-8')
        span = ctx['span']
        self.assertEqual(raw[span['start']['byte_offset']:span['end']['byte_offset']].decode(),
                         text[span['start']['char_offset']:span['end']['char_offset']])
        for row in ctx['excerpts']:
            piece = row['before'] + row['selected'] + row['after']
            self.assertEqual(piece, text[row['char_start']:row['char_end']])
            self.assertLessEqual(len(piece), show.WINDOW_CHARS)
            if row['selected']:
                begin = row['char_start'] + len(row['before'])
                end = begin + len(row['selected'])
                self.assertGreaterEqual(begin, span['start']['char_offset'])
                self.assertLessEqual(end, span['end']['char_offset'])

    def test_saved_zto_policy_valid_and_offline(self):
        c, d = 'shared/payment-evidence/policy.contract.json', 'shared/payment-evidence/example.policy.json'
        with patch.object(socket, 'socket', side_effect=AssertionError('network forbidden')):
            result = show.inspect(self.reader, self.source, self.engine, self.rules, c, d)
        self.assertTrue(result['valid'])
        self.assertEqual(result['error_count'], 0)
        self.assertIn('VALID: 0', show.text_report(result))
        for role, name in [('contract', c), ('document', d)]:
            self.assertEqual(result['sources'][role]['sha256'],
                             hashlib.sha256(Path(name).read_bytes()).hexdigest())

    def test_inherited_diagnostics_unchanged_except_contexts(self):
        c, d = 'line-2/tools/json-contract/report.contract.json', 'line-2/tools/rule-locator/report.invalid.json'
        cs = self.source.Source(Path(c).read_bytes(), c)
        ds = self.source.Source(Path(d).read_bytes(), d)
        expected = self.source.locate(self.engine, self.rules, cs, ds)
        result = show.inspect(self.reader, self.source, self.engine, self.rules, c, d)
        self.assertEqual(result['error_count'], 3)
        for new, old in zip(result['errors'], expected['errors']):
            stripped = {k: v for k, v in new.items() if not k.endswith('_context')}
            self.assertEqual(stripped, old)
            self.assert_excerpt_slices(new['document_context'], ds.data)
            self.assert_excerpt_slices(new['contract_context'], cs.data)
        self.assertEqual(result['errors'][0]['document_context']['excerpts'][1]['selected'], '"yes"')
        self.assertEqual(result['errors'][2]['contract_context']['excerpts'][1]['selected'], 'false')

    def test_unicode_crlf_tabs_and_escaped_key(self):
        c = '{"type":"object","properties":{"é/🐸":{"type":"integer"}}}'.encode()
        d = '{\r\n\t"é\\/🐸": "日", "other": 2\r\n}'.encode()
        result = self.inspect(c, d)
        err = result['errors'][0]
        self.assertEqual(err['path'], '/é~1🐸')
        for role, raw in [('document', d), ('contract', c)]:
            self.assert_excerpt_slices(err[role + '_context'], raw)
        token = err['document_context']['span']
        self.assertEqual(d[token['start']['byte_offset']:token['end']['byte_offset']], '"日"'.encode())
        self.assertIn('\\u65e5', show.text_report(result))
        self.assertNotIn('日', show.text_report(result))
        self.assertIn('\\r', show.text_report(result))

    def test_missing_value_anchors_parent_without_invented_token(self):
        c = b'{"type":"object","required":["missing"],"properties":{"missing":{"type":"string"}}}'
        d = b'{\n "present":null\n}'
        result = self.inspect(c, d)
        err = result['errors'][0]
        self.assertFalse(err['document_source']['present'])
        ctx = err['document_context']
        self.assertEqual(ctx['kind'], 'missing_value_parent_anchor')
        self.assertEqual(ctx['anchor_path'], '')
        self.assert_excerpt_slices(ctx, d)
        self.assertIn('missing token; containing object ""', show.text_report(result))

    def test_null_is_present(self):
        result = self.inspect(b'{"type":"string"}', b'null')
        ctx = result['errors'][0]['document_context']
        self.assertEqual(ctx['kind'], 'value')
        self.assertEqual(ctx['excerpts'][0]['selected'], 'null')

    def test_multiline_root_preserves_head_tail_and_reports_omitted_lines(self):
        d = ('[\n' + ',\n'.join(str(i) for i in range(100)) + '\n]').encode()
        result = self.inspect(b'{"type":"object"}', d)
        ctx = result['errors'][0]['document_context']
        self.assertEqual(ctx['omitted_lines'], 100)
        self.assertEqual([x['line'] for x in ctx['excerpts']], [1, 102])
        self.assert_excerpt_slices(ctx, d)

    def test_long_single_line_has_bounded_head_tail_and_explicit_omission(self):
        d = json.dumps('a' * 20000).encode()
        result = self.inspect(b'{"type":"integer"}', d)
        ctx = result['errors'][0]['document_context']
        self.assertEqual(len(ctx['excerpts']), 2)
        self.assertGreater(ctx['excerpts'][0]['omitted_after_chars'], 19000)
        self.assertGreater(ctx['excerpts'][1]['omitted_before_chars'], 19000)
        self.assertEqual(ctx['excerpts'][0]['selected'][0], '"')
        self.assertEqual(ctx['excerpts'][-1]['selected'][-1], '"')
        self.assert_excerpt_slices(ctx, d)
        self.assertLess(len(show.bounded_json(result)), 100000)

    def test_terminal_control_characters_and_ansi_cannot_execute(self):
        # Source spelling and decoded property names both need safe quoting.
        name = '\x1b[31m\u202e\n'
        d = json.dumps({name: 1}).encode()
        result = self.inspect(b'{"type":"object","additionalProperties":false}', d)
        rendered = show.text_report(result)
        self.assertTrue(rendered.isascii())
        self.assertNotIn('\x1b', rendered)
        self.assertIn('\\u001b', rendered)
        self.assertIn('\\u202e', rendered)
        self.assert_excerpt_slices(result['errors'][0]['document_context'], d)

    def test_correct_separately_retained_pins(self):
        c, d = b'{"type":"integer"}', b'3'
        result = self.inspect(c, d, contract_sha256=hashlib.sha256(c).hexdigest(),
                              document_sha256=hashlib.sha256(d).hexdigest())
        self.assertTrue(result['valid'])

    def test_contract_pin_failure_stops_before_document_read(self):
        reader = MemoryReader({'c.json': b'{"type":"null"}'})
        with self.assertRaisesRegex(ValueError, 'SHA-256 mismatch'):
            show.inspect(reader, self.source, self.engine, self.rules, 'c.json', 'unread.json',
                         contract_sha256=hashlib.sha256(b'other bytes').hexdigest())
        self.assertEqual(reader.reads, ['c.json'])

    def test_document_whitespace_change_rejects_original_pin(self):
        with self.assertRaisesRegex(ValueError, 'SHA-256 mismatch'):
            self.inspect(b'{"type":"null"}', b'null\n',
                         document_sha256=hashlib.sha256(b'null').hexdigest())

    def test_malformed_pin_stops_before_input_read(self):
        reader = MemoryReader({})
        with self.assertRaisesRegex(ValueError, 'lowercase hex'):
            show.inspect(reader, self.source, self.engine, self.rules, 'a', 'b', document_sha256='wrong')
        self.assertEqual(reader.reads, [])

    def test_shared_path_captured_once(self):
        reader = MemoryReader({'same.json': b'{"type":"object"}'})
        result = show.inspect(reader, self.source, self.engine, self.rules, 'same.json', 'same.json')
        self.assertTrue(result['valid'])
        self.assertEqual(reader.reads, ['same.json'])

    def test_invalid_contract_stops_before_document_read(self):
        reader = MemoryReader({'c': b'{"unsupported":true}'})
        with self.assertRaisesRegex(ValueError, 'unsupported rules'):
            show.inspect(reader, self.source, self.engine, self.rules, 'c', 'unread')
        self.assertEqual(reader.reads, ['c'])

    def test_malformed_duplicate_nonfinite_and_utf8_reject(self):
        for d in (b'{', b'{"x":1,"x":2}', b'NaN', b'1e999', b'"\xff"'):
            with self.subTest(d=d), self.assertRaises(ValueError):
                self.inspect(b'{"type":"string"}', d)

    def test_escaped_surrogate_preserves_inherited_parsing_and_safe_display(self):
        result = self.inspect(b'{"type":"integer"}', b'"\\ud800"')
        self.assertFalse(result['valid'])
        self.assertTrue(show.text_report(result).isascii())
        self.assert_excerpt_slices(result['errors'][0]['document_context'], b'"\\ud800"')

    def test_output_limit_fails_closed_without_partial_diagnostics(self):
        result = self.inspect(b'{"type":"integer"}', b'"bad"')
        with patch.object(show, 'MAX_OUTPUT_BYTES', 100):
            with self.assertRaisesRegex(ValueError, 'no diagnostics emitted'):
                show.bounded_json(result)
            with self.assertRaisesRegex(ValueError, 'no diagnostics emitted'):
                show.text_report(result)
            output = io.StringIO()
            with patch.object(show, 'inspect', return_value=result), contextlib.redirect_stdout(output):
                code = show.main(['c', 'd', '--json'])
            self.assertEqual(code, 2)
            error = json.loads(output.getvalue())
            self.assertEqual(error['status'], 'input_or_output_error')
            self.assertNotIn('errors', error)

    def test_real_output_overflow_rejects_every_diagnostic_together(self):
        result = self.inspect(b'{"type":"array","items":{"type":"integer"}}',
                              json.dumps(['bad'] * 80).encode())
        self.assertEqual(result['error_count'], 80)
        with self.assertRaisesRegex(ValueError, 'complete output exceeds'):
            show.bounded_json(result)

    def test_cli_exit_codes_and_input_immutability(self):
        with tempfile.TemporaryDirectory(dir='test/scratch') as root:
            c, d = Path(root) / 'c.json', Path(root) / 'd.json'
            c.write_bytes(b'{"type":"integer"}')
            for raw, wanted in [(b'2', 0), (b'"bad"', 1), (b'{', 2)]:
                d.write_bytes(raw)
                run = subprocess.run([sys.executable, '-B', str(Path(__file__).with_name('show.py')),
                                      c.relative_to(Path.cwd()).as_posix(), d.relative_to(Path.cwd()).as_posix(), '--json'], capture_output=True, text=True)
                self.assertEqual(run.returncode, wanted, run.stdout + run.stderr)
                self.assertEqual(run.stderr, '')
                self.assertEqual(json.loads(run.stdout)['valid'], wanted == 0)
                self.assertEqual(c.read_bytes(), b'{"type":"integer"}')
                self.assertEqual(d.read_bytes(), raw)

    def test_no_follow_and_path_boundary(self):
        with tempfile.TemporaryDirectory(dir='test/scratch') as root:
            target = Path(root) / 'target.json'
            target.write_bytes(b'null')
            link = Path(root) / 'link.json'
            link.symlink_to(target.name)
            for name in (link.relative_to(Path.cwd()).as_posix(), '../outside', '/etc/passwd', '.hidden', Path(root).relative_to(Path.cwd()).as_posix()):
                with self.subTest(name=name), self.assertRaises((ValueError, OSError)):
                    show.inspect(self.reader, self.source, self.engine, self.rules,
                                 'line-2/tools/json-contract/report.contract.json', name)


if __name__ == '__main__':
    unittest.main(verbosity=2)
