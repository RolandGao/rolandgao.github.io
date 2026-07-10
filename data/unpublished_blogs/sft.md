## Tool use is all you need

A good idea is radical now, but obvious in retrospect.

what I am writing here is perhaps still radical but will become obvious in a year or two. 

The standard LLM training includes three stages: pre-training, SFT, and RL. They seem quite different, but they are all just next-token prediction in disguise.

I'm proposing a new paradigm called Learning through tool use. It not only generalizes the existing three stages of LLM training, but also enables continual learning and significantly higher data efficiency. Understanding how to learn through tool use can be a step in bridging the gap between human-learning and machine-learning.

TODO: revolutionizes reasoning. individual CoT is costly. what if the second CoT can see the first CoT? how about discrete vs continuous tokens?

Let's first define a few tools
```
tool1
sft(prompt, response, weight)
prompt is a list of tokens
response is a list of tokens
weight is a scalar.
This tool performs one gradient update with the objective of predicting the response tokens. The loss and gradient are scaled by the weight scalar.

So when does the weight update happen? The update should be async in nature, because we don't want the update to stall subsequent text generations. When we want to do the weight update, we would collect all the async sft calls and train on all the data in these sft calls. During the pre-release training phase, especially during RL, the model can benefit a lot from frequent gradient updates, perhaps once every minute. But after the model release, model serving prefers not changing the weights for every user chat thread, we can perform weight update once every night. For large-scale tasks, 

When doing long-horizon tasks that take a few hours or more, the model might benefit from test-time training as a way to support long-context. One way to support this is to have one set of weights for every long-horizon task, where the weight for each task is expected to change over time through sft tool calls. But we can merge all the learnings for all tasks at the end by deleting the per-task weights and training the base model on the combined sft tool calls. The same data performed gradient updates twice, once during the task, one at the end for merging. 

Given the sft tool definition, there are many details abstracted away, such as the learning rate and weight decay. Researchers have to tune these beforehand. Automating hyperparameter search is possible, but hard to do. 

tool2
read(file_name, index, length)
This tool opens the file with file_name and returns a list of tokens with the specified length starting at the specified index.

tool3
gen(prompt)
This tool generates a response given the prompt. The LLM weights used to generate the response can be either itself or some other stored checkpoint.

TODO: coding is the ultimate tool. it generalizes all these tools. coding + data inspection. 
TODO: basically, training data curation. LLM decides what training data to use. 
TODO: there are two main tasks. data curation, and model trainnig. LLM can do both. 
the three stages are different ways to curate the data, but the training phase is the same.
AI research done by LLM. LLM trying to produce the next LLM. 

data, training, infra
```

## Technical details of the sft tool. 
The final consideration is how to teach the model to use the sft tool. If we can create a setup where the model self-improves on its usage of the sft tool, the model has "learned how to learn". If this is achieved, once we create the initial setup, the model is able to learn anything by itself. In particular, it can learn to use the sft tool more effectively over time. 

## test time scaling

## pretraining
Input: data with no structure
Summary: we have three tools: read, gen, and sft. LLM calls these tools to read the data, gen, sft. 

data_chunk1 = read("document1", index=0, length=8096)
data_chunk2 = read("document1", index=8096, length=8096)

data_chunk1 = gen(prompt_for_cleaning + data_chunk1)
data_chunk2 = gen(prompt_for_cleaning + data_chunk2)

sft([], data_chunk1, 1)
sft([], data_chunk2, 1)


## SFT
Input: data in the format of (prompt, response) pairs

prompt1 = read("prompt1", index=0, length=8096)
response1 = read("response1", index=0, length=8096)

prompt2 = read("prompt2", index=0, length=8096)
response2 = read("response2", index=0, length=8096)

sft(prompt1, response1, 1)
sft(prompt2, response2, 1)

## RL
Input: data in the format of (prompt, reward_function) pairs. 

For each prompt, we do the following.

response_1 = gen(prompt)
...
response_99 = gen(prompt)

reward_1 = reward_function(response_1)
...
reward_99 = reward_function(response_99)

\[transformed_reward_1, ..., transformed_reward_99\] = transformation(reward_1, ..., reward_99)

sft(prompt, response_1, transformed_reward_1)
...
sft(prompt, response_99, transformed_reward_99)


