#!/usr/bin/env python3
"""Show safe, bounded source context for offline JSON contract violations."""
import argparse
from bisect import bisect_right
import hashlib
import json
from pathlib import Path
import re
import sys
import types

MAX_OUTPUT_BYTES = 100_000
WINDOW_CHARS = 160

def bounded_module():
    # Bootstrap only the fixed, trusted sibling; user inputs use its no-follow reader.
    source = Path(__file__).absolute().parent.parent / 'bounded-contract' / 'check.py'
    relative = source.relative_to(Path.cwd()).as_posix()
    if any(not p or p.startswith('.') for p in relative.split('/')):
        raise ValueError('run inside the workspace containing the sibling tools')
    # Open each component without following links, including the trusted bootstrap.
    import os
    import stat
    directory = os.open('.', os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
    leaf = None
    try:
        parts = relative.split('/')
        for part in parts[:-1]:
            child = os.open(part, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW,
                            dir_fd=directory)
            os.close(directory)
            directory = child
        leaf = os.open(parts[-1], os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK,
                       dir_fd=directory)
        if not stat.S_ISREG(os.fstat(leaf).st_mode):
            raise ValueError('trusted sibling must be a regular file')
        chunks, remaining = [], 1_000_001
        while remaining:
            chunk = os.read(leaf, min(65536, remaining))
            if not chunk:
                break
            chunks.append(chunk)
            remaining -= len(chunk)
        code = b''.join(chunks)
        if len(code) > 1_000_000:
            raise ValueError('trusted sibling exceeds byte limit')
    finally:
        if leaf is not None:
            os.close(leaf)
        os.close(directory)
    module = types.ModuleType('repair_bounded_contract')
    module.__file__ = str(source)
    exec(compile(code, str(source), 'exec'), module.__dict__)
    return module



def dependencies():
    reader = bounded_module()
    path = Path(__file__).absolute().parent.parent / 'source-locator' / 'locate.py'
    module = types.ModuleType('context_source_locator')
    module.__file__ = str(path)
    relative = path.relative_to(Path.cwd()).as_posix()
    exec(compile(reader.read_bytes(relative), str(path), 'exec'), module.__dict__)
    _, engine, rules = module.dependencies()
    return reader, module, engine, rules


def bounded_json(value):
    """Encode all diagnostics or reject; never emit a partial report."""
    pieces, size = [], 0
    encoder = json.JSONEncoder(ensure_ascii=True, allow_nan=False, indent=2)
    for chunk in encoder.iterencode(value):
        size += len(chunk)  # ensure_ascii makes character and byte counts equal
        if size + 1 > MAX_OUTPUT_BYTES:
            raise ValueError('complete output exceeds 100,000 bytes; no diagnostics emitted')
        pieces.append(chunk)
    return ''.join(pieces) + '\n'


def context(source, location):
    """Bound excerpts, retaining the exact full span and explicit omissions."""
    present = location['present']
    span = location['value'] if present else location['anchor']['value']
    start, end = span['start']['char_offset'], span['end']['char_offset']
    first = bisect_right(source.lines, start) - 1
    # A closing token ending at a newline boundary belongs to the previous line.
    last = bisect_right(source.lines, max(start, end - 1)) - 1
    selected_lines = sorted({first, last, max(0, first - 1),
                             min(len(source.lines) - 1, last + 1)})
    excerpts = []
    for row in selected_lines:
        lo = source.lines[row]
        hi = source.lines[row + 1] - 1 if row + 1 < len(source.lines) else len(source.text)
        a, b = max(lo, start), min(hi, end)
        intersects = a < b
        if intersects:
            left = max(lo, a - 24)
            right = min(hi, left + WINDOW_CHARS)
            windows = [(left, right)]
            if b > right:
                left2 = max(right, b - (WINDOW_CHARS - 24))
                windows.append((left2, min(hi, left2 + WINDOW_CHARS)))
        else:
            windows = [(lo, min(hi, lo + WINDOW_CHARS))]
        for left, right in windows:
            cut_start, cut_end = max(left, start), min(right, end)
            if cut_start >= cut_end:
                cut_start = cut_end = left
            excerpts.append({'line': row + 1, 'column': left - lo + 1,
                             'char_start': left, 'char_end': right,
                             'before': source.text[left:cut_start],
                             'selected': source.text[cut_start:cut_end],
                             'after': source.text[cut_end:right],
                             'omitted_before_chars': left - lo,
                             'omitted_after_chars': hi - right})
    result = {'kind': 'value' if present else 'missing_value_parent_anchor',
              'span': span, 'excerpts': excerpts,
              'omitted_lines': last - first + 1 - len(
                  [row for row in selected_lines if first <= row <= last])}
    if not present:
        result['anchor_path'] = location['anchor']['path']
    return result


def inspect(reader, source, engine, rules, contract_name, document_name,
            contract_sha256=None, document_sha256=None):
    for pin in (contract_sha256, document_sha256):
        if pin is not None and not re.fullmatch('[0-9a-f]{64}', pin):
            raise ValueError('expected SHA-256 must be 64 lowercase hex digits')
    captured = {}
    def capture(name, pin):
        if name not in captured:
            captured[name] = reader.read_bytes(name)
        data = captured[name]
        if pin is not None and hashlib.sha256(data).hexdigest() != pin:
            raise ValueError('source SHA-256 mismatch: ' + name)
        return source.Source(data, name)
    contract = capture(contract_name, contract_sha256)
    engine.prepare(contract.value)  # invalid contract rejects before document read
    document = capture(document_name, document_sha256)
    report = source.locate(engine, rules, contract, document)
    for error in report['errors']:
        error['document_context'] = context(document, error['document_source'])
        error['contract_context'] = context(contract, error['contract_source'])
    report['context_display'] = {
        'text': 'JSON-quoted ASCII; escapes are display text, not source columns',
        'selection': 'selected is the intersection with the full token or parent anchor',
        'limits': '160 code points per excerpt; head/tail and neighboring lines; omissions explicit'}
    return report


def text_report(report):
    """Quote untrusted strings, preventing terminal escape/control injection."""
    quote = lambda value: json.dumps(value, ensure_ascii=True, allow_nan=False)
    parts, size = [], 0
    def add(line):
        nonlocal size
        size += len(line) + 1
        if size > MAX_OUTPUT_BYTES:
            raise ValueError('complete output exceeds 100,000 bytes; no diagnostics emitted')
        parts.append(line)
    add(('VALID' if report['valid'] else 'INVALID') +
        ': ' + str(report['error_count']) + ' structural violations')
    for role in ('document', 'contract'):
        identity = report['sources'][role]
        add(role + ' ' + quote(identity['file']) + ' SHA-256 ' + identity['sha256'])
    add('Text is JSON-quoted ASCII; columns refer to original Unicode code points.')
    for index, error in enumerate(report['errors'], 1):
        add('')
        add(str(index) + '. ' + quote(error['path']) + ' ' + quote(error['rule']) +
            ': ' + quote(error['message']))
        for role in ('document', 'contract'):
            ctx = error[role + '_context']
            span = ctx['span']
            add('  ' + role + ' ' + ctx['kind'] + ' bytes [' +
                str(span['start']['byte_offset']) + ', ' +
                str(span['end']['byte_offset']) + ')')
            if 'anchor_path' in ctx:
                add('    missing token; containing object ' + quote(ctx['anchor_path']))
            for row in ctx['excerpts']:
                add('    L' + str(row['line']) + ':C' + str(row['column']) +
                    ' before=' + quote(row['before']) +
                    ' selected=' + quote(row['selected']) + ' after=' + quote(row['after']) +
                    ' omitted chars=' + str(row['omitted_before_chars']) + '/' +
                    str(row['omitted_after_chars']))
            if ctx['omitted_lines']:
                add('    omitted interior lines=' + str(ctx['omitted_lines']))
    return '\n'.join(parts) + '\n'


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('contract', help='explicit relative workspace contract')
    parser.add_argument('document', help='explicit relative workspace JSON document')
    parser.add_argument('--json', action='store_true', help='emit complete JSON with contexts')
    parser.add_argument('--contract-sha256', help='separately retained exact contract byte hash')
    parser.add_argument('--document-sha256', help='separately retained exact document byte hash')
    args = parser.parse_args(argv)
    try:
        report = inspect(*dependencies(), args.contract, args.document,
                         args.contract_sha256, args.document_sha256)
        # Bound both representations, even when only one is requested.
        encoded = bounded_json(report)
        rendered = text_report(report)
        sys.stdout.write(encoded if args.json else rendered)
        return 0 if report['valid'] else 1
    except (ValueError, OSError, RecursionError, KeyError, IndexError) as exc:
        sys.stdout.write(json.dumps({'valid': False, 'status': 'input_or_output_error',
                                    'error': str(exc)[:1000]}, ensure_ascii=True) + '\n')
        return 2


if __name__ == '__main__':
    sys.exit(main())
