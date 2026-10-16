---
title: "2026 Complete, Sound, and Scalable Identification of Minimal Failure-Causing Schema (TOSEM'26)"
---

# Complete, Sound, and Scalable Identification of Minimal Failure-Causing Schema

这篇工作解决的是一个很小众的问题：组合测试的故障定位。组合测试把被测系统看成一堆参数，每个参数能取若干值，一个 test-case 就是所有参数各取一个值拼成的组合；所谓故障定位，就是在某个 failing test-case 里，找出究竟是哪几个参数取值的组合导致了失败，其中最小的这种组合就叫 MFS[^Nie2011Minimal]（Minimal Failure-Causing Schema）。这年头做组合测试的人已经不多了，组合测试故障定位就更少了，~~所以我们打算把这个问题做完就跑路，不碰组合测试了~~。

不过，我们觉得论文的受众倒没那么窄：这篇论文的核心其实是一个**单调性下的 Delta Debugging** 问题，而 Delta Debugging 在 Debugging 领域算是核心问题之一。

## 背景：Delta Debugging

Delta Debugging 的输入是一个 failing test-case $T_0 = \{1,2,\dots,n\}$，目标是要找到一个很小的 failing test-case $T^* \subset T_0$。这个过程依赖一个 Oracle $\phi$，用来判断一个更小的 test-case 是否还能触发原来的错误：$\phi(T)=✗$ 表示还能触发（failing），$\phi(T)=✔️$ 表示不能了（passing）。

当 Oracle $\phi$ 不具备任何性质时，无论想找全局最小的解（minimum），还是只找一个局部极小的解（minimal，也就是拿掉任何元素就不再 failing 的解），最坏情况下的查询复杂度都是指数级的 $O(2^n)$。反过来，跑得快的算法又给不出什么像样的保证——比如 ddmin[^Zeller2022Simplifying] 只能保证得到的 $T^*$ 是 1-minimal 的，这个保证非常弱。而且即便全局存在多个 minimal 的解，Delta Debugging 通常也只能找出一个。

## 导读

在组合测试故障定位场景下，Oracle $\phi$ 是一个单调的函数：给定 $T_1 \subseteq T_2$，如果 $\phi(T_1)=✗$，那么 $\phi(T_2)=✗$；如果 $\phi(T_2)=✔️$，那么 $\phi(T_1)=✔️$。换句话说，一个 failing 的 test-case，它的超集一定还是 failing；一个 passing 的，它的子集一定还是 passing。有了单调性，Delta Debugging 这件事就变得可控多了。

在 TOSEM'26 这篇论文中，我们做的就是把全局所有 minimal 的解都找出来（在组合测试的语境下，就是找出所有的 MFS，也就是所谓的 Complete），并且空间复杂度也不再是 $O(2^n)$ 的——我们不需要枚举所有子集，实际开销只跟 MFS 的大小和数量有关。

虽然标题里有 Complete, Sound, Scalable 三个大词，但重点其实是 Complete 和 Scalable 的兼顾——Sound 有赖于组合测试故障定位领域一个比较常见的假设；这个假设一旦去掉，三者恐怕无法同时达到。

读这篇论文时，可以把重点放在 Approach 部分，而不是 Evaluation 部分：算法的理论性质很清晰，不看 Evaluation 也能知道它能做到 Complete 和 Sound。Evaluation 主要回答的是 Scalability 的问题——这个算法能不能扩展到几百个参数的系统上。

## 幕后故事

这篇工作的 idea 来源于我的导师钮鑫涛，大概可以追溯到 2013 年，当时他刚刚提出了 Tuple Relation Tree[^Niu2013Identifying]。在经历大量试错之后，他隐约意识到：要找到所有的 MFS，并不需要真的把 $T_0$ 的所有子集都存下来——那可是 $O(2^n)$ 的空间。但为这个想法找到合适的形式化描述，是一件很困难的事。