So far, this is not very interesting. We merely rewrote the learning formulas used in the three stages by using tool calling, especially the sft tool. The interesting thing is: currently, the "tool calls" are manual, hand designed by top researchers. But under this generalized tool calling perspective, we see that there's no reason why the model can't be the one calling those tools. By replacing the manual steps with LLM-automated steps, we are left with a much more automated learning process. 

We assumed the existence of a LLM capable of reliable tool calling, and I believe this has been achieved in 2025 with the release of openai's o3 model. This is why this research idea could not be realized one year ago but is possible now. 

The model can decide for itself when to learn, what to learn. 

All forms are learning are just tool calling. 

## AlphaZero

How do we train an LLM to play Chess and Go? 

according to the paper (https://arxiv.org/pdf/1712.01815), AlphaZero played about 1M games to be at a level that beats Lee Sedol. 
Lee Sedol played 1900 games professionally, and suppose he played 2100 games in private, totaling 4000 games. AlphaZero used 250 times as many games to get to the same level. This shows the existence of a learning algorithm (the top human's learning algorithm) that's much more data efficient than AlphaZero. 

naive:
We use the original AlphaZero algorithm code, but replace policy and value network calls with LLM gen calls. We also transform the generated training data to the format required by LLMs. If the LLM learns as quickly as the network in the original paper, then it will take an equal number of train steps as the original network. However, an LLM is much bigger than the network used in the original network, causing training duration to skyrocket. 

less naive:
this method is not necessarily better, as there's no experiment backing this method. 
LLM can decide for itself how to spend the compute. 
It can adaptively think longer on harder board states. It can decide for itself which states to explore more, instead of relying on the UCB (Upper Confidence Bound). It can decide for itself which data points are worth learning. 

For example, the only ground-truth reward is the end-game win or lose signal. (+1, -1). 
How do we attribute this signal to the few moves that significantly contributed to this end-game win or loss? 
The original AlphaZero learns this through emergence of large-scale data, but LLMs might be able to directly attribute the few significant moves and directly learn them.

## Reading a math textbook
If I ask an LLM to read a math textbook, will it learn as much from this book as a human would? Probably not. Humans are more data efficient than current LLMs. We can think of ways to improve LLM's data efficiency. 

A math textbook includes prose, and pairs of questions and answers. Many college-level math textbooks contain only the prose and questions, with no answers.
pre-training throws away all this structure. RL requires manual data curation and throws away the prose and keeps only the questions and answers (and the answers have to somehow induce a reward_function)

Humans do not naively do SFT on the text. One theory is that humans think a lot to find a good explanation for the surface text, and humans memorize the good explanation, without memorizing the surface text. One visualization of this is that students take notes during lectures or during reading. Much of the knowledge in lectures and textbooks are condensed to notes and then the human learns from the notes. 

When doing questions with no answers, the student probably still learned something from doing the question. Maybe it learned an algebra manipulation trick, that a certain statement is false, or a few approaches that might work on other problems even though they didn't work on this problem. These learnings fall outside the standard RL training, but can be included in the generalized SFT tool call learning. 

## Reading a philosophy book
If I ask an LLM to read Plato's Republic, can it learn as much from this book as a human would? Probably not. There's no obvious verifiable reward for this book. 



## Coding
Coding agents have gotten much better in the past year, but is still unable to replace good software engineers just yet. Many coding evals are still unsaturated. It's still hard to build a simple website with the perfect UI. Coding is one area where researchers are creative about the types of data the LLM can learn from. One common way is perhaps synthetic or transformed data on top of public GitHub issues and pull requests. The sft tool call can take over this process. 

## Long context
While researchers have been pushing for architectural changes that enable robust long context, I am reminded of the biological fact that humans have short context. Humans can remember only around 7 things in their short-term memory. 

Perhaps the solution to long context requires no architectural changes at all. A vanilla transformer should work just fine for the purpose of long context.

Inspired by humans, suppose we force the LLM's context to be short. Then, there are two places that an LLM can store its long-term memory: model weights and external file system. 

External file system involves tool calls that can read from and write to external files. OpenAI's API already supports external files (https://platform.openai.com/docs/api-reference/files), but the model has not learned to use this feature as long-term memory yet. In my next blog, I will try to use prompting to make the model learn this. 

But in this blog, I will focus on model weights. When given a long prompt, the model would read it in chunks, and call the sft tool on things it thinks are foundational or important. After reading the entire prompt and understanding what the user's request actually is, the model should be allowed to read previous chunks again by using the seek() tool. It will draw its answer based on the updated model weights caused by the sft() tool, as well as going over the prompt potentially many times using the seek() tool.