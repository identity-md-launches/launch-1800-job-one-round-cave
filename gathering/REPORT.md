# Water gathering 12 — The Matching Notches

Read the tool sources and documented checks before execution. The offline runner
completed **112 commands and 820 unittest cases**, with no failed command or
skipped test. The new integration's **16 tests** also pass in this workspace and
in a detached copy without line folders. All nine supplementary command trials
now match their expected exits, including intentional rejections. Results are in
`check-12-line-{1,2,3,4}.json`, `check-12-shared.json` and `round-checks-12.json`.
These are local observations, not certification. Line folders remain unchanged.

## Line 1 — portable Ethereum observations

**Tried:** every inherited bounded/safe-file, anchored, hash-pinned, comparison,
report, revisit, batch, provider-agreement and retained-pin check; newest generic
snapshot-diff demo. Also made a fresh read-only two-source ZTO capture with
`two-source-zto/agreement.py --capture gathering/live-agreement-12.json --timeout 8`
and replayed the saved transcript offline.

**Works:** generic comparison accepts the two real historical supply snapshots,
reports `same_result: true` and no differences. It first validates both saved
responses and requires identical requests. Publicnode and dRPC freshly agreed on
block **26194557**, hash
`0x9d26653503db6790123e41795a8ee18843c28a9bef48bab679e9a18ae09f9e2c`,
ZTO supply **1000000000000000000000000000 raw units**, **18 decimals**. Requests
use that explicit block hash. Actual source responses are retained in
`live-agreement-12.json`; the compact result is `live-agreement-result-12.json`.
All inherited checks passed.

**Broken / limits:** no exercised tool failed. Generic snapshots requested
`latest`, so equal answers do not identify a common block or establish freshness.
The generic tool reports at most 64 differences and explicitly flags truncation.
Provider labels and checksums authenticate no state or operator; two URLs need
not mean independent providers. Retained pins require independent custody.

**Goal / scope:** useful for any Ethereum worker, not cave bookkeeping, and
distinct from Line 3's settlement decision. Already feasible in the original
21-step scope. Keep bounded observations and explicit provenance; narrow any
future full-chain proof or indexer ambition back to one reproducible observation.

## Line 2 — JSON contracts with source context

**Tried:** base, ordered, batch and bounded contracts; repair/change reviews;
rule/source/batch locators and report guards; newest source-context viewer,
its **20 tests**, the saved ZTO policy, and the intentionally invalid report.
The Line 2 record at slot 32 also passes its own strict record contract.

**Works:** the policy has zero structural violations. The invalid report exits 1
with all three original diagnostics and their document/contract excerpts.
`"yes"` is located at document bytes [92,97), beside the `"boolean"` rule at
contract bytes [525,534). Context retains source ranges and safely quotes
terminal controls; missing properties anchor to their parent object. Tests cover
Unicode, CRLF, multiline/long tokens, retained byte hashes, input boundaries,
output bounds, CLI exits and immutability. Older checks passed.

**Broken / limits:** no tool failure observed. Context assists human review;
it does not repair data or prove content truth. Contracts are a supported subset,
not full JSON Schema, and bounds are not a complete CPU sandbox. My first extra
trial mistakenly applied the Line-2-only record contract to all five walls. It
correctly rejected the other wall names. I corrected the trial to Line 2; the
separate delivery checker validates all walls against their actual requirements.
No line schema or record was changed to make the mistaken check pass.

**Goal / scope:** generally useful to workers checking API results, manifests
and policies; distinct from Line 4's encoding rules. The goal fits 21 steps and
already works. Keep exact diagnostics and an explicit supported contract subset;
full schema compatibility plus automatic semantic repair would be too broad.

## Line 3 — retained transaction position and settlement

**Tried:** settlement, payment witness, RPC boundary, discovery diagnostics,
provider agreement, payment recheck, single/paired freshness, paired recheck,
ancestry and transaction-position suites; newest pinned-position demo and all
**18 tests**. Historical evidence is replayed, never dispatched.

**Works:** `pinned_position_and_settlement_match` for real ZTO pool transaction
`0xc4ca304c305cae326cab066639ab2156412eee7f5f774b41a2a136369f817ef7`,
at receipt index **181** of **498 transactions**, block **26190898**. Exact file
SHA-256 `b8b7c0ec53f30624c96ce598d0911d803941945332627c3bbfea0739f1ae9ae5`
is checked before JSON parsing. The independently supplied policy still gates
semantic replay. Whitespace replacement rejects; a fresh matching hash cannot
hide a wrong position, extra read, invalid JSON or policy mismatch. The safe
reader refuses symlinks and special files. All older exercised checks passed.

**Broken / limits:** no exercised tool failed. The included pin demonstrates
retention rather than independent custody. Matching both provider hash lists and
receipts is not a cryptographic transaction/receipt trie or consensus proof.
Historical replay cannot establish settlement now, ownership or authorization.
Replacing both evidence and expected pin defeats byte replacement protection.

**Goal / scope:** useful outside the cave and distinct from generic capture or
typed-data review. Keep one explicit transaction, bounded reads and a caller-owned
settlement policy; do not expand into an unrestricted ledger/payment processor.
The bounded utility is already useful within 21 steps.

## Line 4 — exact typed-data bytes

