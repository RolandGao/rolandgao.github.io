1. An optimizer that always works
    1. Minimizes the loss function without any hyper parameters 
2. Efficient video understanding
    1. Essentially solving the long context problem
    2. Constant memory, constant disk. The model has to keep on compressing to meet the constant memory constraint.
    3. Memory could be the hidden state in RNN, or in the weights like in test time training. 
    4. Disk is queried using RAG. Conceptually, agentic AI can go to the queried time in a video player, or navigate to any file in any folder. 
        1. AI outputs “Go to time 1m20s in the video”, and then the future input tokens would be the frames of the video starting at 1m20s. The model would output nothing at first, looking at the video, until it eventually gives another instruction.
3. Good RL algorithm that can achieve superhuman in Go, StarCraft, math, and code
    1. Some combination of deep seek r1 and the classical RL in Go and StarCraft
4. RL environments with proper reward functions.
    1. Agents is an application of 4
    2. An example RL environment is using the computer, where it gets a reward if it achieves some specified task. 
    3. Robotics is also an application of 4.
    4. The environment is the real world, where the reward is some specified task such as moving some object, cleaning the house, or cooking a meal. Touching someone without consent would be a negative reward.

Lingering questions
1. How does the model learn continuously?
    1. Is it really possible that all the learning is in the hidden states in RNN, without changes to the weights?
        1. Probably not, humans have only one continuous training stage; while models have the train stage and the inference stage. How to make models have one continuous training stage?
        2. The solution is possibly some continuous update of the weights and also the hidden states.
2. If I tell the model to read a book, does it learn as much as humans do?
    1. It can probably memorize more of it, but does it understand as much?
    2. Next token prediction is clearly not enough, especially in math textbooks.
    3. In a math textbook, the model needs to come up with its own train set with questions and answers. Textbook problems can be easily converted, but expositions (implicit problems) can be harder to convert.
        1. Then it can do RL to learn from it.
        2. The model needs to specify when to learn and when to not learn.
            1. For example, when it’s converting the dataset into Q and A and trying 100 CoT paths on a problem and verifying if the CoT answer is correct, it’s only doing inference. Then, it can do the actual learning to teach itself to have the specified output given some input. Basically deepseek R1 but the learning structure and when to learn is decided by the model itself instead of manually set up. Model’s decision to do gradient descent can be implemented as a function call.
3. If AI can solve all the previous problems, perhaps it can learn from data as efficiently as humans. If it still cannot, we have to keep on iterating to close this gap. 
    1. Even if AI cannot learn as efficiently, it can still achieve super human intelligence by using significantly more data and compute than humans.
    2. But if the AI can learn as efficiently, its intelligence will be even more super human than before.
    3. In fact, we could define the intelligence quotient as the data and compute efficiency. And intelligence = intelligence quotient x data x compute.
