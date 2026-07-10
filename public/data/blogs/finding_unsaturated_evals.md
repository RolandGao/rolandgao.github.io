I have compiled a list of unsaturated evals, most of which have up-to-date public leaderboards. Then I created some hard prompts for independent testing. Finally, I discuss the need for more video game and web browsing evals.

## Unsaturated evals


| Category     | Benchmark                                                      |      Score | Best model                       |
| ------------ | -------------------------------------------------------------- | ---------: | -------------------------------- |
| Agentic      | [Agent's Last Exam](https://agents-last-exam.org/leaderboard)  |        31% | GPT-5.6                         |
| Puzzles      | [SimpleBench](https://simple-bench.com/)                       |        82% | Fable 5                          |
| Chess        | [Chess](https://dubesor.de/chess/chess-leaderboard)            |   1.8k Elo | Gemini 3.0 Pro                   |
| Vision       | [ZeroBench](https://zerobench.github.io/)                      |        23% | GPT-5.4 (no GPT-5.6)             |
| Agentic      | [Vending-Bench 2](https://andonlabs.com/evals/vending-bench-2) | 11k / $63k | Claude Opus 4.7                  |
| Long context | [MRCR (512k, 8 needles)](https://contextarena.ai/?needles=8)   |        58% | GPT-5.5 (no GPT-5.6)             |
| Coding       | [SlopCodeBench](https://www.scbench.ai/leaderboard)            |        14% | GPT 5.5 (no GPT-5.6) |
| Coding       | [ProgramBench](https://programbench.com/)                      |       0.5% | GPT 5.5 (no GPT-5.6) |


<!-- ## Recently saturated evals



| Category     | Benchmark                                                                                      |        Score | Best model                         |
| ------------ | ---------------------------------------------------------------------------------------------- | -----------: | ---------------------------------- |
| Coding      | [Vibe Code Bench](https://www.vals.ai/benchmarks/vibe-code)                                                  |              90% | Fable 5                  |
| Mathematics | [FrontierMath](https://epoch.ai/frontiermath/tiers-1-4?view=graph&tab=release-date&tier=Tier+4+%28v2%29) |        87% | Fable 5                |
| Mathematics | [PutnamBench](https://trishullab.github.io/PutnamBench/leaderboard.html) | 668 / 672 | Aleph Prover (Logical Intelligence) |
| Web Browsing | [BrowseComp](https://openai.com/index/browsecomp/) | 84% | Claude Opus 4.6 |
| Puzzles | [ARC-AGI 2](https://arcprize.org/leaderboard) | 85% | Gemini 3 Deep Think |
| Coding       | [Terminal-Bench 2.0](https://www.tbench.ai/leaderboard/terminal-bench/2.0)                     |          82% | GPT-5.4  |
| Agentic | [GDPval](https://evals.openai.com/gdpval/leaderboard) | 83% | GPT-5.4 | -->


<!-- honorable mentions
Formal Conjectures: https://github.com/google-deepmind/formal-conjectures, no leaderboard
iq test: https://www.trackingai.org/home
https://benchmark.gtowizard.com/

sycophancy eval
https://github.com/lechmazur/sycophancy


to slow to update
| General      | [Arena.ai Leaderboard](https://arena.ai/leaderboard)                                           |     1.5k Elo | Claude Opus 4.6         |
https://artificialanalysis.ai/evaluations/humanitys-last-exam 
-->


## Independent testing


| Metric                              | Claude Opus 4.8 Max | Grok 4.5 | Gemini 3.1 Pro | GPT-5.6 xhigh | Meta Muse 1.1 |
| ----------------------------------- | ------------------: | -------: | -------------: | ------------: | ------------: |
| health                              |                 4/9 |      6/9 |            4/9 |           7/9 |           6/9 |
| optimizer                           |                 1/1 |      1/1 |            0/1 |           1/1 |           1/1 |
| days to learn ap calc               |                 0/1 |      0/1 |            1/1 |           0/1 |         0.5/1 |
| days to learn multi calc            |                 0/1 |      1/1 |            1/1 |         0.5/1 |           1/1 |
| interview prep                      |                 1/1 |      1/1 |            1/1 |         0.5/1 |           1/1 |
| iOS battery icon while charging     |                 0/1 |      0/1 |            0/1 |           0/1 |           0/1 |
| make LLM Eval                       |                 0/1 |      0/1 |            0/1 |           0/1 |           0/1 |
| tax 1                               |                 0/1 |      0/1 |            1/1 |           1/1 |         0.5/1 |
| immigration 1                       |                 0/3 |      1/3 |            0/3 |           0/3 |           2/3 |
| immigration 2                       |                 1/3 |      1/3 |            3/3 |         1.5/3 |           2/3 |
| find uoft cs phds                   |              93/200 |   78/200 |         18/200 |       116/200 |        35/200 |
| find good companies                 |                 1/1 |      1/1 |            0/1 |           0/1 |           1/1 |
| find where people work              |               0.5/1 |    0.5/1 |            0/1 |         0.9/1 |         0.7/1 |
| parallel sessions in UI             |                 0/1 |      1/1 |            0/1 |           1/1 |           1/1 |
| **Average**                         |            **0.34** | **0.52** |       **0.40** |      **0.55** |      **0.63** |




<!-- 

im eating amox clav antibiotics and have some stomach issues, what probiotic should i buy from amazon.ca 

how to make adamw rotationally invariant?

what's the best way to tune the learning rate and momentum, both the initial value and the scheduler?

add two columns at the end: score, and best model. score is 2 sig figs. score is the score of the best model

meta ai: 6/7
gemini 6/7
grok: 6/7

| Category     | Benchmark                                                      |

| ------------ | -------------------------------------------------------------- |

| Agentic      | [Agent's Last Exam](https://agents-last-exam.org/leaderboard)  |

| Puzzles      | [SimpleBench](https://simple-bench.com/)                       |

| Chess        | [Chess](https://dubesor.de/chess/chess-leaderboard)            |

| Vision       | [ZeroBench](https://zerobench.github.io/)                      |

| Agentic      | [Vending-Bench 2](https://andonlabs.com/evals/vending-bench-2) |

| Long context | [MRCR (512k, 8 needles)](https://contextarena.ai/?needles=8)   |

| Coding       | [SlopCodeBench](https://www.scbench.ai/leaderboard)            |

| Coding       | [ProgramBench](https://programbench.com/)                      |


output this table twice, once with the last two columns removed

| Category    | Benchmark                                                                                                    |            Score | Best model                        |
| ----------- | ------------------------------------------------------------------------------------------------------------ | ---------------: | --------------------------------- |
| Agentic     | [Agent's Last Exam](https://agents-last-exam.org/leaderboard)                                               |     27% | Opus 4.8                  |
| Puzzles     | [SimpleBench](https://simple-bench.com/)                                                                     |              82% | Fable 5           |
| Chess        | [Chess](https://dubesor.de/chess/chess-leaderboard)                                     |          1.8k Elo | Gemini 3.0 Pro                       |
| Vision      | [ZeroBench](https://zerobench.github.io/)                                                                    |       23% | GPT-5.4                     |
| Agentic     | [Vending-Bench 2](https://andonlabs.com/evals/vending-bench-2)                                               |     11k / $63k | Claude Opus 4.7                   |
| Long context | [MRCR (512k, 8 needles)](https://contextarena.ai/?needles=8) | 58% | GPT-5.5 (no Fable 5) |
| Coding      | [SlopCodeBench](https://www.scbench.ai/leaderboard)                                                          | 14% | GPT 5.5 (no Fable 5 or Opus 4.8)               |
| Coding      | [ProgramBench](https://programbench.com/)                                                          | 0.5% | GPT 5.5 (no Fable 5 or Opus 4.8)               |


over the summer break, how long does it take to read multivariable calculus by James Stewart if i already finished calculus by spivak. i won't do any problems or exercises.
24 hours max.

how many days does it take to learn ap calculus during the summer break if i can get into aime
2 weeks max.
eval: anything more than 4 weeks is wrong

on ios 18 with battery percentage on, if my phone is below 20% battery and i start charging the phone. what color is the battery icon?


For each of the following authors, find their current affiliation. output should be one name per row, and each row is "{name} | {affiliations comma separated}". if it's unknown, put unknown in the affiliations

Diederik P. Kingma
Jimmy Ba
Ilija Radosavovic
Raj Prateek Kosaraju
Ross Girshick
Kaiming He
Piotr Dollár
Ilya Loshchilov
Frank Hutter
Ashish Vaswani
Noam Shazeer
Niki Parmar
Jakob Uszkoreit
Llion Jones
Aidan N. Gomez
Lukasz Kaiser
Illia Polosukhin
Xiaohan Ding
Xiangyu Zhang
Ningning Ma
Jungong Han
Guiguang Ding
Jian Sun
Priya Goyal
Pieter Noordhuis
Lukasz Wesolowski
Aapo Kyrola
Andrew Tulloch
Yangqing Jia
Siyuan Qiao
Huiyu Wang
Chenxi Liu
Wei Shen
Alan Yuille
Ron Banner
Itay Hubara
Elad Hoffer
Daniel Soudry
Pierre Foret
Ariel Kleiner
Hossein Mobahi
Behnam Neyshabur
Shaoqing Ren
Alec Radford
Karthik Narasimhan
Tim Salimans
Ilya Sutskever
Jeffrey Wu
Rewon Child
David Luan

list all the factors for increasing or lowering the risk of heart disease in a table and provide the statistical risk impact of each
# LDL/apoB, lp(a), flu infection, smoking, alcohol, water, sleep, stress/loneliness, exercise

design a self-study cs curriculum that can get you a job at google or meta. 

which companies hiring computer science students have the hardest interviews? 
answer: openai, anthropic, jane street


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

what optimizer should i use to train LLMs


find as many current cs phds at university of toronto

given 50% employer match, 300K salary, age 25, how much money can i put into 401k in 2025?


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

## Video games
Improving LLM performance on video games is a great step toward achieving physical intelligence. Simulated environments can be made to mimic real environments, and an algorithm that outperforms other algorithms in the simulated environment is likely to outperform in the real environment as well. Video games challenge LLMs on many fronts, including image understanding, long context, and reasoning.

There are many games in the browser and in mobile app stores, so how do we turn all those games into RL environments? I'm not sure and would be happy for someone to teach me. One thing I'm not a big fan of is developing games just for evaluating AIs because it is time-consuming and the additional value over existing games might be minimal.

A particular game that I care about is Go. How do we develop an LLM learning algorithm that can simultaneously teach the model Go, coding, and math? AlphaZero hard-coded the Monte Carlo tree search algorithm. To make the algorithm more general, the model should decide, through reasoning, which nodes to explore further and what data to learn from. We know it's possible to achieve superhuman-level strength in Go. Now we just have to do it one more time, with a more general algorithm that also works for coding and math. The impact of developing such an algorithm will extend far beyond just Go.

## Web browsing
Web browsing is my main use case for LLMs. If one Google search request can give me the answer, I will use Google Search. Otherwise, I will use an LLM. Many of my queries require synthesizing information across 10+ articles, so an LLM can save me a lot of time. 

The problem with web browsing is that the only popular benchmark, BrowseComp, is getting saturated by Claude Opus 4.6, and that most other web browsing benchmarks have no up-to-date leaderboards. Worse, I'm not sure whether all APIs support web search. This is one case where the app experience might be more advanced than the API experience.