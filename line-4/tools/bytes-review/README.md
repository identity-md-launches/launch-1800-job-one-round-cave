# Offline EIP-712 byte reviewer

Inspect every reachable `bytes` and `bytes1`–`bytes32` value in an EIP-712
request, including domain salt, nested structs and array elements. Shows exact
hex, byte length, zero-byte offsets and the 32-byte encoding word. Dynamic
bytes are hashed; fixed bytes are padded on the right. Input is never changed.
Python standard library only. Copy this whole folder to use it offline.

One working command from the repository root:

```sh
python3 -B line-4/tools/bytes-review/bytes_review.py line-4/tools/bytes-review/zto-payment.json --bytes-expect line-4/tools/bytes-review/zto-bytes.json --digest-expect 0xf33e2506e5c103f98dbfe3feb6d4b87d55f1fad4e423dbaa8462465ff4ab9774
```

Tried: exit **0**, two byte fields, `byteExpectationsMatch: true`,
`digestMatchesExpected: true`, `checksPass: true`. This reproduces the
inherited historical real-ZTO payment commitment, including its transaction
and transcript hashes. ZTO is Ethereum token
`0xd782bdea4ef02a0bd391eb9089470c8080f0a68e`. No fresh chain observation is
claimed. The fixture is evidence, not a request to sign or transfer.

Replace `zto-payment.json` with `zto-substitution.json` in that command:
exit **1**, changed transaction-hash bytes and a changed digest. That fixture
changes only the final byte from `f7` to `f8` to demonstrate rejection; it is
not another chain observation. Saved results are `example-match.json` and
`example-rejection.json`.

For real review, prepare expectations independently of the incoming request:

```json
{"fields":{"/message/payload":{"type":"bytes2","value":"0x1200"}}}
```

This is a format example, not a ZTO policy. Paths refer only to fields in the
parsed typed data. They never select files. Supply all reachable byte fields:
omitted actual paths appear as `unpinnedPaths`; expectations for nonexistent
paths appear as `absentPaths`. Both reject. Exact declared type and exact bytes
must match. Hex digit case is immaterial. `0x`, `0x00`, and trailing zero bytes
are distinct; fixed-byte values must already have exactly their declared width.
The tool never trims or supplies missing bytes. No wildcard, coercion, prefix
match, length-only match or repair is offered.

`--bytes-expect` compares byte fields only. Other values and schema changes,
including declarations behind empty arrays, require the separately obtained
complete `--digest-expect` or the ancestor full-request/pin comparison. Empty
arrays have no byte-valued elements to compare. An empty expectation object
matches only a request with no reachable byte values. The example expectations
and digest were copied from inherited evidence to demonstrate execution, so
they are not independent approval. Keep real expectations separately under
your control; replacing both data and expectations can pass.

Without either expectation option the command is inspection only:
`checksPass: null`, exit **0**. With expectations, exit **0** means all requested
comparisons pass; **1** means at least one differs; **2** means malformed input,
unsafe file, or an exceeded bound. No partial success report is emitted on
exit 2. Matching is never signing approval, ownership, settlement, contract
support or protection against replay. A hash-looking field is uninterpreted
bytes: the reviewer does not authenticate its source or infer its meaning.

The unchanged ancestor encoder is shared implementation, not independent
cryptography. Encoding follows [EIP-712](https://eips.ethereum.org/EIPS/eip-712).
`provenance.json` pins the exact source copies. Nothing signs, sends, dispatches
RPC, accesses wallets, reads environment variables or installs dependencies.

Inputs are regular no-follow files beneath cwd, at most 65,536 bytes, strict
UTF-8 JSON without duplicate keys, floats or nonfinite numbers. Hidden paths,
parent traversal, symlinks and nonregular files reject. POSIX descriptors are
required by the inherited reader. Inherited limits include depth 48, 8,192
nodes, 64 types, 256 fields and eight array dimensions. The entire ASCII JSON
report including its trailing newline is limited to **100,000 bytes**; excess
fails closed. These bounds are not a complete CPU or memory sandbox.

```sh
python3 -B -m unittest discover -s line-4/tools/bytes-review -v
```

Tried: **21 tests pass**, covering all fixed widths, right padding, the known
empty Keccak vector, zero versus empty bytes, exact byte/type expectations,
coverage, nested arrays, domain salt, full-digest matching, invalid inputs,
immutability, output bounds and CLI exits. The detached folder's 21 tests and
CLI also pass, plus 28 ancestor tests in scratch. Actual CLI trials reject
duplicate/null expectations and unsafe paths. Local logs are in
`line-4/check-results-32.json`.
