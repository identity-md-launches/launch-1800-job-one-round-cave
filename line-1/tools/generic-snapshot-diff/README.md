# Generic snapshot diff

Compare the `result` of two saved, bounded Ethereum JSON-RPC responses offline. The tool first replays the inherited snapshot validation: public-read request shape, successful response envelope, and stored response checksum. It refuses different requests. It permits different provider labels so a worker can compare two observations of the same question; it does not claim the providers are independent or the answers are true. Differences use escaped JSON Pointer paths and short value previews. At most 64 differences are printed, and `changes_truncated` says when more exist. Input stays within the inherited no-follow workspace file boundary.

One command from the repository root shows it working without network:

```sh
python3 -B line-1/tools/generic-snapshot-diff/diff.py line-1/tools/bounded-rpc-snapshot/sample-zto-supply.json line-1/tools/generic-snapshot-diff/live-zto-supply.json
```

I ran that command after capturing `live-zto-supply.json` from Ethereum Publicnode on 2026-10-15 using the existing bounded `--preset zto-supply` reader. Both historical observations asked for the real ZTO contract's `totalSupply()` at `latest`; both returned the same raw result, so `same_result` was `true` and `changes` was empty. They are saved provider responses, not proof of current supply. The request's `latest` tag gives neither capture a shared block identity; equal answers could come from different blocks. The timestamps are untrusted source metadata.

To compare your own snapshots, capture them with `bounded-rpc-snapshot/snapshot.py` and pass their two workspace-relative paths in place of the example paths. Each input can be up to the inherited bounded-snapshot limit (2,016,384 bytes). The JSON report is limited to 100,000 bytes. The tool uses Python's standard library and the existing sibling `bounded-rpc-snapshot` and `safe-snapshot-files` source files. It reads no wallet or secret and makes no network call, payment, signature, or transaction.

This is a structural comparison of provider claims. It does not establish Ethereum state, chain ancestry, provider authenticity, or freshness. If the two requests use a moving tag such as `latest`, any difference is a difference between returned responses, not a measured change at known block heights. For ZTO supply comparisons at explicit block hashes, use the sibling `compare-zto-snapshots` tool.
