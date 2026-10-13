---
title: An Introduction to My Work
---

# An Introduction to My Work

## [OOPSLA'26](https://doi.org/10.1145/3839516)

**幕后故事.** 这篇工作的历史悠久，可以追溯到2021年。

## [TOSEM'26](https://doi.org/10.1145/3811916)

这篇工作解决的是一个很小众的问题：组合测试的故障定位。这年头做组合测试的人已经不多了，组合测试故障定位就更少了，所以我们打算把这个问题做完就跑路，不碰组合测试了（bushi）。

不过，这篇文章的受众倒也不会那么窄，因为我们把这个问题 formalize 成单调性下的 Delta Debugging 问题，而 Delta Debugging 问题可以说是 Debugging 领域的一个核心问题。

### Delta Debugging

Delta Debugging的输入是一个failing test-case $T_0 = \{1,2,\dots,n\}$，然后目标是要找到一个很小的failing test-case $T^* \subset T_0$。这个过程需要依赖一个Oracle $\phi$ 来判断一个test-case是否保持了failure。如果 $\phi(T)=✔️$，则不保持（passing）；如果 $\phi(T)=❌$，则保持了failure（failing）。

在没有任何性质的保证下，Delta Debugging几乎无法为解得到什么性质保障。ddmin可以保证最终得到的$T^*$是1-minimal的，而不是真正的minimal。此外，Delta Debugging通常是只能得到一个解，即使全局有多个minimal的解。

### 单调性

在组合测试故障定位场景下，Oracle $\phi$是一个单调的函数：给定 $T_1 \subseteq T_2$，如果$\phi(T_1)=❌$，那么 $\phi(T_2)=❌$；如果 $\phi(T_2)=✔️$，那么 $\phi(T_1)=✔️$。

有了这个性质，Delta Debugging 就可以做出很好的结果了。我们这篇文章要做的就是把所有 minimal 的 $T^*$ 都找出来。

### 导读

虽然这篇工作的标题中有 Complete, Sound, Scalable 三个大词，不过重点还是在于 Complete 和 Scalable 的平衡，因为Sound其实是依赖于组合测试故障定位领域一个比较常见的假设，如果把这个假设去掉，恐怕这三者想要同时达到就不大可能了。

读者在阅读这篇文章的时候可以把重点放在 Approach 部分而不是 Evaluation 部分，因为算法的理论性质很清晰，不需要Evaluation也能知道算法可以做到 Complete 和 Sound。Evaluation 更多是看一下 Scalability，也就是这个算法是否能扩展到几百个参数的 SUT 上。

### 幕后故事

这篇工作的 idea 来源于我的导师钮鑫涛，大概可以追溯到 2013 年，当时他刚刚发表了 [Tuple Relation Tree](http://ieeexplore.ieee.org/document/6571643/) 这篇工作。当时他经过很多尝试，他已经大概意识到了为了找到多个 minimal 的 $T^*$，我们并不需要真的把 $T_0$ 的所有子集都存下来。但是为这个想法找到合适的形式化描述是一件很困难的事情。发表在TSE'22上的 [Pending Schema Theory](https://ieeexplore.ieee.org/document/9543605/) 往前迈了一大步，但是符号上还是很难理解。

TOSEM'26 做的事情就是把这个形式化描述搞定，

### 未来工作
