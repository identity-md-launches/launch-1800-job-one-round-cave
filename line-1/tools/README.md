# RPC snapshot

This tool gives a worker one portable, offline-readable record of a live Ethereum JSON-RPC response. The compatibility command `rpc_snapshot.py` now uses the bounded public-read implementation in `bounded-rpc-snapshot/`. It stores the endpoint, request method and parameters, HTTP metadata, and the parsed response. It never uses a wallet, reads secrets, signs, or sends a transaction.

I tried the updated tool against Ethereum’s public JSON-RPC endpoint with ZTO `totalSupply()`; it returned a successful JSON-RPC response and wrote a snapshot. An offline verification of that saved response passed. Network access is required for capture, but the result can be checked offline.

Run it:

```sh
python3 -B line-1/tools/rpc_snapshot.py --preset zto-supply --output test/scratch/zto-supply.json
```

The output is ordinary JSON and can be opened later without the network. See `bounded-rpc-snapshot/README.md` for the offline demonstration and limits.

For two hash-pinned ZTO state reads sent in one JSON-RPC batch and correlated by
response ID, see `batched-zto-snapshot/README.md`. It includes a real public-read
transcript and one offline verification command.

To check whether a saved hash-pinned ZTO block is still reported with the same hash and values, see `revisit-zto-snapshot/README.md`. It includes a real public-read transcript and an offline verification command.

To check whether two public RPC endpoints report the same ZTO supply and decimals at one block hash, see `two-source-zto/README.md`. It includes both real response transcripts and an offline verification command.

For a finalized-block ZTO supply bundle, see `anchored-zto-snapshot/README.md`. It ties a public read to a block number and hash, then rechecks the block before saving four responses together.

For a general offline comparison of two bounded JSON-RPC snapshots with the same request, see `generic-snapshot-diff/README.md`.
