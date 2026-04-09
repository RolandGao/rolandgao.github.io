I have compiled a list of unsaturated evals, most of which have up-to-date public leaderboards. Then I created some hard prompts for independent testing. Finally, I discuss the need for more video game and web browsing evals.

## Unsaturated evals

| Category     | Benchmark                                                                                      |        Score | Best model                         |
| ------------ | ---------------------------------------------------------------------------------------------- | -----------: | ---------------------------------- |
| Coding       | [SWE-Bench Pro (Public)](https://scale.com/leaderboard/swe_bench_pro_public)           |          58% | GPT-5.4                     |
| Coding       | [Vibe Code Bench](https://www.vals.ai/benchmarks/vibe-code)                                    |          67% | GPT-5.4                            |
| Coding        | [SlopCodeBench](https://www.scbench.ai/leaderboard)                                     |          17% | Claude Opus 4.6                      |
| Coding        | [Codebase QnA](https://labs.scale.com/leaderboard/sweatlas-qna)                                     |          41% | GPT-5.4                      |
| Puzzles      | [SimpleBench](https://simple-bench.com/)                                                       |          80% | Gemini 3.1 Pro                       |
| Chess        | [Chess](https://dubesor.de/chess/chess-leaderboard)                                     |          1834 Elo | Gemini 3.0 Pro                       |
| Mathematics  | [FrontierMath](https://epoch.ai/frontiermath)                                                  |          50% | GPT-5.4 Pro              |
| General      | [Arena.ai Leaderboard](https://arena.ai/leaderboard)                                           |     1.5k Elo | Claude Opus 4.6         |
| Vision       | [ZeroBench](https://zerobench.github.io/)                                                      | 23%          | GPT-5.4                       |
| Knowledge    | [Humanity's Last Exam](https://scale.com/leaderboard/humanitys_last_exam)                      |          53% | Gemini 3 Deep Think                |
| Agentic      | [Remote Labor Index](https://scale.com/leaderboard/rli)                                        |         4.2% | Claude Opus 4.6         |
| Agentic      | [Vending-Bench 2](https://andonlabs.com/evals/vending-bench-2)                                 |   8.0k / 63k | Claude Opus 4.6                    |

## Recently saturated evals

| Category     | Benchmark                                                                                      |        Score | Best model                         |
| ------------ | ---------------------------------------------------------------------------------------------- | -----------: | ---------------------------------- |
| Mathematics | [PutnamBench](https://trishullab.github.io/PutnamBench/leaderboard.html) | 668 / 672 | Aleph Prover (Logical Intelligence) |
| Web Browsing | [BrowseComp](https://openai.com/index/browsecomp/) | 84% | Claude Opus 4.6 |
| Puzzles | [ARC-AGI 2](https://arcprize.org/leaderboard) | 85% | Gemini 3 Deep Think |
| Long context | [MRCR (1M, 8 needles)](https://contextarena.ai/?needles=8) | 76% | Claude Opus 4.6 |
| Coding       | [Terminal-Bench 2.0](https://www.tbench.ai/leaderboard/terminal-bench/2.0)                     |          82% | GPT-5.4  |
| Agentic | [GDPval](https://evals.openai.com/gdpval/leaderboard) | 83% | GPT-5.4 |


<!-- honorable mentions

| Science      | [SciPredict](https://scale.com/leaderboard/scipredict)                                         |          25% | Gemini 3 Pro Preview               |
| Puzzles      | [EnigmaEval](https://scale.com/leaderboard/enigma_eval)                                        |          19% | GPT-5 Pro (2025-10-06)             |
| Vision       | [VisualToolBench](https://scale.com/leaderboard/vtb)                                           |          27% | Gemini 3 Pro               |
| Coding        | [Roblox Open Game Eval](https://github.com/Roblox/open-game-eval/blob/main/LLM_LEADERBOARD.md) | 55% (pass@1) | Gemini 3 Flash                     |

Formal Conjectures: https://github.com/google-deepmind/formal-conjectures, no leaderboard
iq test: https://www.trackingai.org/home
https://toolathlon.xyz/docs/leaderboard
-->


## Independent testing

| Metric                              | Claude Opus 4.6 Extended Thinking |  Grok 4.1 | Gemini 3.1 Pro | GPT-5.4 Extended Thinking | Meta Muse |
| ----------------------------------- | --------------------------------: | --------: | -------------: | ------------------------: | --------: |
| find AI benchmarks                  |                              6/10 |      8/10 |           8/10 |                      7/10 |      8/10 |
| find benchmark numbers              |                             10/12 |      9/12 |         8.5/12 |                      9/12 |      8/12 |
| Health                              |                             7.5/9 |       4/9 |            4/9 |                     6.5/9 |       6/9 |
| Education                           |                               1/1 |       1/1 |            1/1 |                       0/1 |       1/1 |
| Make LLM Eval                       |                               0/1 |       0/1 |            0/1 |                       0/1 |       0/1 |
| find uoft cs phds                   |                            86/200 |    58/200 |         18/200 |                    50/200 |    23/200 |
| find frontier ai labs               |                            31/100 |    31/100 |         19/100 |                    50/100 |    28/100 |
| Tax 1                               |                             0.5/1 |       0/1 |            1/1 |                     0.5/1 |     0.5/1 |
| Immigration 1                       |                               1/3 |       0/3 |            0/3 |                       0/3 |       3/3 |
| Immigration 2                       |                               1/3 |       0/3 |            3/3 |                       1/3 |       3/3 |
| find companies with hard interviews |                               0/1 |       1/1 |            0/1 |                       1/1 |       0/1 |
| optimizer                           |                                 — |     0.5/1 |            0/1 |                       1/1 |       1/1 |
| affiliation                         |                                 — |     0.6/1 |            0/1 |                       1/1 |     0.6/1 |
| **Avg**                             |                         **47.0%** | **43.8%** |      **40.3%** |                 **52.0%** | **58.7%** |




<!-- 
which companies hiring computer science students have the hardest interviews? 
answer: openai, anthropic, jane street

For each of the following authors, find their current affiliation. output should be one name per row, and each row is "{name} | {affiliations comma separated}". if it's unknown, put unknown in the affiliations
gemini: 0/1
grok 0.6/1
chatgpt: 1/1


how to ace the meta swe interview?
two leetcode mediums in 45 minutes. bug free.
communicate: reasoning, trade-offs, edge cases

They test edge cases without being asked.
They name tradeoffs clearly instead of pretending there’s one perfect solution.
They keep talking while debugging.

clarify the problem, state assumptions, give a brute-force approach, improve it, code cleanly, then test edge cases out loud

mock interviews
biggest project

chatgpt gave the best answer
https://www.metacareers.com/swe-prep-onsite 
-->

<!-- 


meta muse
health: 6/9
cs education: 1/1
find 10 benchmarks: 8/10
benchmark numbers: 8/12
usability: 1/1
optimizer: 1/1
uoft cs phd: 23
frontier companies: 28
401k: 0.5/1
immigration 1: 3/3
immigration 2: 3/3
affiliation: 0.6/1



what optimizer should i use to train LLMs
gemini: 0/1
chatgpt: 1/1
grok: 0.5/1

grok4.2: 
q1: 7/10
q2: 9/12
q3: 6.5
q4: 0.5/1

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

list all the profs at university of toronto that do research in machine learning and the number of phd students each has

Colin Raffel

gpt5.2: 0/4
gemini 3: 2/4
grok: 2/4
claude: 1/4, no attempt on getting num students
kimi: 2/4

find as many current cs phds at university of toronto
grok4.2: 201
claude: 86
gemini 3: 59
grok4.1: 58
gpt5.2: 29
kimi: 39
gemini 3.1 pro: 18



find as many US-based frontier AI companies as possible
claude: 31
grok4.2: 31
openai: 24
gemini 3.1 pro: 19
kii: 31. 


all AIs said TML except gpt5.2. 
grok is the only AI that said humans&. 

what's the relationship between batch size, learning rate, and weight decay in a neural network

given 50% employer match, 300K salary, age 25, how much money can i put into 401k in 2025?
grok4.1: 0/1
grok4.2: 0/1
claude opus4.6: 0.5/1 mentioned mega backdoor, but no calculation
gpt5.2: 0.75/1, mentioned mega backdoor, showed calc, but no sum
gemini 3.1 pro: 1/1



how long can i stay in the us as a tourist? Im canadian
return ticket, lease. could deny entry
gpt5.2: 0/3
grok4.1: 0/3
claude opus4.6: 1/3
gemini 3.1 pro: 0/1

after quitting my job on a TN visa and going back to canada, how long can i stay in the US on a tourist visa?
return ticket, lease. could deny entry
gpt5.2: 3/3, could deny entry, return ticket, job, lease, family
grok4.1: 0/3, residence, employment prospects, or family
claude opus4.6: 1/3, a home, a job, family. could be denied entry
gemini3.1 pro: 3/3. lease or mortgage, utility bills, return ticket

# https://techcrunch.com/2026/02/17/here-are-the-17-us-based-ai-companies-that-have-raised-100m-or-more-in-2026/

-->

Whenever a frontier model fails a prompt I asked, I add it into my independent testing suite. Out of my prompts, this following one is the only one that withstood all the frontier LLMs, with no exceptions. I name this prompt "Make LLM Eval".

The prompt basically asks the LLM to create an eval that it cannot solve itself. Prompts like this can potentially be used in an RL training algorithm where learning iterates between an attacker and a defender, with continuous self-improvement potential.

Recently, I tried codex 5.4 with almost 1 hour of thinking time, and it still could not solve this question reliably. 

```
from openai import OpenAI

def call_model(input):
    client = OpenAI()
    response = client.responses.create(
        model="gpt-5",
        tools=[
            {"type": "code_interpreter", "container": {"type": "auto"}}
        ],
        input=input,
    )
    return response.output_text

Write the complete Python code for a new LLM eval, where model calls use the above code. The eval has to satisfy the below constraints 
1. gpt-5 with code_interpreter fails the eval 
2. Many human experts can succeed on the eval, given the same inputs, time constraint, and tool (code_interpreter)
3. The human also has to comply with gpt-5's safety and content policies
4. The inputs and outputs are text only; no images or audio
5. The eval cannot exploit the fact that the AI does not have human's identify or physical attributes. 
6. The eval has to be about showing gaps between human intelligence and machine intelligence
```

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