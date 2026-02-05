I compiled a list of unsaturated evals, as shown below. Afterward, I discuss some ideas for developing unsaturated evals.

| Category            | Benchmark                                                                   | Score                                     |
| ------------------- | --------------------------------------------------------------------------- | ----------------------------------------- |
| Math                | [FrontierMath](https://epoch.ai/frontiermath)                               | 38%                                       |
| Math                | [PutnamBench](https://trishullab.github.io/PutnamBench/leaderboard.html)    | 462 / 657                                 |
| Coding              | [Terminal-Bench 2](https://www.tbench.ai/leaderboard/terminal-bench/2.0)    | 59%                                       |
| Coding              | [LiveCodeBench Pro](https://livecodebenchpro.com/)                          | 49%                                       |
| Coding              | [SWE-rebench](https://swe-rebench.com/)                                     | 44% (no gemini 3 yet)                     |
| Coding              | [Vibe Code Bench](https://www.vals.ai/benchmarks/vibe-code)                 | 25%                                       |
| Puzzles             | [ARC-AGI 2](https://arcprize.org/leaderboard)                               | 45%                                       |
| Puzzles             | [EnigmaEval](https://scale.com/leaderboard/enigma_eval)                     | 19%                                       |
| Puzzles             | [SimpleBench](https://simple-bench.com/)                                    | 76%                                       |
| Puzzles             | [TrackingAI offline IQ test](https://www.trackingai.org/home)               | 130                                       |
| Vision              | [ZeroBench](https://zerobench.github.io/)                                   | 19% (pass@5)                              |
| Vision              | [VisualToolBench](https://scale.com/leaderboard/vtb)                        | 27%                                       |
| Knowledge           | [HLE](https://scale.com/leaderboard/humanitys_last_exam)                    | 46% — best: gemini 3                      |
| Long Context        | [MRCR](https://contextarena.ai/?needles=8)                                  | 35.3% (1M, 8n) · 54% (128K, 8n)           |
| Agentic             | [Vending-Bench](https://andonlabs.com/evals/vending-bench-2)                | 5.5k/63k                                  |
| Video Games         | [VideoGameBench](https://www.vgbench.com/)                                  | 0.48% (no gemini 3 yet)                   |
| Web Browsing        | [BrowseComp](https://openai.com/index/browsecomp/)                          | 69% — best: OpenAI Agent (no leaderboard) |
| Multilingual        | [MultiNRC](https://scale.com/leaderboard/multinrc)                          | 65%                                       |
| Multi-turn Dialog   | [MultiChallenge](https://scale.com/leaderboard/multichallenge)              | 64%                                       |

<!-- honorable mentions
Formal Conjectures: https://github.com/google-deepmind/formal-conjectures, no leaderboard
GDPval: https://evals.openai.com/gdpval/leaderboard, no gemini 3
lmarena: https://lmarena.ai/leaderboard 
https://www.vals.ai/benchmarks/vibe-code
https://www.scbench.ai/
https://qwenlm.github.io/Qwen-Agent/en/benchmarks/deepplanning/
-->

## Video games
Improving LLM performance on video games is a great step toward achieving physical intelligence. Simulated environments can be made to mimic real environments, and an algorithm that outperforms other algorithms in the simulated environment is likely to outperform in the real environment as well. Video games challenge LLMs on many fronts, including image understanding, long context, and reasoning.

There are many games in the browser and in mobile app stores, so how do we turn all those games into RL environments? I'm not sure, and would be happy for someone to teach me. One thing I'm not a big fan of is developing games just for AI because it is time consuming and their additional value over the existing games might be minimal. 

A particular game that I care about is Go. How do we develop an LLM learning algorithm that can simultaneously teach the model Go, coding, and math? AlphaZero hard coded the monte carlo tree search algorithm. To make the algorithm more general, the model should decide, through reasoning, which node to explore further and what data to learn from. We know it's possible to achieve superhuman level strength in Go. Now we just have to do it one more time, with a more general algorithm that also works for coding and math. The impact of developing such an algorithm will extend far beyond just Go. 

## Web Browsing
Web browsing is my main use case for LLMs. If one google search request can give me the answer, I will use google search. Otherwise, I will use ChatGPT. Many of my queries requires synthesizing information across 10+ articles, so ChatGPT can save me a lot of time. The problem with Web Browsing right now is there's not enough effort in frontier labs to improve the performance here. Web Browsing somehow doesn't get as much attention as math or coding. For one, there's only one browsing benchmark, BrowseComp, and there's no public leaderboard for this benchmark. Worse, I'm not sure whether all the APIs have support for web search. This is one case where the App experience might be more advanced than the API experience. 

## Usability
For me, ChatGPT has the best user experience. If Gemini 3 is still thinking when I refresh the browser or close the app, the conversation is gone. I would have to stay on the page until it finishes thinking, which wastes time. ChatGPT does not have this problem, and I can have 10 different conversations in parallel. 

## Some prompts I use to evaluate models


### prompt 1
I discovered a prompt that fails all current LLMs. The prompt basically asks the LLM to create an eval that it cannot solve itself. An example of this prompt on GPT-5 is [here](https://chatgpt.com/share/68f08459-4ff8-8011-8eab-31c0d4862ae2). Prompts like this can potentially be used in an RL training algorithm where the the learning iterates between an attacker and a defender, with continuous self-improvement potential.

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

### prompt 2

```
The following is a list of current Stanford CS PhDs; find where they attended undergrad. Each line in the output should be in the format of "{name} | {school}". Do not output any citations or annotations. Use the web browsing tool. Do not ask followup questions. If the school is not found, say "unknown" as the school.

Andy Bartolo
Tianlang Chen
Jared Davis
Boyang Deng
Nate Diamant
Perry Ang Dong
Ben Driscoll
Alireza Haqi
Qiantan Hong
Yunfan Jiang
Evan Laufer
Matthew Liu
Katherine Mohr
Michael Poli
Diana Popescu
Yicheng Qian
Daniel Richman
Yingxuan Tan
Sierra Wang
Haoran Xu
```

The answer key is below.

```
Andy Bartolo | Stanford University
Tianlang Chen | Peking University
Jared Davis | Washington University in St. Louis
Boyang Deng | Beihang University
Nate Diamant | Harvey Mudd College
Perry Ang Dong | University of California, Berkeley
Ben Driscoll | University of California, Berkeley
Alireza Haqi | Sharif University of Technology
Qiantan Hong | Massachusetts Institute of Technology
Yunfan Jiang | University of Edinburgh
Evan Laufer | University of California, San Diego
Matthew Liu | University of California, Berkeley
Katherine Mohr | Massachusetts Institute of Technology
Michael Poli | Nanjing University, University of Bologna
Diana Popescu | Georgia Institute of Technology
Yicheng Qian | Peking University
Daniel Richman | Massachusetts Institute of Technology
Yingxuan Tan | Rice University
Sierra Wang | University of Washington
Haoran Xu | Massachusetts Institute of Technology
```

Kimi K2: 19/20
GPT5 Thinking: 15/20
Claude: 7/20
Qwen3-Max: 6/20
Gemini 3: 0/20
Grok 4.1: 0/20
Deepseek V3.2: 0/20

<!-- what moves should i do for 2x a week full body strength training
help edit my blog post for grammar and style. do not make unnecessary changes. i usually need to prompt it a few times to correct all the mistakes
-->