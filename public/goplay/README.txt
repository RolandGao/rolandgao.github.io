GoPlay runtime assets

- kataeval.js and kataeval.wasm were built from saigo-online/katago-webgpu commit
  d5ad1c0423dba989c60a2f06b1848e7eec2b5941 with Emscripten 6.0.8. This is a
  single-threaded, CPU-only build: the WebGPU sources are excluded, and Eigen
  3.4.0 is compiled with EIGEN_MPL2_ONLY.
- networks/ contains only the base kata1-b6c96 checkpoints used by the
  post-filter GoPlay opponent catalog. Temperature aliases reuse their base
  checkpoint. The original files come from https://katagotraining.org/networks/.
  See THIRD_PARTY_NOTICES.txt.
- GoPlay forces CPU execution and rejects any request where numVisits is not 1.
- THIRD_PARTY_NOTICES.txt consolidates all notices for code and weights shipped
  here; it is not loaded by the GoPlay application.
