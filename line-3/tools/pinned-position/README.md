# Pinned transaction position

Review a retained Ethereum transaction-position transcript against an independently
kept SHA-256 and settlement policy. This Python 3.9+ standard-library tool checks
exact file bytes before parsing JSON, then runs the existing canonicality,
execution, confirmation, finality and transaction-index replay. No installation
or network is needed. Keep the sibling tx-position, payment-witness and
settlement-check folders when copying this tool.

From the repository root, one command shows it working:

```sh
python3 -B line-3/tools/pinned-position/pinned.py --demo
```

When tried, this returned `pinned_position_and_settlement_match`, exit 0. It
replayed the saved real ZTO pool transaction
`0xc4ca304c305cae326cab066639ab2156412eee7f5f774b41a2a136369f817ef7`,
at index 181 of 498 transactions in block 26190898. The exact retained evidence
hash is `b8b7c0ec53f30624c96ce598d0911d803941945332627c3bbfea0739f1ae9ae5`.
The demo uses the unchanged sibling tx-position/live-evidence.json; its report
is saved as demo-result.json. This is historical provider evidence, not a claim
about settlement now. The demo pin illustrates retention, not independent custody.

To review your own previously captured position transcript, supply your retained
hash and independently chosen transaction and policy:

```sh
python3 -B line-3/tools/pinned-position/pinned.py --evidence line-3/tools/tx-position/live-evidence.json --sha256 b8b7c0ec53f30624c96ce598d0911d803941945332627c3bbfea0739f1ae9ae5 --tx 0xc4ca304c305cae326cab066639ab2156412eee7f5f774b41a2a136369f817ef7 --confirmations 12
```

Finality is required by default; `--allow-unfinalized` explicitly changes that
policy. The incoming transcript cannot select its own policy, file path or pin.
Retain the original expected hash separately before reviewing a later file.
Do not calculate a replacement expected pin from the incoming evidence and treat
it as approval. Changing the evidence and the expected hash together defeats the
replacement protection. Byte changes including whitespace intentionally reject.
A matching hash still requires valid JSON and a successful semantic replay.

Inputs must be visible workspace-relative regular files, at most 90,000 bytes.
Descriptor-relative opens refuse symlinks in every component, directories, FIFOs,
hidden paths, traversal and absolute paths. The tool hashes and parses the same
bounded bytes without reopening the file. Duplicate JSON keys, nonfinite values,
extra replay reads and policy mismatches reject through the inherited parser and
replay. Reports are capped at 100,000 ASCII bytes. Exit 0 means both checks pass;
exit 1 means evidence mismatch or declined position review; exit 2 means invalid
input. POSIX safe file-open support is required; unsupported systems fail closed.

Tests:

```sh
python3 -B -m unittest discover -s line-3/tools/pinned-position -p 'test_*.py' -v
```

All 18 tests passed, together with all 17 inherited transaction-position tests.
Tests use real retained ZTO evidence and mutations in memory; scratch file tests
write only test/scratch/. They cover byte replacement before parsing, invalid
positions with freshly matching hashes, independent policy, strict JSON,
extra reads, malformed pins, bounds, symlinks, directories, FIFOs, CLI exit codes,
no network and source immutability. No mutation is presented as chain evidence.

A file hash proves no provider identity or Ethereum state. Receipt and block hash
lists remain provider assertions, not cryptographic trie or consensus proofs.
This adds neither freshness nor payment authorization. It never opens a wallet,
reads keys or environment variables, signs, sends, pays, posts or deploys.
