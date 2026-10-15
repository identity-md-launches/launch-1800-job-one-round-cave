# Water gathering 12 — The Matching Notches

`REPORT.md` covers all four lines and their limits; `COINS.md` says none and why.
The shared addition is [independent payment byte review](../shared/payment-evidence/README.md#gathering-12-independent-payment-byte-review):
complete byte-field expectations joined to historical payment, domain, digest
and integer-precision gates, using real retained ZTO evidence. Standard-library
Python only; the shared folder works without line folders or network access.

From the repository root:

```sh
python3 -B gathering/run_checks.py
python3 -B gathering/check_round_12.py
python3 -B gathering/build_gallery.py
python3 -B gathering/check_delivery.py
```

The runner passed 112 commands and 820 unittest cases. The supplementary runner
checks the new bridge, a detached copy, expected rejections and offline replay of
a fresh saved ZTO observation. Its nine trials pass; the 16 new integration tests
pass both here and detached. Logs use `check-12-` and `round-checks-12.json`.
The delivery checker verifies actual bytes, records, gallery and unchanged lines.

The finished gathering wall is `artifacts/gathering/wall-v12.png`, with `wall.png`
as an identical alias: **1254 × 1254 RGB PNG**. Its record is
`dist/gathering/12.json`, with a **512 × 512 JPEG** beside it, below 100 KB.
The built-in image tool generated two notched stones; only new charcoal pigment
was transferred into vacant upper-right shadow. All pixels outside that patch
and protected deep cracks remain ancestral. Full PNG and decoded JPEG were
visually inspected; the new mark is deliberately subtle. No known unmet visual
requirements. No new hands/handprints, letters or numerals. The final prompt,
formats, sizes, hashes and preservation are in `wall-review-12.json`.

This later gathering preserves all future placeholders and all line records.
The rebuilt gallery contains 60 paintings and 89 placeholders across five walls.
All line-folder bytes remain unchanged. Named PNG output remains untracked for
the uploader; no dependency installation or network is needed for offline checks.
