# Unsaturated Evals in Aug 2025
date: 2025-08-07

I compiled a list of unsaturated evals, they are shown below.

We need more video game evals and improve LLMs performance on them. Solving video games is a great step towards solving robotics and achieving AGI, since simulated environments can be made quite close real world environments.

It will be pretty cool to have an LLM that's good at math, Go, and video games. Currently, no model is simultaneously good at even two of these three.

We also need more synthetic evals, each of which focuses on only one problem and pushes that problem to the limit. For example, [MRCR](https://huggingface.co/datasets/openai/mrcr) reveals the shortcomings of current LLMs on long-context inputs. As another example, LLMs fail to multiply two integers with more than 20 digits, unless they use tools.

Here's a genius idea: evaluate the LLM's ability to create an unsaturated eval. This eval will be unsaturated until there's no more unsaturated evals and AGI is achieved. In order for the model to create an unsaturated eval, it needs to be able to verify the results. There are still many tasks that are easy to verify but hard to do. For example, a task can be to create the code that has the specified UI interactions. The UI interactions are easy to verify but the code is hard to write. As another example, winning at a game is easy to verify but hard to do. This paradigm seems limitless and maybe working on this will help us achieve AGI.

| Category | Benchmark | Leaderboard | Latest Reported Score (Model) |
|----------|------------------|-------------|------------------------------|
| **Knowledge** | [HLE](https://scale.com/leaderboard/humanitys_last_exam) | Yes | 44.4 (Grok 4 Heavy) |
| **Math** | [FrontierMath](https://epoch.ai/frontiermath) | Yes | 24.8 % (gpt5, tiers 1–3) |
|  | [PutnamBench](https://trishullab.github.io/PutnamBench/leaderboard.html) | Yes | 86 / 657 solved |
|  | [Formal Conjectures](https://github.com/google-deepmind/formal-conjectures) | No | — |
| **Image Understanding** | [ZeroBench](https://zerobench.github.io/) | Yes | 5 / 100 (Claude Opus 4.1) |
| **Coding** | [SWE-Lancer IC SWE Diamond](https://openai.com/index/swe-lancer/) | No | \$86 K / \$236 K (o3) |
|  | [LiveCodeBench Pro](https://livecodebenchpro.com/) | Yes | 1791 (o4-mini) |
|  | [Terminal-Bench](https://www.tbench.ai/leaderboard) | Yes | 52 % |
| **Video Understanding** | [LVBench](https://lvbench.github.io/#leaderboard) | Yes | 74.2 % |
| **Puzzles** | [ARC-AGI 2](https://arcprize.org/leaderboard) | Yes | 16 % (Grok 4) |
|  | [EnigmaEval](https://scale.com/leaderboard/enigma_eval) | Yes | 13 % (o3) |
|  | [SimpleBench](https://simple-bench.com/) | Yes | 62.4 % (Gemini 2.5 Pro) |
| **Web Browsing** | [BrowseComp](https://openai.com/index/browsecomp/) | No | 68.9 % (OpenAI Agent) |
| **Long Context** | [MRCR](https://huggingface.co/datasets/openai/mrcr) | Yes ([contextarena](https://contextarena.ai/?needles=8)) | 8 needles at 1M: 27.5 % (Gemini 2.5 Pro), 8 needs at 128K: 40.0% (gpt5) |
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
