I have compiled a list of unsaturated evals, most of which have up-to-date public leaderboards. Then I created some hard prompts for independent testing. Finally, I discuss the need for more video game and web browsing evals.

## Unsaturated evals

| Category     | Benchmark                                                                                      |        Score | Best model                         |
| ------------ | ---------------------------------------------------------------------------------------------- | -----------: | ---------------------------------- |
| Coding       | [Terminal-Bench 2.0](https://www.tbench.ai/leaderboard/terminal-bench/2.0)                     |          75% | GPT-5.3-Codex  |
| Coding       | [SWE-Bench Pro (Public)](https://scale.com/leaderboard/swe_bench_pro_public)           |          57% | GPT-5.3-Codex                     |
| Coding       | [Vibe Code Bench](https://www.vals.ai/benchmarks/vibe-code)                                    |          41% | GPT-5.2                            |
| Puzzles      | [SimpleBench](https://simple-bench.com/)                                                       |          76% | Gemini 3 Pro                       |
| Mathematics  | [FrontierMath](https://epoch.ai/frontiermath)                                                  |          41% | GPT-5.2 & Claude Opus 4.6              |
| General      | [Arena.ai Leaderboard](https://arena.ai/leaderboard)                                           |     1.5k Elo | Claude Opus 4.6         |
| Vision       | [ZeroBench](https://zerobench.github.io/)                                                      | 19%          | Gemini 3 Pro                       |
| Knowledge    | [Humanity's Last Exam](https://scale.com/leaderboard/humanitys_last_exam)                      |          53% | Gemini 3 Deep Think                |
| Agentic      | [Remote Labor Index](https://scale.com/leaderboard/rli)                                        |         3.8% | Claude Opus 4.5         |
| Agentic      | [Vending-Bench 2](https://andonlabs.com/evals/vending-bench-2)                                 |   8.0k / 63k | Claude Opus 4.6                    |
| Agentic | [GDPval](https://evals.openai.com/gdpval/leaderboard) | 50% | GPT-5.2 |
| Long context | [MRCR (1M, 8 needles)](https://contextarena.ai/?needles=8) | 76% | Claude Opus 4.6 |

## Recently saturated evals

| Category     | Benchmark                                                                                      |        Score | Best model                         |
| ------------ | ---------------------------------------------------------------------------------------------- | -----------: | ---------------------------------- |
| Mathematics | [PutnamBench](https://trishullab.github.io/PutnamBench/leaderboard.html) | 668 / 672 | Aleph Prover (Logical Intelligence) |
| Web Browsing | [BrowseComp](https://openai.com/index/browsecomp/) | 84% | Claude Opus 4.6 |
| Puzzles | [ARC-AGI 2](https://arcprize.org/leaderboard) | 85% | Gemini 3 Deep Think |

<!-- honorable mentions

| Science      | [SciPredict](https://scale.com/leaderboard/scipredict)                                         |          25% | Gemini 3 Pro Preview               |
| Puzzles      | [EnigmaEval](https://scale.com/leaderboard/enigma_eval)                                        |          19% | GPT-5 Pro (2025-10-06)             |
| Vision       | [VisualToolBench](https://scale.com/leaderboard/vtb)                                           |          27% | Gemini 3 Pro               |
| Coding        | [Roblox Open Game Eval](https://github.com/Roblox/open-game-eval/blob/main/LLM_LEADERBOARD.md) | 55% (pass@1) | Gemini 3 Flash                     |

Formal Conjectures: https://github.com/google-deepmind/formal-conjectures, no leaderboard
iq test: https://www.trackingai.org/home
-->


## Independent testing

The results of my independent testing are shown below. Then, I describe each question in more detail.

Grok4.1 does surprisingly well, given its absence in many public benchmarks.


| Model             |   Q1 |    Q2 |     Q3 |        Q4 |  Q5 |        Q6 |  Avg (excl. Q6) |
| ----------------- | ---: | ----: | -----: | --------: | --: | --------: | -------: |
|    Topic    |  Web |   Web | Health | Education |  IQ | Usability | --- |
| Claude Opus 4.6   | 6/10 | 10/12 |  7.5/9 |       1/1 | 0/1 |       0/1 |      65% |
| Grok 4.1          | 8/10 |  9/12 |    4/9 |       1/1 | 0/1 |       1/1 |      60% |
| Gemini 3 Pro      | 7/10 |  8/12 |    5/9 |       1/1 | 0/1 |       0/1 |      58% |
| Claude Sonnet 4.5 | 4/10 |  4/12 |  6.5/9 |       1/1 | 0/1 |       0/1 |      49% |
| GPT-5.2           | 9/10 |  8/12 |    7/9 |       0/1 | 0/1 |       1/1 |      47% |
| Kimi K2.5         | 7/10 |  6/12 |    6/9 |       0/1 | 0/1 |       1/1 |      37% |
| Qwen3-Max         | 3/10 |  8/12 |    6/9 |       0/1 | 0/1 |       0/1 |      33% |
| GLM-5             | 2/10 |  0/12 |    0/9 |       1/1 | 0/1 |       0/1 |      24% |
| DeepSeek V3.2     | 3/10 |  0/12 |    2/9 |       0/1 | 0/1 |       1/1 |      10% |





<!-- 

claude opus 4.6: education 1/1, search 6/10, search 10/12, health 7.5, eval 0/1, usability 0/1


Qwen3-Max: 3/10
Deepseek V3.2: 3/10
GLM: 2/10
Kimi k2.5: 7/10
Gemini 3 pro: 7/10
gpt5.2: 9/10
Grok: 8/10
Claude Sonnet 4.5: 4/10 

if i ask for 20 benchmarks

grok4.1 expert: 4/20
gpt5.2: 6/20
kimi k2.5: 6/20
gemini 3 pro: 3/20, hallucinates like crazy


q2
Qwen3-Max: 8/12
Deepseek V3.2: 0/12
GLM: 0/12
Kimi k2.5: 6/12
Gemini 3 pro: 8/12
gpt5.2:8/12
Grok: 9/12
Claude Sonnet 4.5: 4/12

q3
Qwen3-Max: 0/1
Deepseek V3.2: 1/1
GLM: 0/1
Kimi k2.5: 1/1
Gemini 3 pro: 0/1
gpt5.2: 1/1
Grok: 1/1
Claude Sonnet 4.5: 0/1

q4
Qwen3-Max: 6/9
Deepseek V3.2: 2/9
GLM: 0/9
Kimi k2.5: 6/9
Gemini 3 pro: 5/9
gpt5.2: 7/9
Grok: 4/9
Claude Sonnet 4.5: 6.5/9


q5
Qwen3-Max: 0/1
Deepseek V3.2: 0/1
GLM: 1/1
Kimi k2.5: 0/1
Gemini 3 pro: 1/1
gpt5.2: 0/1
Grok: 1/1
Claude Sonnet 4.5: 1/1

-->



### Q1
```
find 10 benchmarks with public leaderboards where gemini 3 pro and gpt5.2 cannot achieve a 50% accuracy. Provide a link to the leaderboard, and report the score of gemini 3 pro and gpt5.2
```

The answer to this question is basically the first section of this blog.

### Q2
```
Add two columns called "score" and "best model" at the end and fill them in. the score entries should be rounded to 2 sig figs. 
| Category     | Benchmark                                                                                      |
| ------------ | ---------------------------------------------------------------------------------------------- |
| Coding       | [Terminal-Bench 2.0](https://www.tbench.ai/leaderboard/terminal-bench/2.0)                     |
| Coding       | [SWE-Bench Pro (Public)](https://scale.com/leaderboard/swe_bench_pro_public)           |      
| Coding       | [Vibe Code Bench](https://www.vals.ai/benchmarks/vibe-code)                                    |    
| Puzzles      | [SimpleBench](https://simple-bench.com/)                                                       |
| Mathematics  | [FrontierMath](https://epoch.ai/frontiermath)                                                  | 
| General      | [Arena.ai Leaderboard](https://arena.ai/leaderboard)                                           | 
| Vision       | [ZeroBench](https://zerobench.github.io/)                                                      | 
| Knowledge    | [Humanity's Last Exam](https://scale.com/leaderboard/humanitys_last_exam)                      | 
| Agentic      | [Remote Labor Index](https://scale.com/leaderboard/rli)                                        |
| Agentic      | [Vending-Bench 2](https://andonlabs.com/evals/vending-bench-2)                                 |
| Agentic | [GDPval](https://evals.openai.com/gdpval/leaderboard) |
| Long context | [MRCR (1M, 8 needles)](https://contextarena.ai/?needles=8) |
```

The answer to this question is also the first section of this blog.

The challenge in this question is that some leaderboards are outdated and the AI has to read the recent blogs on Claude Opus 4.6, Gemini 3 Deep Think, and GPT Codex 5.3 to get the up-to-date numbers. 

### Q3
```
list all the factors for increasing or lowering the risk of heart disease in a table and provide the statistical risk impact of each
```

I have a list of nine factors that I selected beforehand after doing extensive research. A few factors on my list are less well known, making this question challenging.

### Q4
```
design a self-study cs curriculum that can get you a job at google or meta. 
```

This is subjective, but I'd say I have good taste on this topic. 


### Q5
```
from openai import OpenAI

def call_model(input):
    client = OpenAI()
    response = client.responses.create(
        model="gpt-5",
        tools=[{"type": "code_interpreter", "container": {"type": "auto"}}],
        input=input,
    )
    return response.output_text

Write the complete Python code for a new LLM eval, where model calls use the above code. The eval has to satisfy the below constraints 
1. gpt-5 with code_interpreter fails the eval 
2. At least one human can succeed on the eval, given the same inputs, time constraint, and tool (code_interpreter)
3. The human also has to comply with gpt-5's safety and content policies
4. The inputs and outputs are text only; no images or audio

```

I discovered a prompt that fails all current LLMs. The prompt basically asks the LLM to create an eval that it cannot solve itself. Prompts like this can potentially be used in an RL training algorithm where learning iterates between an attacker and a defender, with continuous self-improvement potential.

### Q6
```
Not a prompt for the LLM.
Check whether the conversation persist after a website refresh,
and whether the website allows many sessions at once.
```

Sadly, Gemini and Claude have some restrictions here, perhaps to slow per-user usage.

## Video games
Improving LLM performance on video games is a great step toward achieving physical intelligence. Simulated environments can be made to mimic real environments, and an algorithm that outperforms other algorithms in the simulated environment is likely to outperform in the real environment as well. Video games challenge LLMs on many fronts, including image understanding, long context, and reasoning.

There are many games in the browser and in mobile app stores, so how do we turn all those games into RL environments? I'm not sure and would be happy for someone to teach me. One thing I'm not a big fan of is developing games just for evaluating AIs because it is time-consuming and the additional value over existing games might be minimal.

A particular game that I care about is Go. How do we develop an LLM learning algorithm that can simultaneously teach the model Go, coding, and math? AlphaZero hard-coded the Monte Carlo tree search algorithm. To make the algorithm more general, the model should decide, through reasoning, which nodes to explore further and what data to learn from. We know it's possible to achieve superhuman-level strength in Go. Now we just have to do it one more time, with a more general algorithm that also works for coding and math. The impact of developing such an algorithm will extend far beyond just Go.

## Web browsing
Web browsing is my main use case for LLMs. If one Google search request can give me the answer, I will use Google Search. Otherwise, I will use an LLM. Many of my queries require synthesizing information across 10+ articles, so an LLM can save me a lot of time. 

The problem with web browsing is that the only popular benchmark, BrowseComp, is getting saturated by Claude Opus 4.6, and that most other web browsing benchmarks have no up-to-date leaderboards. Worse, I'm not sure whether all APIs support web search. This is one case where the app experience might be more advanced than the API experience.

<!-- what moves should i do for 2x a week full body strength training
help edit my blog post for grammar and style. do not make unnecessary changes. i usually need to prompt it a few times to correct all the mistakes
-->