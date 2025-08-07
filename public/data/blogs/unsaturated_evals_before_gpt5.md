# Unsaturated Evals before GPT5
date: 2025-08-07

I compiled a list of unsaturated evals prior to GPT5's launch. Can't wait to see how GPT5 performs on these. 

| Category | Benchmark | Leaderboard | Latest Reported Score (Model) |
|----------|------------------|-------------|------------------------------|
| **Knowledge** | [HLE](https://agi.safe.ai/) | Yes | 44.4 (Grok 4 Heavy) |
| **Math** | [FrontierMath](https://epoch.ai/frontiermath) | Yes | 20 % (tiers 1–3) |
|  | [PutnamBench](https://trishullab.github.io/PutnamBench/leaderboard.html) | Yes | 86 / 657 solved |
|  | [Formal Conjectures](https://github.com/google-deepmind/formal-conjectures) | No | — |
| **Image Understanding** | [ZeroBench](https://zerobench.github.io/) | Yes | 4 / 100 (o3) |
| **Coding** | [SWE-Lancer IC SWE Diamond](https://openai.com/index/swe-lancer/) | No | \$86 K / \$236 K (o3) |
|  | [CodeForces](https://codeforces.com/) | Yes ([ratings](https://livecodebenchpro.com/)) | 2706 / 3820 rating (o3) |
|  | [Terminal-Bench](https://www.tbench.ai/leaderboard) | Yes | 52 % |
| **Video Understanding** | [LVBench](https://lvbench.github.io/#leaderboard) | Yes | 74.2 % (top model) |
| **Puzzles** | [ARC-AGI 2](https://arcprize.org/leaderboard) | Yes | 16 % (Grok 4) |
|  | [EnigmaEval](https://scale.com/leaderboard/enigma_eval) | Yes | 13 % (o3) |
|  | [SimpleBench](https://simple-bench.com/) | Yes | 62.4 % (Gemini 2.5 Pro) |
| **Web Browsing** | [BrowseComp](https://openai.com/index/browsecomp/) | No | 68.9 % (OpenAI Agent) |
| **Long Context** | [MRCR](https://huggingface.co/datasets/openai/mrcr) | Yes ([contextarena](https://contextarena.ai/?needles=8)) | 23 % (Gemini 2.5 Pro, 8 needles / 1 M) |
| **Agentic** | [Tau-Bench Airline](https://sierra.ai/blog/benchmarking-ai-agents) | No | 60 % (Claude Sonnet 4) |
| **Multi-turn Dialog** | [MultiChallenge](https://scale.com/leaderboard/multichallenge) | Yes | 63.77 % (o3-pro) |
| **Safety** | [FORTRESS](https://scale.com/leaderboard/fortress) | Yes | Risk 24.76 / Refusal 1.89 % (Claude Opus 4) |
| **Video Games** | [VideoGameBench](https://www.vgbench.com/) | Yes | 0.48 % (Gemini 2.5 Pro) |
|  | [Game Arena](https://www.kaggle.com/game-arena) | Coming soon | — |
| **Multilingual** | [MultiNRC](https://scale.com/leaderboard/multinrc) | Yes | 49 % (o3-pro) |



<!-- conversation: https://chatgpt.com/share/6854f927-5a04-8011-98e5-0d94030ca71d -->


<!-- <style>
table {
  font-size: 12px;
}
table th,
table td {
  /* padding: 0 !important; */
  min-width: 0px !important;
}
</style> -->
<!-- | Model                           | LiveBench | HLE (Text-only) | MASK | MultiChallenge | Aider Polyglot | Vista | Aggregate (no Vista) | Aggregate (with Vista) |
| ------------------------------- | --------- | --------------- | ---- | -------------- | -------------- | ----- | -------------------- | ---------------------- |
| **o3 (high)**                   | 0.75      | 0.21            | 0.84 | 0.59           | 0.83           | 0.50  | **0.64**             | **0.62**               |
| **Claude Opus 4 (thinking)**    | 0.73      | 0.11            | 0.88 | 0.54           | 0.71           | 0.47  | **0.59**             | **0.57**               |
| **Gemini 2.5 Pro (prev-06-05)** | 0.71      | 0.22            | 0.56 | 0.52           | 0.83           | 0.55  | **0.57**             | **0.56**               |
| **DeepSeek R1 (05-28)**         | 0.65      | 0.14            | 0.57 | 0.45           | 0.71           | —     | **0.50**             | 0.42                   |
| **Qwen3-235B-A22B**             | 0.65      | 0.12            | 0.56 | 0.41           | 0.60           | —     | **0.47**             | 0.39                   |
| **DeepSeek V3 (03-24)**         | 0.56      | 0.05            | 0.45 | 0.32           | 0.55           | —     | **0.38**             | 0.32                   |
| **GPT-4o (Nov-24)**             | 0.47      | 0.02            | 0.60 | 0.28           | 0.18           | 0.35  | **0.31**             | 0.32                   |
| **Llama 4 Maverick (17B)**      | 0.48      | 0.05            | 0.50 | 0.32           | 0.16           | 0.38  | **0.30**             | 0.31                   | -->
