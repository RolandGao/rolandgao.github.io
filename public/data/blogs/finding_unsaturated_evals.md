I compiled a list of unsaturated evals, as shown below. Afterward, I discuss some ideas for developing unsaturated evals.

| Category            | Benchmark                                                                                               | Score                                     |
| ------------------- | ------------------------------------------------------------------------------------------------------- | ----------------------------------------- |
| Math                | [FrontierMath](https://epoch.ai/frontiermath)                                                           | 29%                                       |
| Math                | [PutnamBench](https://trishullab.github.io/PutnamBench/leaderboard.html)                                | 462 / 657                                 |
| Math                | [Formal Conjectures](https://github.com/google-deepmind/formal-conjectures)                             | — (no leaderboard)                        |
| Coding              | [Terminal-Bench](https://www.tbench.ai/leaderboard)                                                     | 60%                                       |
| Coding              | [SWE-rebench](https://swe-rebench.com/)                                                                 | 45%                                       |
| Puzzles             | [ARC-AGI 2](https://arcprize.org/leaderboard)                                                           | 29%                                       |
| Puzzles             | [EnigmaEval](https://scale.com/leaderboard/enigma_eval)                                                 | 13%                                       |
| Puzzles             | [SimpleBench](https://simple-bench.com/)                                                                | 62%                                       |
| Puzzles             | [TrackingAI offline IQ test](https://www.trackingai.org/home)                                           | 122                                       |
| GDP                 | [GDPval](https://evals.openai.com/gdpval/leaderboard)                                                   | 44%                                       |
| Knowledge           | [HLE](https://scale.com/leaderboard/humanitys_last_exam)                                                | 44 — best: Grok 4 Heavy                   |
| Image Understanding | [ZeroBench](https://zerobench.github.io/)                                                               | 5%                                 |
| Long Context        | [MRCR](https://huggingface.co/datasets/openai/mrcr) · [Leaderboard](https://contextarena.ai/?needles=8) | 28% (1M, 8n) · 40% (128K, 8n)             |
| Safety              | [FORTRESS](https://scale.com/leaderboard/fortress)                                                      | Risk 25 / Refusal 1.9%                    |
| Web Browsing        | [BrowseComp](https://openai.com/index/browsecomp/)                                                      | 69% — best: OpenAI Agent (no leaderboard) |
| Multilingual        | [MultiNRC](https://scale.com/leaderboard/multinrc)                                                      | 52%                                       |
| Video Games         | [VideoGameBench](https://www.vgbench.com/)                                                              | 0.48%                                     |
| Multi-turn Dialog   | [MultiChallenge](https://scale.com/leaderboard/multichallenge)                                          | 64%                                       |


Improving LLM performance on video games is a great step toward achieving physical intelligence. Simulated environments can be made to mimic real environments, and an algorithm that outperforms other algorithms in the simulated environment is likely to outperform in the real environment as well. Video games challenge LLMs on many fronts, including image understanding, long context, and reasoning.

A particular game that I care about is Go. How do we develop an LLM learning algorithm that can simultaneously teach the model Go, coding, and math? Such an algorithm is more general than what we have now and is perhaps closer to how humans learn. The impact of developing such an algorithm will extend far beyond just Go.

On the topic of developing evals, I especially like Jason Wei’s blog post [here](https://www.jasonwei.net/blog/evals). One additional piece of advice I have is that an eval should ideally have a public leaderboard, because LLM companies might not report numbers for all the evals we want.

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

<!-- Whenever a new LLM drops, I test it out with the following prompt to understand its web browsing capabilities. Interestingly, about half of the models I try fail on this prompt.

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
```

The answer key is below.

```
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
``` -->
