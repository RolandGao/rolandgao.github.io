A good idea is radical now, but obvious in retrospect.

what I am writing here is perhaps still radical but will become obvious in a year or two. 

The standard LLM training includes three learning paradigms: pre-training, SFT, and RL. They seem quite different, and, indeed, frontier labs usually have separate teams for pre-trainig and post-trainig, and SFT is somehow more "solved" and the cool people work on either pretraining or RL.

But I argue that they all fall under the generalized learning paradigm of sequence prediction, and understanding how this works can be a step in bridging the gap between human-learning and machine-learning. This learning paradigm generalizes the existing three paradigms and enables continual learning, as well as significantly higher data efficiency. 

we can define a tool call called sft that takes in three parameters. 
sft(prompt, response, weight)

TODO: revolutionizes reasoning. individual CoT is costly. what if the second CoT can see the first CoT? how about discrete vs continuous tokens?

## pretraining
Input: data with no structure

naive:
separate the data into chunks of 8096 tokens
sft([], data_chunk1, 1)
sft([], data_chunk2, 1)
...

less naive:
clean the data. 
original_data_chunk1 = read("document1", index=0, length=8096)
cleaned_data_chunk1 = gen(prompt_for_cleaning + original_data_chunk1)
write("cleaned_document1", cleaned_data_chunk1)

original_data_chunk2 = read("document1", index=8096, length=8096)
cleaned_data_chunk2 = gen(prompt_for_cleaning + original_data_chunk1)
write("cleaned_document1", cleaned_data_chunk2, append = True)

This is equivalent to a user request in chatgpt where you
1. attach a file
2. give a prompt that asks chatgpt to clean the file
3. copy the output into a file. maybe chatgpt can directly write to a file. 


sft([], cleaned_data_chunk1, 1)
sft([], cleaned_data_chunk2, 1)
...

## SFT
Input: data in the format of (prompt, response) pairs

sft(prompt1, response1, 1)
sft(prompt2, response2, 1)
...

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


So far, this is not very interesting. We merely rewrote the learning formulas used in the three stages by using tool calling, especially the sft tool. The interesting thing is: currently, the "tool calls" are manual, hand designed by top researchers. But under this generalized tool calling perspective, we see that there's no reason why the model can't be the one calling those tools. By replacing the manual steps with LLM-automated steps, we are left with a fully automated learning process. 

We assumed the existence of a LLM capable of reliable tool calling, and I believe this has been achieved in 2025 with the release of openai's o3 model. This is why this research idea could not be realized one year ago but is possible now. 

The model can decide for itself when to learn, what to learn. 

All forms are learning are just tool calling. 

## AlphaZero

Suppose an LLM wants to improve its ability in Go and Chess. The AIs trained in the original AlphaZero paper could only play those games and not much else. While LLMs today can do many things but are nowhere near superhuman strength in Go and Chess. Could an LLM become superhuman at Go and Chess?

naive:
We use the original AlphaZero algorithm code, but replace policy and value network calls with LLM gen calls. We also transform the generated training data to the format required by LLMs. If the LLM learns as quickly as the network in the network in the original paper, then it will take an equal number of train steps as the original network. However, an LLM is much bigger than the network used in the original network, causing training duration to skyrocket. 

less naive:
this method is not necessarily better, as there's no experiment backing this method. 
LLM can decide for itself how to spend the compute. 
It can adaptively think longer on harder board states. It can decide for itself which states to explore more, instead of relying on the UCB (Upper Confidence Bound). It can decide for itself which data points are worth learning. 
For example, the only ground-truth reward is the end-game win or lose signal. (+1, -1). 

How do we attribute this signal to the few moves that significantly contributed to this end-game win or loss? 
The original AlphaZero learns this through emergence, but LLMs might be able to directly attribute the few significant moves and directly learn them.

AlphaZero 
according to the paper (https://arxiv.org/pdf/1712.01815), AlphaZero played about 1M games be at a level that beats Lee Sedol. 
Lee Sedol played 1900 games professionally, and suppose he played 2100 games in private, totally 4000 games. AlphaZero used 250 times as many games to get to the same level. This shows the existence of a learning algorithm (the top human's learning algorithm) that's much more data efficient than AlphaZero. 

## Reading a math textbook
A math textbook includes prose, and pairs of questions and answers. Many college-level math textbooks contain only the prose and questions, with no answers.
pre-training throws away all this structure. RL requires manual data curation and throws away the prose and keeps only the questions and answers (and the answers have to somehow induce a reward_function)

We can do much better in regards to data efficiency.

Humans do not naively do SFT on the text. One theory is that humans think a lot to find a good explanation for the surface text, and humans memorize the good explanation, without memorizing the surface text. One visualization of this is that students take notes during lectures or during reading. Much of the knowledge in lectures and textbooks are condensed to notes and then the human learns from the notes. 

## Coding
Coding agents have gotten much better in the past year, but is still unable to replace good software engineers just yet. Many coding evals are still unsaturated. It's still hard to build a simple website with the perfect UI. Coding is one area where researchers are creative about the types of data the LLM can learn from. One common way is perhaps synthetic or transformed data on top of public GitHub issues and pull requests. The sft tool call can take over this process. 

## Long context
While researchers have been pushing for architectural changes that enable robust long context, I am reminded of the biological fact that humans have short context. Humans can remember only around 7 things in their short-term memory. 

Perhaps the solution to long context requires no architectural changes at all. A vanilla transformer should work just fine for the purpose of long context.

Inspired by humans, suppose we force the LLM's context to be short. Then, there are two places that an LLM can store its long-term memory: model weights and external file system. 

External file system involves tool calls that can read from and write to external files. OpenAI's API already supports external files (https://platform.openai.com/docs/api-reference/files), but the model has not learned to use this feature as long-term memory yet. In my next blog, I will try to use prompting to make the model learn this. 

But in this blog, I will focus on model weights. When given a long prompt, the model would read it in chunks, and call the sft tool on things it thinks are foundational or important. After reading the entire prompt and understanding what the user's request actually is, the model should be allowed to read previous chunks again by using the seek() tool. It will draw its answer based on the updated model weights caused by the sft() tool, as well as going over the prompt potentially many times using the seek() tool.

## Technical details of the sft tool. 
Given the sft tool definition, there are many details abstracted away, such as the learning rate and weight decay. Researchers have to tune these beforehand. Automating hyperparameter search is possible, but hard to do. 

Another consideration is when to take the gradient step. We can default to async, and have a second tool called sft_flush() that forces all the sft steps to take place before the LLM continues.

The final consideration is how to teach the model to use the sft tool. If we can create a setup where the model self-improves on its usage of the sft tool, the model has "learned how to learn". If this is achieved, once we create the initial setup, the model is able to learn anything by itself. In particular, it can learn to use the sft tool more effectively over time. 