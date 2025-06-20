---
title: "Browsing Evals"
date: 2025-06-19
# weight: 1
tags: ["ML"]
draft: true
---

I'm browsing some evals today. And what better way to do it than ask o3 to gather all the data for me.

conversation: https://chatgpt.com/share/6854f927-5a04-8011-98e5-0d94030ca71d


<!-- ![name](eval_results.png) -->


<style>
table {
  font-size: 12px;
}
table th,
table td {
  /* padding: 0 !important; */
  min-width: 0px !important;
}
</style>
| Model                           | LiveBench | HLE (Text-only) | MASK | MultiChallenge | Aider Polyglot | Vista | Aggregate (no Vista) | Aggregate (with Vista) |
| ------------------------------- | --------- | --------------- | ---- | -------------- | -------------- | ----- | -------------------- | ---------------------- |
| **o3 (high)**                   | 0.75      | 0.21            | 0.84 | 0.59           | 0.83           | 0.50  | **0.64**             | **0.62**               |
| **Claude Opus 4 (thinking)**    | 0.73      | 0.11            | 0.88 | 0.54           | 0.71           | 0.47  | **0.59**             | **0.57**               |
| **Gemini 2.5 Pro (prev-06-05)** | 0.71      | 0.22            | 0.56 | 0.52           | 0.83           | 0.55  | **0.57**             | **0.56**               |
| **DeepSeek R1 (05-28)**         | 0.65      | 0.14            | 0.57 | 0.45           | 0.71           | —     | **0.50**             | 0.42                   |
| **Qwen3-235B-A22B**             | 0.65      | 0.12            | 0.56 | 0.41           | 0.60           | —     | **0.47**             | 0.39                   |
| **DeepSeek V3 (03-24)**         | 0.56      | 0.05            | 0.45 | 0.32           | 0.55           | —     | **0.38**             | 0.32                   |
| **GPT-4o (Nov-24)**             | 0.47      | 0.02            | 0.60 | 0.28           | 0.18           | 0.35  | **0.31**             | 0.32                   |
| **Llama 4 Maverick (17B)**      | 0.48      | 0.05            | 0.50 | 0.32           | 0.16           | 0.38  | **0.30**             | 0.31                   |
