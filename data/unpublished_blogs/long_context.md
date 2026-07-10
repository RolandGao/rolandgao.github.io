While researchers have been pushing for architectural changes that enable robust long context, I am reminded of the biological fact that humans have short context. Humans can remember only around 7 things in their short-term memory. 

Perhaps the solution to long context requires no architectural changes at all. A vanilla transformer should work just fine for the purpose of long context.

Inspired by humans, suppose we force the LLM's context to be short. Then, there are two places that an LLM can store its long-term memory: model weights and external file system. 

External file system involves tool calls that can read from and write to external files. OpenAI's API already supports external files (https://platform.openai.com/docs/api-reference/files), but the model has not learned to use this feature as long-term memory yet. In this blog, I will use prompting techniques to make the model learn this.

TODO: the text above was copied from sft.md

evaluation on [MRCR](https://contextarena.ai/?needles=8), and at least one other dataset, to avoid severe overfitting. 