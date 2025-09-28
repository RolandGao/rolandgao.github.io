# Finding Unsaturated Evals
date: 2025-08-07

I compiled a list of unsaturated evals, as shown below. I also discuss some ideas about new unsaturated evals after the table.

| Category | Benchmark | Leaderboard | Latest Reported Score (Model) |
|----------|------------------|-------------|------------------------------|
| **Knowledge** | [HLE](https://scale.com/leaderboard/humanitys_last_exam) | Yes | 44.4 (Grok 4 Heavy) |
| **Math** | [FrontierMath](https://epoch.ai/frontiermath) | Yes | 24.8 % (gpt5, tiers 1–3) |
|  | [PutnamBench](https://trishullab.github.io/PutnamBench/leaderboard.html) | Yes | 329 / 657 (Seed-Prover) |
|  | [Formal Conjectures](https://github.com/google-deepmind/formal-conjectures) | No | — |
| **Image Understanding** | [ZeroBench](https://zerobench.github.io/) | Yes | 5 / 100 (Claude Opus 4.1) |
| **Coding** | [SWE-Lancer IC SWE Diamond](https://openai.com/index/swe-lancer/) | No | \$86 K / \$236 K (o3) |
|  | [LiveCodeBench Pro](https://livecodebenchpro.com/) | Yes | 48% (gpt5, medium) |
|  | [Terminal-Bench](https://www.tbench.ai/leaderboard) | Yes | 59 % (Droid) |
|  | [SWE-Bench Pro](https://scale.com/leaderboard/swe_bench_pro_commercial) | Yes | 18% (Claude Opus 4.1) |
| **Video Understanding** | [LVBench](https://lvbench.github.io/#leaderboard) | Yes | 74.2 % |
| **Puzzles** | [ARC-AGI 2](https://arcprize.org/leaderboard) | Yes | 29 % (Grok 4 + scaffolding) |
|  | [EnigmaEval](https://scale.com/leaderboard/enigma_eval) | Yes | 13 % (o3) |
|  | [SimpleBench](https://simple-bench.com/) | Yes | 62.4 % (Gemini 2.5 Pro) |
|  | [TrackingAI offline IQ test](https://www.trackingai.org/home) | Yes | 118 (Claude Opus 4.0) |
| **Web Browsing** | [BrowseComp](https://openai.com/index/browsecomp/) | No | 68.9 % (OpenAI Agent) |
| **Long Context** | [MRCR](https://huggingface.co/datasets/openai/mrcr) | Yes ([contextarena](https://contextarena.ai/?needles=8)) | 8 needles at 1M: 27.5 % (Gemini 2.5 Pro), 8 needs at 128K: 40.0% (gpt5) |
| **Agentic** | [Tau-Bench Airline](https://sierra.ai/blog/benchmarking-ai-agents) | No | 60 % (Claude Sonnet 4) |
| **Multi-turn Dialog** | [MultiChallenge](https://scale.com/leaderboard/multichallenge) | Yes | 63.77 % (o3-pro) |
| **Safety** | [FORTRESS](https://scale.com/leaderboard/fortress) | Yes | Risk 24.76 / Refusal 1.89 % (Claude Opus 4) |
| **Video Games** | [VideoGameBench](https://www.vgbench.com/) | Yes | 0.48 % (Gemini 2.5 Pro) |
| **Multilingual** | [MultiNRC](https://scale.com/leaderboard/multinrc) | Yes | 52% (gpt5) |


We need more video game evals and improve LLMs performance on them. Solving video games is a great step towards solving robotics and achieving AGI, since simulated environments can be made quite close real world environments.

It will be pretty cool to have an LLM that's good at math, Go, and video games. Currently, no model is simultaneously good at even two of these three.

We also need more synthetic evals, each of which focuses on only one problem and pushes that problem to the limit. For example, [MRCR](https://huggingface.co/datasets/openai/mrcr) reveals the shortcomings of current LLMs on long-context inputs. As another example, LLMs fail to multiply two integers with more than 20 digits, unless they use tools.

Here's a genius idea: evaluate the LLM's ability to create an unsaturated eval. This eval will be unsaturated until there's no more unsaturated evals and AGI is achieved. In order for the model to create an unsaturated eval, it needs to be able to verify the results. There are still many tasks that are easy to verify but hard to do. For example, a task can be to create the code that has the specified UI interactions. The UI interactions are easy to verify but the code is hard to write. As another example, winning at a game is easy to verify but hard to do. This paradigm seems limitless and maybe working on this will help us achieve AGI.

One prompt I always try on a new LLM is the following:

```
The following is a list of current Stanford CS PhDs; find where they attended undergrad. Each line in the output should be in the format of "{name} | {school}". Avoid citations so that I can easily copy and paste later. If the school is not found, say "unknown" as the school.

FNU Aditi
Ahmed Ahmed
[47 more names...]
Owen Dugan
```

This prompt sees some success on openai [deep research](https://chatgpt.com/share/6896f95a-0cbc-8011-a2da-ebcfd37566bf), [agent](https://chatgpt.com/share/6896f89f-b458-8011-bdd0-04ad296f5af9), o3, and claude deep research, but all other models fail, including [gpt5](https://chatgpt.com/share/6896f89f-b458-8011-bdd0-04ad296f5af9). [gemini 2.5 pro]((https://g.co/gemini/share/12f90d95a562)) hallucinates. No model does perfectly on this prompt, so there's still room for improvement.

Another prompt I use nowadays:
```
create evals such that top LLMs would fail but grade 6 students would succeed
```
I have not seen a single satisfactory answer by any LLM.

```
LLMs cannot reliably multiply 2 numbers with many digits, but LLMs can solve them with tools. What are some compositional tasks that LLMs cannot solve even with tools? grade 6 students need to be able to do them.
```

find 15 unsaturated evals for the frontier llms that have a public leaderbaord

another prompt:
```
Did egoist sing for guilty crown?
```
failed once: https://chatgpt.com/share/68b62767-16cc-8011-ba35-3d0f353db63a
but succeeded another time: https://chatgpt.com/share/68b62779-9f1c-8011-826f-fe0ad5015b94 

```
compare tesla model y 2024 vs 2025
```
both o3 and gpt 5 thinking didn't mention LR RWD 2024

```
find unsaturated evals for the frontier llms. 
```

```
compare tesla model y 2024 vs 2025
```
should mention that noise reduction is 20%.


```
create an eval that you cannot solve but can verify, and at least 1 human can solve. You and the human can read only text, no image or audio. You and the human both have 5 minutes, and you both have the same resources: a laptop and the internet. you are not constrained by the runtime of your chat environment. The human also has to comply with your safety and content policies. write out the runnable python code that proves you are not able to solve it.
```


```
Write the complete python code for a new LLM eval, where model calls use openai's API. The eval has to satisfy the below constraints
1. gpt-5 fails the eval
2. At least 1 human can succeed on the eval, given the same inputs, time constraint, and compute resources as gpt-5
3. The human also has to comply with gpt-5's safety and content policies
4. The input is text only, no image or audio
```


The following is a list of current Stanford CS PhDs; find where they attended undergrad. Each line in the output should be in the format of "{name} | {school}". Avoid citations so that I can easily copy and paste later. If the school is not found, say "unknown" as the school.

FNU Aditi
Ahmed Ahmed
Samuel Alber
Ali Alkhatib
Daneshvar Amrollahi
Leni Aniva
Aryaman Arora
Simran Arora
Luke Bailey
Neil Band
Andy Bartolo
Michael Dawit Bereket
Keller Blackwell
Guy Blanc
Beleicia Bullock
Steven Cao
Eric Chan
Keshigeyan Chandrasegaran
Francois Chaubard
Liangyu Chen

FNU Aditi | Indian Institute of Technology Delhi
Ahmed Ahmed | Stanford University
Samuel Alber | University of California, Berkeley
Ali Alkhatib | University of California, Irvine
Daneshvar Amrollahi | unknown
Leni Aniva | University of Waterloo
Aryaman Arora | Georgetown University
Simran Arora | University of Pennsylvania
Luke Bailey | Harvard University
Neil Band | Harvard College
Andy Bartolo | unknown
Michael Dawit Bereket | Stanford University
Keller Blackwell | University of South Florida
Guy Blanc | Stanford University
Beleicia Bullock | Bowdoin College
Steven Cao | University of California, Berkeley
Eric Chan | Yale University
Keshigeyan Chandrasegaran | Singapore University of Technology and Design
Francois Chaubard | University of Delaware
Liangyu Chen | Nanyang Technological University

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
