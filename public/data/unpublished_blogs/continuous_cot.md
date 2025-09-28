The rise of RNN in the era of test-time compute.


residual connection and drop block might be similar. Attention introduces multiplicatively many residual connections. Maybe that's one reason why attention is so good.

think a bit more about how SFT and RL actuall works at the backprop level.

continuous CoT converts RL to SFT

SFT might be bad. There are many was to say the same thing, and SFT cares more about the way the model responds than the answer actually being right. because the answer token might just be one token while there are tons of filler words. Or, the answer is the embedding of the entire sentence instead of a token, and who knows how much the model will learn in this case. 

RL actually solves this SFT problem, because RL cares about the accuracy of the answer more than the style of the answer.

RNN can be fed think tokens to be deep, while transformer needs the output to be fed into the input. RL is discrete while continuous CoT is continuous. 

RNN with think token can be sampled multiple times, each time having different number of think tokens. this is because the think token doesn't have prob 1.0. Obviously, think tokens have to end so that the model can actually answer the quesiton and terminate. We can reward models with fewer think tokens to make the model more efficient.

Transformer can also be fed with think tokens, but it's not as effective, because the compute gets wider instead of deeper. without think tokens, transformer can actually get deeper but with bottleneck at the token space. We can try to make transformer compute deeper:
1. attend to all layers of previous tokens instead of just the same layer. 
2. attend to all layers of the previous token in addition to the same layer of previous tokens.

what if tool call to allocate a certain number of tokens for continuous CoT. 

continuous CoT has the problem that the output of the last layer and the input to the first layer have different distributions. Transformer is going to be humongously confused. 

continuous CoT is really just a RNN.
VLA is better as RNN: takes an input image frame at every time step and outputs text.


Human as a sequential vector-to-vector model. VLA model. 
input vector contains image, audio, touch, smell, taste. image is the most important; audio and touch are the second most important. 
output vector contains the force vector for each muscle. 

How about text? native text would simplify things. input text can be in image and audio. output text can be the action of movement that represents hand writing for keyboard click. But I think otuput text can be just the output vector, and let's forget muscle vectors for the moment. muscle vectors are very general and unnecessary for many tasks, especially computer tasks. 

What kind of model architecture is best for sequential vector-to-vector? maybe transformer, but I'm not so sure. video-to-text is much harder than text-to-text, because video contains much more information than text. After figuring out video-to-text architecture, we can reapply this more general architecture to text-to-text, and it will just work, better than tranformer.

transformer actually works for video understanding, as shown by gemini 2.5 pro's video understanding results. 

transformer is best for pretraining, but how does the training for video understanding look like? If the setting is an agent in a simulation or video game, a lot fo times, the agent will be taking in the video frames without outputing anything. 

memory storage system as tool call. call a tool to get or set the text on the scratchpad. solves the long context problem.

if humans can remember only 7 things, how does a human remember a movie or a book? 
answer: https://chatgpt.com/share/689bd71d-67a8-8011-bcd9-b0cb45246b54

hypothesis: workable memory vs encoded memory. a workable vector can turn into an encoded vector for more efficient storage. When we need to manipulate the vector again, we have to decode into the workable vector again. reminds me of MobileNet. also, number in binary versus one-hot encoding.

can AI take naps?

vector vs text. 59 and 61 are very different in text space but very close in vector space. every entry in the vector decides the action of every muscle. 

VLA: https://github.com/openvla/openvla

Flexible Thinking Pretraining: https://docs.google.com/document/d/1bZQcF9-AU0SZ1nIKSDg56OXV38kuIcKfbWpw_U4Mndo/edit?tab=t.0