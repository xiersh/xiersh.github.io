---
title: "2026 Complete, Sound, and Scalable Identification of Minimal Failure-Causing Schema (TOSEM'26)"
---

# Complete, Sound, and Scalable Identification of Minimal Failure-Causing Schema

这篇工作解决的是一个很小众的问题：组合测试的故障定位。这年头做组合测试的人已经不多了，组合测试故障定位就更少了，~~所以我们打算把这个问题做完就跑路，不碰组合测试了~~。

不过，这篇文章的受众倒也不会那么窄，因为我们把这个问题 formalize 成单调性下的 Delta Debugging 问题，而 Delta Debugging 问题可以说是 Debugging 领域的一个核心问题。

## 背景：Delta Debugging

Delta Debugging 的输入是一个 failing test-case $T_0 = \{1,2,\dots,n\}$，然后目标是要找到一个很小的 failing test-case $T^* \subset T_0$。这个过程需要依赖一个 Oracle $\phi$ 来判断一个 test-case 是否保持了目标错误。如果 $\phi(T)=✔️$，则不保持（passing）；如果 $\phi(T)=✗$，则保持了目标错误（failing）。

当Oracle $\phi$ 没有任何性质时，找到全局最小的解（minimum），甚至找一个局部极小的解（minimal），在最坏情况下只能是指数级的查询复杂度 $O(2^n)$。而一个运行速度较快的 Delta Debugging 算法则几乎无法为这个解提供什么理论保证，比方说 ddmin 只能保证最终得到的$T^*$是 1-minimal 的[^Zeller2022Simplifying]，而这个保证非常弱。此外，Delta Debugging 通常是只能得到一个解，即使全局有多个 minimal 的解。

## 导读

在组合测试故障定位场景下，Oracle $\phi$是一个单调的函数：给定 $T_1 \subseteq T_2$，如果$\phi(T_1)=✗$，那么 $\phi(T_2)=✗$；如果 $\phi(T_2)=✔️$，那么 $\phi(T_1)=✔️$。有了这个性质，Delta Debugging 就可以做出很好的结果了。在TOSEM'26这篇文章中，我们做的就是把全局所有的 minimal 的解都找出来（也就是所谓的Complete），并且空间复杂度，不会像已有工作那样完完全全是$O(2^n)$的空间复杂度。

虽然这篇工作的标题中有 Complete, Sound, Scalable 三个大词，不过重点还是在于 Complete 和 Scalable 的平衡，因为 Sound 其实是依赖于组合测试故障定位领域一个比较常见的假设，如果把这个假设去掉，恐怕这三者想要同时达到就不大可能了。

读者在阅读这篇文章的时候可以把重点放在 Approach 部分而不是 Evaluation 部分，因为算法的理论性质很清晰，不需要 Evaluation 也能知道算法可以做到 Complete 和 Sound。Evaluation 更多是看一下 Scalability，也就是这个算法是否能扩展到几百个参数的 SUT 上。

## 幕后故事

这篇工作的 idea 来源于我的导师钮鑫涛，大概可以追溯到 2013 年，当时他刚刚发表了 [Tuple Relation Tree](http://ieeexplore.ieee.org/document/6571643/) 这篇工作。当时他做了很多试错之后已经大概意识到了为了找到多个 minimal 的 $T^*$，我们并不需要真的把 $T_0$ 的所有子集都存下来（这个会导致 $O(2^n)$ 的空间复杂度）。但是为这个想法找到合适的形式化描述是一件很困难的事情。

这个idea一开始投 TOSEM 的时候有 60 页的篇幅，其中有一位审稿人因为篇幅过长拒掉这篇文章了。后面他把这个idea拆成两部分，第一部分 Pending Schema Theory 发表在了TSE'22[^Niu2022Theory]。第二部分就是这篇 TOSEM'26 了。我主要做的工作是简化了 Presentation，例如我把问题 formulate 成 Delta Debugging，这样我就可以使用了集合而不是序列的符号；此外我引入 Minimal Hitting Set Generation 去描述这个算法中最难理解的部分。

这篇文章的 Evaluation 完成度不是很高，当时完成这部分实验时 DeepSeek R1 刚出来没多久，还是没有 AI agent 的时代，所以代码中不少还是靠手搓的。ICT 这个 baseline 是一位审稿人要求加的，但是这个 baseline 我们觉得不是很有可比性，因为这个不是纯故障定位，而是把覆盖表生成和故障定位融合起来了。

## 总结

总的来说，这篇文章的 Contribution 更多是理论层面的。原先大家可能会认为解决这个问题必须要用到 $O(2^n)$ 的开销（时间 or 空间），而我们的算法在 minimal failing test-cases 的大小和数量受限的情况下，复杂度可以降低很多。但是这个算法的复杂度分析起来比较复杂，所以我们文章中并没能证明其复杂度是否已经降到多项式级别，或者仍然是指数级别的复杂度。如果这个问题有意思的话，说不定日后我们会继续往下做。

“查询复杂度”这个概念来源于我的本科同学徐博研。由于博研是 TCS 方向的 PhD，我便向他请教了一下这个问题，在这个过程中发现这个问题是查询问题，而不是 P/NP 问题。在此向他表示感谢🙏

[^Zeller2022Simplifying]: Andreas Zeller and Ralf Hildebrandt. 2002. Simplifying and Isolating Failure-Inducing Input. *IEEE Trans. Softw. Eng.* 28, 2 (February 2002), 183–200. https://doi.org/10.1109/32.988498

[^Niu2022Theory]: X. Niu, H. Wu, C. Nie, Y. Lei and X. Wang, "A Theory of Pending Schemas in Combinatorial Testing," in IEEE Transactions on Software Engineering, vol. 48, no. 10, pp. 4119-4151, 1 Oct. 2022, https://doi.org/10.1109/TSE.2021.3113920.
