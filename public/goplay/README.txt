GoPlay runtime assets

- kataeval.js and kataeval.wasm were built from saigo-online/katago-webgpu commit
  d5ad1c0423dba989c60a2f06b1848e7eec2b5941 with Emscripten 6.0.8. This is a
  single-threaded, CPU-only build: the WebGPU sources are excluded, and Eigen
  3.4.0 is compiled with EIGEN_MPL2_ONLY.
- Weights live in the repository's networks/goplay/ directory, outside public/.
  GoPlay downloads them directly from raw.githubusercontent.com with
  cache: 'no-store'; they are not included in the Cloudflare static deployment.
- data/goplay_catalog.json defines the approved 50 opponents and their 38
  shared checkpoints, including text and binary network files up to 100 MB.
  Temperature aliases reuse their base checkpoint. The original files come
  from https://katagotraining.org/networks/. See THIRD_PARTY_NOTICES.txt.
- scripts/generate-goplay-opponents.js generates the public catalog from the
  approved selection and current GoBench ratings, validating the file sizes
  and minimum 50-Elo gaps (with an exception permitted for the top opponent).
- Run node scripts/check-goplay-networks.cjs to verify all network hashes and
  load and evaluate every network through the actual GoPlay worker and WASM
  engine in Node. No browser download cache is used.
- GoPlay forces CPU execution and rejects any request where numVisits is not 1.
- THIRD_PARTY_NOTICES.txt consolidates all notices for code and weights shipped
  here; it is not loaded by the GoPlay application.
