# GoPlay weights

These 38 checkpoints serve the 50 opponents approved in
[`data/goplay_catalog.json`](../../data/goplay_catalog.json). Temperature variants
share their base checkpoint. Each compressed file is below 100,000,000 bytes.

GoPlay downloads these files from this repository's `main` branch through
`raw.githubusercontent.com`, with browser caching disabled. Keep weights outside
`public/` so Next.js does not copy them into the Cloudflare static deployment.
Push the weights to GitHub before deploying a catalog that references them.

The catalog records each original KataGo download URL, exact byte count, and
SHA-256 checksum. Preserve the original `.txt.gz` or `.bin.gz` extension; the
runtime needs the appropriate model format.

Licenses and attribution: [third-party notices](../../public/goplay/THIRD_PARTY_NOTICES.txt).

Verification:

```sh
node scripts/generate-goplay-opponents.js
node scripts/check-goplay-networks.cjs
```

To check one model, pass its checkpoint name as an argument to the second command.
