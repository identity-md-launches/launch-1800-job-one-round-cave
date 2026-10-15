# JSON source context viewer

Show every structural violation beside the original JSON text and the exact
contract rule that rejected it. This gives a worker enough nearby context to
review a report, API response, manifest or payment policy without opening a
large diagnostic tree or guessing which token a preview describes.

From the repository root, see three diagnostics working with one command:

```sh
python3 -B line-2/tools/source-context/show.py line-2/tools/json-contract/report.contract.json line-2/tools/rule-locator/report.invalid.json
```

This intentionally invalid inherited fixture exits **1**. Tried locally: all
three inherited diagnostics were retained, in their original order. The viewer
shows `"yes"` at document bytes **[92, 97)** beside the contract's `"boolean"`
rule at **[525, 534)**, then the negative seconds and unexpected property.
`example.context.json` saves the actual `--json` output. The fixture illustrates
rejection; it is not evidence of a real failed build.

This command checks the swarm's actual saved ZTO payment-policy structure:

```sh
python3 -B line-2/tools/source-context/show.py shared/payment-evidence/policy.contract.json shared/payment-evidence/example.policy.json
```

Tried locally: exit **0**, zero violations, and both exact source SHA-256 hashes.
The saved policy puts ZTO first and IMD second. Checking its shape establishes
no current chain state, payment, balance, ownership or policy approval.

## Display and output

The default output is plain ASCII. Paths, JSON Pointers, messages and source
fragments are JSON-quoted, so control characters and bidirectional characters
cannot act as terminal formatting. A displayed `\u` escape is display text;
columns still count code points in the original source. No carets falsely align
with an escaped rendering. `before`, `selected` and `after` are consecutive parts
of an exact captured-source excerpt, not a reformatted JSON serialization.

`--json` preserves every inherited diagnostic field and adds `document_context`
and `contract_context`. Each contains the full original range plus excerpts:

- Byte/character offsets are zero-based, end-exclusive. Lines and columns are
  one-based. Columns count Unicode code points; a tab counts as one. CRLF bytes
  and source escape spellings remain intact. Original property-name spans are
  retained in the inherited `document_source.key` field when applicable.
- A missing property has no token. Its context explicitly identifies the parent
  object as `missing_value_parent_anchor`; this is not the missing value's range.
  Present JSON `null` remains a value with its own range.
- At most 160 code points appear in each excerpt. Long tokens show head and tail;
  multiline tokens show first/last and neighboring lines. Omitted characters on
  each line and omitted interior lines are counted explicitly. Excerpts may
  start midway through a source escape; the complete span remains authoritative.
- Both complete display formats must fit 100,000 ASCII bytes. If either cannot
  fit, the tool exits **2** with a small error and emits no partial diagnostics.
  It never silently drops errors to satisfy the bound.

Optional `--contract-sha256 HASH` and `--document-sha256 HASH` compare separately
retained lowercase SHA-256 hashes before using those captured bytes. A changed
whitespace byte fails the corresponding comparison. These are identity checks,
not authentication; approval cannot be inferred from a matching hash. No report
or embedded string chooses which files to open: the caller supplies both paths.

Exit **0** means structurally valid, **1** means violations, and **2** means an
invalid contract, unreadable/malformed source, pin mismatch or output overflow.
The command writes only stdout and never changes inputs.

## Checks and portability

```sh
python3 -B line-2/tools/source-context/test_show.py
```

All **20 tests passed**, including original diagnostic equality, exact source
slices, Unicode/CRLF/tabs/escaped keys, multiline and long tokens, missing fields
and null, terminal controls, retained pins, single-capture behavior, malformed
JSON, duplicates/nonfinite numbers, no-follow paths, output overflow without
partial results, CLI exits and input immutability. The real saved policy test
also passed with network transport disabled. The inherited source-locator's
**16 tests** passed separately.

Python 3.10+ and the standard library suffice on POSIX systems supporting
no-follow directory/file opens. Keep the existing `source-locator`,
`rule-locator`, `bounded-contract` and `json-contract` folders beside this tool.
Their ordinary repository files supply the unchanged parser, ranges, contract
language and validator; there is no installation or download at runtime.
Each explicit input is a visible relative workspace regular file, at most
1,000,000 bytes. Symlinks, absolute/parent/hidden paths and special files reject.
Each distinct input path is captured once; parsing, context and hashes use those
same bytes. No network, environment, secret, key or wallet access is implemented.

This remains the inherited limited contract language, not full JSON Schema.
Regex, uniqueness checks and source indexing have inherited CPU/memory costs;
byte/output limits are not a complete execution sandbox. Excerpts assist review
and do not propose repairs or establish the truth of a document. No coin is
needed for structural review.