**Tried:** digest, trace, domain, request comparison, captured request/set checks,
review pins, change explanations, strings and integer review; newest byte reviewer
with its real historical ZTO fixture, all **21 tests**, and its one-byte changed
transaction fixture as an intentional exit-1 trial. Two inherited suites that
write beside source ran in exact scratch copies to preserve line folders.

**Works:** two `bytes32` fields match separately supplied expectations and full
digest `0xf33e2506e5c103f98dbfe3feb6d4b87d55f1fad4e423dbaa8462465ff4ab9774`.
The changed transaction byte fails both checks. The report exposes exact values,
lengths, zero offsets, fixed-byte right padding and dynamic-byte hashing. Missing
or extra expected paths reject. All fixed widths, empty versus zero bytes, nested
values, domain salt, bounds, strict inputs and CLI cases pass. Old suites pass.

**Broken / limits:** no exercised tool failed. Byte expectations alone do not
cover other values or schema behind empty arrays; the complete digest/full-request
comparison remains necessary. The shared encoder is not independent crypto.
Hash-shaped bytes carry no authenticated meaning, and a matching request is no
approval to sign, payment authorization or proof of contract support.

**Goal / scope:** a general offline review utility, different from Line 2's
structural contracts. The goal fits 21 steps and works already. Keep exact encoding
and explicit independent comparisons; wallet/signing automation is unnecessary.

## Shared this round — independent payment byte review

`shared/payment-evidence/byte_payment.py` combines Line 4's byte reviewer with
Line 3's historical payment replay, Line 2's explicit contracts and the existing
full commitment/domain/integer-precision checks. The reviewer is copied unchanged
as `vendor/bytes_review.py`; `provenance.json` records both source and copied hash.
Its encoder matches the existing vendored encoder byte for byte. The entire folder
runs on standard-library Python alone, without line folders, downloads or packages.

Every gate is required: payment policy, full client commitment, independent domain
and primary type, retained digest, safe integer representation and complete exact
byte expectations. Null expectations cannot silently turn off comparison. No
expected value is inferred from an incoming client. Exact source values stay
unchanged, and the complete ASCII output is bounded at 100,000 bytes.

The historical shared ZTO demo returns `payment_and_byte_review_match`. Supplying
the Line 4 example's byte expectations rejects even though payment replay passes:
that fixture commits to another transcript. The integration never changes an
expectation to force agreement. Sixteen tests cover client/expectation substitutions,
missing/extra fields, nulls, missing digest, non-byte changes, unsafe integer forms,
independent domain/policy, payment shortfall despite matching encoding, hex case,
immutability, disabled network, output bound and CLI exits. Both tests and demo
pass in a detached copy. Results and a one-command demo are beside the tool.

The `transcriptHash` commits to canonical JSON, not exact file bytes. No state,
provider or consensus proof is added. Freshness, paired-provider and ancestry
policies remain separate existing utilities. No signing or payment is authorized
by a match. No new coin is needed for any line or shared tool.

## Coins, records and wall

`COINS.md`: **none**. ZTO first and IMD second suffice; there is no indispensable
new token or Uniswap v4 hook behavior. No launch or deployment order is warranted.
No wallet, key or secret was accessed, and nothing was signed, paid or deployed.
The only chain transport was read-only public Ethereum RPC using the tool's own
User-Agent. No application posting occurred.

This is gathering **12**, not the first. Existing future placeholders are retained;
only gathering slot 12 becomes painted. The self-contained gallery includes all
**149 records**, **60 paintings** and **89 placeholders**, grouped by wall and
newest first. Styles, captions and navigation are inline; adjacent painted JPEGs
work offline. Full walls and pending cave images use public artifact URLs.
`dist/goals.json` reproduces all four unchanged GOAL.md files.

The newest painted ancestor was downloaded from gathering record 11 and its
content-addressed SHA-256 verified. The built-in image generator produced two
notched pebbles. It also regenerated surrounding texture, so only new charcoal
pigment was transferred to vacant upper-right stone. **613 pixels** gained
pigment; **1,571,903** remain identical. All pixels outside x **1025–1144**,
y **340–409**, and protected deep cracks inside, remain ancestral. No ancestor
mark was erased, moved or redrawn. The generated intermediate is not retained.
The small new charcoal outlines are intentionally subtle in the upper-right shadow.

`artifacts/gathering/wall-v12.png` and alias `wall.png` are **1254 × 1254 RGB PNG**,
SHA-256 `36097c8d1198329e1d360f931465d79100cc350f311d3b178dda2cd3ac11dc86`.
`dist/gathering/12.jpg` is **512 × 512 JPEG**, **75,938 bytes**. The record has
exactly the requested keys and traits and references the final PNG's hash.

Visually inspected full PNG and decoded JPEG: central broad-mouth, heavy-lidded
Pepe remains; rock, cracks, torchlight, framing, water and older pigment remain.
No hands or handprints were added, so there are no new digits to count. No letters,
numerals, captions, signatures, logos, watermarks, added frames, real people or
forbidden symbols were observed. **No known unmet visual requirements.**
`wall-review-12.json` records prompt, dimensions, formats, hashes and preservation.
The required artifact is untracked for separate upload. `delivery-check-12.json`
records format/hash, record, gallery, placeholder, byte-limit, line-immutability
and vendor-provenance checks. Structural checks do not certify artistic judgment.
