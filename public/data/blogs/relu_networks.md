In the past few weeks, I've been thinking increasingly about basic neural networks, such as one composed of linear and ReLU layers.

It's hard to understand what exactly the network is doing, or why it works. A network with only linear and ReLU layers seems very constrained in its capacity, yet the [Universal Approximation Theorem](https://en.wikipedia.org/wiki/Universal_approximation_theorem) says that a 2-layer network can approximate any function arbitrarily well given enough neurons in the hidden layer.

To resolve this conflict in my understanding of neural networks, I went on a journey to understand them a bit more.

# ReLU networks can sort the input

Sorting is a highly nonlinear function, but it's possible for a neural network to sort the input.

When there are only two numbers in the input, we can compute the max as follows:

$$\max(a,b) = b + \text{ReLU}(a-b)$$

If a is larger than b, then $b + \text{ReLU}(a-b) = b + (a-b) = a$.\
If b is larger than a, then $b + \text{ReLU}(a-b) = b + 0 = b$.

We can compute the min as:

$$\min(a,b) = a + b - \max(a,b) = a + b - (b + \text{ReLU}(a-b)) = a - \text{ReLU}(a-b)$$

By computing the min and the max, we essentially sorted the input with two numbers.

We can easily extend this to 3 dims, where we use $\max(\max(a,b),c)$ to compute the max, $\min(\min(a,b),c)$ to compute the min, and $\text{mid} = a + b + c - \max - \min$.

In general, such a network is called a [sorting network](https://en.wikipedia.org/wiki/Sorting_network). We can naively use a $O(n^2)$ algorithm such as bubble sort, where we find the max among all elements, and then find the max among the remaining elements, and so on. There are also specialized algorithms such as bitonic sort, with $O(n\log^2(n))$ runtime complexity.

# ReLU networks can produce common shapes

We've seen how ReLU can be used to compute $\max(a,b)$, but how about $\text{clip}(x,a,b) = \min(b, \max(a,x))$? We can chain two ReLUs, but we can also use two ReLUs in parallel as follows:

$$\text{ReLU}(x-a) + a - \text{ReLU}(x-b)$$

<img src="/data/images/relu1.png" width="400" alt="relu1">

With two clip functions in parallel, we can create shapes like buckets and triangles.

<img src="/data/images/relu2.png" width="400" alt="relu2">

We can also increase the slope inside the clip to create an approximation to the discontinuous function $\text{Indicator}(x \ge 0)$.

<img src="/data/images/relu3.png" width="400" alt="relu3">

To create crazier shapes, check out this [Jane Street blog](https://blog.janestreet.com/visualizing-piecewise-linear-neural-networks/) where they used ReLU networks to create their logo.

# LeakyReLU and the zero gradient problem

<img src="/data/images/relu4.png" width="400" alt="relu4">

If our linear layer is a Gaussian distribution with zero mean, then about half of the elements in the output will be negative. Because of ReLU, the weights responsible for negative outputs will receive zero gradients in the backward pass. To alleviate this problem, we can use:

$$\text{LeakyReLU}(x) = \max(\alpha x, x)$$

This way, all weights will get nonzero gradients.