这个想法一开始投 TOSEM 时有 60 页篇幅。一位审稿人认真读完了全文，也读懂了，写了整整 10 页的拒稿 PDF——他的意见是：这个 idea 本身不需要这么多形式化的篇幅来讲，presentation 还有很大的改进空间。后来导师把它拆成两部分：第一部分 Pending Schema Theory 发表在了 TSE'22[^Niu2022Theory]，第二部分就是这篇 TOSEM'26。

近十年没能推进的，其实正是"怎么把这个想法讲清楚"这一步；这篇工作里，这部分主要由我负责。比如，把问题 formulate 成 Delta Debugging 的形式——这样一来，问题本身变得更 general，不至于局限在组合测试这个小圈子里；DD 的传统表述用的是序列，但集合的记号方便得多，于是全程改用集合；此外，引入 Minimal Hitting Set Generation 来描述 NoPend 里最难理解的那部分机制。

这篇论文的 Evaluation 完成度不算高。不过这对结论的影响不大：Complete 和 Sound 是理论保证的，Evaluation 只需要回答 Scalability 这一个问题，它回答得还可以——只是也就到此为止了，所以代码的参考价值可能比较有限。做实验那会儿 DeepSeek R1 刚出来没多久，还没有 AI agent 这回事，不少代码靠手搓。ICT 这个 baseline 是一位审稿人要求加的，不过它和别的方法不太可比——它不是纯粹的故障定位，而是把覆盖表生成和故障定位揉在了一起。

## 总结

总的来说，这篇论文的 Contribution 更多是理论层面的。原先大家可能会认为解决这个问题必须要用到 $O(2^n)$ 的开销（时间 or 空间），而我们的算法在 MFS 的大小和数量受限的情况下，复杂度可以降低很多。但是我们关心的其实不是这个算法的复杂度，而是问题本身的：在一个单调 Oracle 下，找出所有的 MFS，最坏情况到底需要多少查询？严格地说，MFS 的数量自己就能随参数个数 $n$ 指数增长，所以"对 $n$ 多项式"是不可能的；有意义的问题是，把 MFS 的数量和大小也算进参数之后，复杂度还能不能做到多项式。（顺带一提，如果只找最小的一个 MFS，即使只看 $n$，答案也已经是指数级了。）这个问题我们觉得挺有意思的，只是暂时还不知道它有多重要——如果重要的话，说不定日后我们会继续往下做。

## 致谢

“查询复杂度”这个概念来源于我的本科同学徐博研。由于博研是 TCS 方向的 PhD，我便向他请教了一下这个问题，这才意识到我们关心的问题应该用查询复杂度（Oracle 查询次数）来刻画，而不是 P/NP 框架下的时间复杂度。在此向他表示感谢🙏

[^Zeller2022Simplifying]: Andreas Zeller and Ralf Hildebrandt. 2002. Simplifying and Isolating Failure-Inducing Input. *IEEE Trans. Softw. Eng.* 28, 2 (February 2002), 183–200. https://doi.org/10.1109/32.988498

[^Niu2022Theory]: X. Niu, H. Wu, C. Nie, Y. Lei and X. Wang, "A Theory of Pending Schemas in Combinatorial Testing," in IEEE Transactions on Software Engineering, vol. 48, no. 10, pp. 4119-4151, 1 Oct. 2022, https://doi.org/10.1109/TSE.2021.3113920.

[^Niu2013Identifying]: Xintao Niu, Changhai Nie, Yu Lei, and Alvin T.S. Chan. 2013. Identifying failure-inducing combinations using tuple relationship. In 2013 IEEE  Sixth International Conference on Software Testing, Verification and Validation Workshops, 271–280. https://doi.org/10.1109/ICSTW.2013.38.

[^Nie2011Minimal]: Changhai Nie and Hareton Leung. 2011. The minimal failure-causing schema of combinatorial testing. 2011 ACM Transactions on Software  Engineering and Methodology, 20, 4, 15:1–15:38. https://doi.org/10.1145/2000799.2000801.
