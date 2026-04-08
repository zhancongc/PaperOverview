# 计算机代数系统的算法实现及应用：文献综述

## 摘要
计算机代数系统（Computer Algebra Systems, CAS）是一类能够处理符号数学表达式的软件系统，它们不仅能够进行数值计算，更能执行符号运算、代数化简、微积分、方程求解等数学操作。近年来，随着计算需求的日益复杂和跨学科研究的深入，计算机代数系统在算法实现、系统架构、应用领域及与其他计算范式（如机器学习、量子计算）的融合方面取得了显著进展。本文旨在通过对近十年（2016-2025年）相关文献的系统梳理，综述计算机代数系统在核心算法实现、主要系统发展、多领域应用、技术融合以及教学实践等方面的研究现状，并展望未来的发展趋势与挑战。

## 1. 引言
计算机代数系统的核心目标是将数学推导与计算过程自动化，从而将研究者从繁琐的手工计算中解放出来，专注于更高层次的科学发现与工程设计。早期的CAS主要关注基础代数运算，而现代CAS已发展成为功能强大的综合性平台，涵盖了从抽象代数、微分几何到物理建模、工程优化的广阔领域 [1]。

文献表明，CAS的发展沿着两条主线并行：一是**算法内核的深化与优化**，致力于提升基础运算（如多项式运算、微分方程求解）的效率与鲁棒性；二是**应用领域的扩展与交叉**，将符号计算能力赋能于物理学、控制论、机器人学、人工智能等前沿学科 [2]。此外，开源运动的兴起使得如Maxima、SymPy等系统得以普及，而高性能计算的需求则催生了如HPC-GAP等面向大规模并行计算的系统 [3, 4]。

近年来，一个显著的范式转变是符号计算与**可满足性检验**、**机器学习**、**量子计算**等领域的深度融合，催生了“符号-数值混合计算”、“神经符号AI”等新方向 [5, 6, 7]。本综述将围绕算法实现、系统发展、应用实践、跨领域融合及未来展望展开，系统呈现这一领域的全貌。

## 2. 核心算法实现与优化
计算机代数系统的能力根基在于其核心算法的效率与可靠性。经典算法如Buchberger算法（用于计算Gröbner基）和LLL算法（用于格基规约）一直是研究的热点。

### 2.1 Gröbner基与Buchberger算法
Gröbner基是多项式理想理论的核心工具，广泛应用于代数几何、编码理论、密码学及机器人运动学求解。Buchberger算法是计算Gröbner基的标准算法，但其性能严重依赖于算法中**S-对选择策略**。

Peifer等人 [8] 创新性地将**强化学习**应用于Buchberger算法中的S-对选择。他们训练了一个近端策略优化（PPO）模型，针对随机二元多项式方程组学习选择策略。实验表明，在某些问题域上，该学习模型在执行的多项式加法总数上优于传统启发式方法，这证明了机器学习有潜力优化符号计算中的经典算法。这项研究为算法自动化优化开辟了新路径。

### 2.2 格基规约与LLL算法
LLL算法是首个多项式时间内计算格约化基的算法，在数论、密码学和计算机代数中应用广泛。算法的正确性与高效实现至关重要。

Bottesch等人 [9] 和Thiemann等人 [10] 分别致力于LLL算法的**形式化验证与高效实现**。Thiemann等人在Isabelle/HOL证明助手中形式化了LLL算法及其在整数多项式因式分解中的应用，确保了算法的逻辑正确性。他们实现的代码性能接近商业CAS中的实现，并且可以通过连接非受信任的快速格规约算法并验证其输出来进一步提升效率。这项工作展示了形式化方法在确保核心算法可靠性方面的价值。

### 2.3 符号积分与微分方程
符号积分与微分方程求解是CAS的基础功能。相关工作不仅关注算法本身，也关注其与机器学习的结合。Rashid Barket等人 [11] 探讨了使用**长短期记忆网络**和**树状长短期记忆网络**来选择符号积分算法，这是利用机器学习优化符号计算中算法选择的又一案例。

此外，在偏微分方程求解中，符号计算被广泛用于寻找精确解，如孤子解、怪波解等。大量研究（如 [12, 13, 14]）利用符号计算结合各种解析方法（如双线性形式、Bäcklund变换、扩展tanh方法）来求解非线性演化方程。

### 2.4 算法选择与可解释AI
随着机器学习越来越多地用于优化CAS中的算法选择（如变量排序），理解机器学习模型决策背后的逻辑变得重要。Pickering等人 [15] 研究了一个案例：利用机器学习为**柱形代数分解**选择变量排序。他们进一步使用**可解释AI**工具SHAP来分析训练好的机器学习模型，以期获得启发，设计出类似于人类专家设计的新启发式规则。这标志着从“黑箱”机器学习应用向获取可解释、可迁移的领域知识迈进了一步。

## 3. 主要计算机代数系统及其特点
计算机代数系统生态丰富多样，既有通用系统，也有面向特定领域的专用系统。表1对比了几种具有代表性的系统。

**表1：代表性计算机代数系统对比**

| 系统名称 | 主要特点 | 应用领域 | 代表文献 |
| :--- | :--- | :--- | :--- |
| **Maxima** | 历史悠久的开源通用CAS，源自MIT的Macsyma。强调符号与数值计算，具有强大的代数、微积分和矩阵运算能力，常用于教学。 | 通用数学、工程计算、数学教育 | [16, 17, 4] |
| **SymPy** | 基于Python的纯开源符号计算库。易于与其他Python科学计算库（如NumPy, SciPy）集成，社区活跃，扩展性强。 | 科学计算、物理建模、算法原型开发 | [18, 19, 20] |
| **Cadabra / Cadabra2** | 专门为张量场论问题设计的CAS。采用接近标准数学记法的输入格式，擅长处理拉格朗日量、运动方程和对称性分析。 | 广义相对论、高能物理、场论 | [21, 22] |
| **OSCAR** | 新兴的计算机代数系统，旨在整合高性能计算与现代代数、几何、数论的研究。 | 抽象代数、代数几何、高性能计算 | [23] |
| **GAP / HPC-GAP** | 专注于计算离散代数，特别是群论的CAS。HPC-GAP是其高性能版本，旨在解决大规模符号计算的并行化问题。 | 群论、组合数学、编码理论 | [3] |
| **SymForce** | 专注于机器人学的符号计算与代码生成库。基于SymPy，能自动生成优化问题的雅可比矩阵，并输出高效的C++代码。 | 机器人学、计算机视觉、运动规划、非线性优化 | [18] |

**通用系统**如Maxima和SymPy，提供了广泛的功能，是教育和科研中入门和解决常规问题的常用工具。Maxima被广泛应用于微积分和线性代数的教学，以增强学生对概念的理解 。SymPy则因其与Python生态的无缝集成，在需要结合符号计算和数值模拟的研究中备受青睐 [19]。

**领域专用系统**则针对特定学科的需求进行了深度优化。例如，Cadabra2 [21] 解决了主流CAS在处理张量场论时面临的记法和算法功能不足的问题，其设计紧密贴合理论物理学家的思维方式。SymForce  则是一个典型的**符号计算驱动代码生成**的成功案例，它将符号推导的优势（开发速度快、灵活）与生成代码的性能优势结合起来，为机器人学中的非线性优化问题提供了高效的解决方案。

**高性能计算**是另一个重要发展方向。HPC-GAP  的设计将并行性置于核心，通过新的编程抽象和领域特定的骨架模式，解决了符号计算中任务粒度不一、结构不规则带来的并行化挑战，能够在多达32,000个核心的高性能计算系统上实现良好的扩展性。

## 4. 跨学科应用领域
计算机代数系统的应用已渗透到众多科学与工程领域，极大地推动了这些领域的理论分析和计算实践。

### 4.1 物理学与工程学
物理学，尤其是引力研究和量子场论，是计算机代数最早也是最重要的应用领域之一。MacCallum [24] 综述了计算机代数在广义相对论研究中的广泛应用，包括精确解的分类、扰动计算、守恒律分析等。Cadabra2  正是为这类需求而生的工具。

在流体动力学、等离子体物理和非线性光学中，符号计算被广泛用于求解描述波传播、湍流等复杂现象的**非线性偏微分方程**。大量研究（如 [25, 26, 27, 14, 28]）利用符号计算技术寻找这些方程的精确解（如孤子解、怪波解、lump解），并分析其动力学特性。例如，Gao等人 [25, 26, 27] 在一系列工作中，系统地将符号计算方法应用于不同维度和可变系数的非线性系统，研究其在水波、等离子体、宇宙-等离子体环境中的行为。

在工程领域，符号计算用于**系统建模与优化**。Kaufmann等人 [29] 提出了一种增量式列验证方法，结合计算机代数和SAT求解器来验证算术电路。Jiang等人 [30] 将符号计算用于自治水面船舶的**非线性模型预测控制**。Martiros等人  开发的SymForce库则直接服务于机器人状态估计和运动规划。

### 4.2 人工智能与机器学习
符号计算与人工智能的融合是当前最活跃的研究方向之一，主要体现为两个层面：一是利用机器学习优化符号计算，二是构建神经符号AI系统。

**机器学习优化符号计算**：如前所述，强化学习用于优化Buchberger算法 [8]，深度学习用于选择积分算法 [11] 和变量排序 [15, 31]，Transformer模型用于加速高能物理中的振幅平方计算 [32]。这些研究都属于此类。Zotos [33] 探讨了在CAS中应用人工智能以优化其性能的多种途径。

**神经符号AI**：旨在融合神经网络强大的感知学习能力和符号系统明确的逻辑推理能力。Liang等人 [6] 在2025年的综述中，系统地回顾了这一范式的发展，介绍了可微分逻辑编程、溯因学习、程序归纳、逻辑感知Transformer等技术，旨在构建兼具学习与推理能力的通用人工智能系统。Buchberger [34] 也从自动编程的角度，分析了符号计算与机器学习作为实现算法合成的两种根本不同但又互补的途径。

此外，**超维计算**作为一种新兴的符号AI框架，利用高维分布式表示来进行随机计算和符号操作，为神经符号整合提供了新的硬件友好型实现路径 [35]。

### 4.3 形式化验证与定理证明
计算机代数系统与定理证明器的结合，对于实现**可验证的科学计算**具有重要意义。Sarma等人 [36] 指出，CAS可以作为特定领域（数学）的“预言机”，而将其与定理证明器集成，是实现“可证明安全”AI的一项具体工作。形式化验证LLL算法 [9, 10] 和算术电路 [29, 37, 38] 的成功案例，展示了这一方向的实际价值。MathCheck [39] 就是一个结合CAS和SAT求解器来辅助数学学习的早期系统。

### 4.4 密码学与编码理论
符号计算在分析密码算法的代数结构、求解编码理论中的多项式系统等方面发挥着关键作用。例如，Alm等人 [40] 使用计算机代数计算Comer关系代数在Z/pZ上的循环结构。Sayols等人 [41] 讲述了计算机代数在Goppa码和McEliece密码学中的应用。量子计算的发展也带来了新的算法，如量子算法用于有限维代数的交换性判断 [42]。

## 5. 与其他计算范式的融合与协同
计算机代数系统不再是孤立的存在，它与数值计算、可满足性检验、量子计算等范式的边界正在变得模糊。

### 5.1 符号-数值混合计算
纯粹的符号计算在处理大规模或涉及浮点数的问题时可能效率低下或不可行，而纯粹的数值计算则可能丢失问题的结构性信息并存在精度问题。符号-数值混合计算旨在结合两者优势。SNC [43] 是一个基于即时编译的云服务平台，专门用于符号-数值计算。England等人 [44] 则对比了使用符号与数值方法来计算生物网络多稳态性参数区域的可视化效果。

### 5.2 符号计算与可满足性检验
**可满足性检验**与符号计算拥有共同的兴趣，即开发算术理论的可判定过程。Abraham等人 [5, 45] 发起的SC²项目旨在加强这两个社区的联系。Bright等人 [7] 进一步探讨了当可满足性求解遇上符号计算时所产生的科学。具体应用包括：Zulkoski等人 [46] 结合SAT求解器和CAS来验证组合猜想；Bright等人 [47] 通过计算机代数和程序化SAT搜索来寻找复Golay对；Fontaine等人 [48] 成功地将计算机代数封装用于非线性SMT问题。

### 5.3 量子计算中的代数基础
量子计算本质上是基于线性代数和酉变换的计算。量子算法的发展离不开代数工具的支持。Coles等人 [49] 为初学者介绍量子算法实现。Low等人 [50] 提出了量子本征值处理框架，用于处理非正规矩阵的本征值。Kerenidis等人 [51] 提出了用于无监督机器学习的q-means量子算法。Nguyen等人 [52] 则探讨了如何通过MAGMA计算代数系统来模拟量子计算。这些研究显示，代数系统既是设计和描述量子算法的语言，也是模拟和验证量子算法的重要工具。

## 6. 数学教育与知识传播
计算机代数系统在教育中的应用效果和模式是另一个研究热点。大量研究探讨了CAS在增强学生概念理解、提升学习动机和成绩方面的作用。

Tamur等人 [53] 对过去十年基于CAS的数学学习进行了**元分析**，综合了31篇文章中的36个效应值。结果表明，使用CAS对学生的数学能力有显著的大型积极影响（效应值ES=0.89）。调节因素分析显示，CAS的使用效果因教育水平和CAS类型的不同而有所差异。

具体实践方面，Karjanto等人  推广在微积分和线性代数教学中采用开源的Maxima系统。Z. Pardos等人 [54] 则进行了一项开创性研究，比较了ChatGPT生成的代数提示与人类导师生成的提示在学习收益上的差异。虽然70%的ChatGPT提示通过了质量检查，且两者都产生了积极的学习收益，但人类导师提示产生的学习收益在统计学上显著更高。这项研究揭示了大型语言模型在教育辅助方面的潜力与当前局限。

此外，针对特殊需求群体，如视障学生，研究人员开发了CASVI [55, 56] 和IrisMath [57] 等盲文友好的计算机代数系统，体现了技术的包容性。

## 7. 挑战与未来方向
尽管计算机代数系统取得了巨大成功，但仍面临诸多挑战，同时也孕育着新的发展方向。

### 7.1 核心挑战
1.  **算法效率与可扩展性**：许多符号算法具有很高的计算复杂性（如指数级或超指数级）。处理大规模问题时，如何设计更高效的算法或有效利用并行计算资源，仍然是一个根本性挑战 。
2.  **稳健性**：符号计算中，表达式膨胀、病态问题处理、算法终止性判断等都是棘手问题。Sarma等人 [36] 将构建健壮的CAS视为实现可控AI预言机的基础。
3.  **易用性与可及性**：降低CAS的使用门槛，使其能被更广泛的科研人员和学生所掌握，包括为残障人士提供无障碍访问 [55]。
4.  **集成与互操作性**：如何让不同的CAS、以及CAS与数值库、AI框架、定理证明器等工具更流畅地协同工作，减少数据转换和接口开发的成本。

### 7.2 未来研究方向
1.  **AI驱动的符号计算**：未来，机器学习将更深入地融入CAS的各个层面，从算法选择、启发式规则发现，到自动公式推导和猜想生成 [34, 31]。可解释AI将帮助人类从机器学习模型中提取新的数学洞察。
2.  **神经符号AI的深度融合**：探索更强大的架构，将神经网络的模式识别能力与符号系统的逻辑推理能力无缝结合，解决需要认知与推理的复杂问题 。
3.  **云原生与高性能计算**：随着云计算和异构计算架构的普及，开发能动态调度和高效利用云上CPU、GPU、乃至量子计算资源的CAS平台将成为趋势 [43]。
4.  **领域特定语言与自动代码生成**：像SymForce  所展示的，将高层次的符号描述自动转化为针对特定硬件优化的低级代码，这一范式将在更多工程领域（如控制、金融建模）得到应用。
5.  **形式化验证的普及**：随着对计算可靠性要求的提高，将关键算法和计算过程进行形式化验证，并与CAS集成，将成为高保证系统（如航空航天、安全协议）的必备要求 。

## 8. 结论
本文系统回顾了计算机代数系统在算法实现与应用方面的近期进展。核心算法的优化，特别是通过机器学习方法的增强，正在持续提升CAS的效率与智能化水平。通用与领域专用的CAS共同构成了一个多样化的生态系统，服务于从基础数学到前沿物理、从机器人工程到人工智能的广阔领域。

一个显著的趋势是，计算机代数系统正从传统的独立工具演变为**跨范式计算生态中的关键组件**。它与数值计算、可满足性检验、定理证明、机器学习和量子计算的融合，不仅解决了各自领域的瓶颈问题，也催生了如神经符号AI、可验证计算等新兴交叉学科。

展望未来，计算机代数系统的发展将在追求更高性能、更强稳健性的同时，更加注重**智能化**、**协同化**和**普适化**。通过与人工智能技术的深度结合，CAS有望从“计算器”进化为“研究助手”，在科学发现和工程创新的自动化进程中扮演更为核心的角色。持续关注并投入这一领域的研究，对于推动整个计算科学和相关学科的发展具有至关重要的意义。



## References

[1] Bruno Salvy, "SYMBOLIC COMPUTATION", Applied Numerical Methods Using Matlab®, 2020. DOI: 10.1002/9781119626879.app7

[2] V. Gerdt, Wolfram Koepf, and Werner M. Seiler, "Computer Algebra in Scientific Computing", Lecture Notes in Computer Science, 2018. DOI: 10.1007/978-3-319-99639-4

[3] R. Behrends, K. Hammond, and V. Janjić, "HPC‐GAP: engineering a 21st‐century high‐performance computer algebra system", Concurrency and Computation: Practice and Experience, 2016. DOI: 10.1002/cpe.3746

[4] N. Karjanto and H. S. Husain, "Adopting Maxima as an Open-Source Computer Algebra System into Mathematics Teaching and Learning", 2017. DOI: 10.1007/978-3-319-62597-3_128

[5] E. Ábrahám, J. Abbott, and B. Becker, "Satisfiability Checking meets Symbolic Computation (Project Paper)", in International Conference on Intelligent Computer Mathematics, 2016. DOI: 10.1007/978-3-319-42547-4_3

[6] Baoyu Liang, Yucheng Wang, and Chao Tong, "AI Reasoning in Deep Learning Era: From Symbolic AI to Neural–Symbolic AI", Mathematics, 2025. DOI: 10.3390/math13111707

[7] Curtis Bright, I. Kotsireas, and Vijay Ganesh, "When satisfiability solving meets symbolic computation", in Communications of the ACM, 2022. DOI: 10.1145/3500921

[8] Dylan Peifer, M. Stillman, and Daniel Halpern-Leistner, "Learning selection strategies in Buchberger's algorithm", in International Conference on Machine Learning, 2020

[9] R. Bottesch, Max W. Haslbeck, and René Thiemann, "A Verified Efficient Implementation of the LLL Basis Reduction Algorithm", Logic Programming and Automated Reasoning, 2018. DOI: 10.29007/xwwh

[10] René Thiemann, R. Bottesch, and Jose Divasón, "Formalizing the LLL Basis Reduction Algorithm and the LLL Factorization Algorithm in Isabelle/HOL", Journal of Automated Reasoning, 2020. DOI: 10.1007/s10817-020-09552-1

[11] Rashid Barket, Matthew England, and Jurgen Gerhard, "Symbolic Integration Algorithm Selection with Machine Learning: LSTMs vs Tree LSTMs", arXiv preprint arXiv:2404.14973, 2024. DOI: 10.48550/arXiv.2404.14973

[12] Jingyuan Yang and W. Ma, "Lump solutions to the BKP equation by symbolic computation", International Journal of Modern Physics B, 2016. DOI: 10.1142/S0217979216400282

[13] Zhaqilao, "A symbolic computation approach to constructing rogue waves with a controllable center in the nonlinear systems", Comput. Math. Appl., 2018. DOI: 10.1016/j.camwa.2018.02.001

[14] Ihsanullah Hamid and Sachin Kumar, "Symbolic computation and Novel solitons, traveling waves and soliton-like solutions for the highly nonlinear (2+1)-dimensional Schrödinger equation in the anomalous dispersion regime via newly proposed modified approach", Optical and Quantum Electronics, 2023. DOI: 10.1007/s11082-023-04903-9

[15] Lynn Pickering, Tereso Del Rio Almajano, and M. England, "Explainable AI Insights for Symbolic Computation: A case study on selecting the variable ordering for cylindrical algebraic decomposition", arXiv preprint, 2023. DOI: 10.1016/j.jsc.2023.102276

[16] A. Öchsner and R. Makvandi, "Maxima—A Computer Algebra System", Finite Elements Using Maxima, 2019. DOI: 10.1007/978-3-030-17199-5_2

[17] N. Karjanto and H. S. Husain, "Not another computer algebra system: Highlighting wxMaxima in calculus", arXiv preprint, 2021. DOI: 10.3390/math9011317

[18] Hayk Martiros, Aaron Miller, and Nathan Bucki, "SymForce: Symbolic Computation and Code Generation for Robotics", arXiv preprint, 2022. DOI: 10.15607/RSS.2022.XVIII.041

[19] F. Kamalov, David Santandreu, and Ho-Hon Leung, "Leveraging computer algebra systems in calculus: a case study with SymPy", in 2023 IEEE Global Engineering Education Conference (EDUCON), 2023. DOI: 10.1109/EDUCON54358.2023.10125196

[20] J. Stewart, "SymPy: A Computer Algebra System", 2017. DOI: 10.1017/9781108120241.009

[21] K. Peeters, "Cadabra2: computer algebra for field theory revisited", J. Open Source Softw., 2018. DOI: 10.21105/JOSS.01118

[22] Dmitry S. Kulyabov, A. V. Korolkova, and L. A. Sevastyanov, "New Features in the Second Version of the Cadabra Computer Algebra System", Programming and Computer Software, 2019. DOI: 10.1134/S0361768819020063

[23] "The Computer Algebra System OSCAR", Algorithms and Computation in Mathematics, 2025. DOI: 10.1007/978-3-031-62127-7

[24] M. MacCallum, "Computer algebra in gravity research", Living Reviews in Relativity, 2018. DOI: 10.1007/s41114-018-0015-6

[25] Xin-Yi Gao, Yongjiang Guo, and Wen-Rui Shan, "Water-wave symbolic computation for the Earth, Enceladus and Titan: The higher-order Boussinesq-Burgers system, auto- and non-auto-Bäcklund transformations", Appl. Math. Lett., 2020. DOI: 10.1016/j.aml.2019.106170

[26] Xin-Yi Gao, "In plasma physics and fluid dynamics: Symbolic computation on a (2+1)-dimensional variable-coefficient Sawada-Kotera system", Appl. Math. Lett., 2024. DOI: 10.1016/j.aml.2024.109262

[27] Xin-Yi Gao, "Symbolic Computation on a (2+1)-Dimensional Generalized Nonlinear Evolution System in Fluid Dynamics, Plasma Physics, Nonlinear Optics and Quantum Mechanics", Qualitative Theory of Dynamical Systems, 2024. DOI: 10.1007/s12346-024-01045-5

[28] Yuan Shen, B. Tian, and Tian-Yu Zhou, "In nonlinear optics, fluid dynamics and plasma physics: symbolic computation on a (2+1)-dimensional extended Calogero–Bogoyavlenskii–Schiff system", The European Physical Journal Plus, 2021. DOI: 10.1140/epjp/s13360-021-01323-0

[29] Daniela Kaufmann, Armin Biere, and Manuel Kauers, "Incremental column-wise verification of arithmetic circuits using computer algebra", Formal Methods in System Design, 2019. DOI: 10.1007/s10703-018-00329-2

[30] Xiaoyong Jiang, Langyue Huang, and Mengle Peng, "Nonlinear model predictive control using symbolic computation on autonomous marine surface vehicle", Journal of Marine Science and Technology, 2021. DOI: 10.1007/s00773-021-00847-5

[31] Tereso del R'io and Matthew England, "Lessons on Datasets and Paradigms in Machine Learning for Symbolic Computation: A Case Study on CAD", Mathematics in Computer Science, 2024. DOI: 10.1007/s11786-024-00591-0

[32] Abdulhakim Alnuqaydan, S. Gleyzer, and H. Prosper, "SYMBA: symbolic computation of squared amplitudes in high energy physics with machine learning", Machine Learning: Science and Technology, 2022. DOI: 10.1088/2632-2153/acb2b2

[33] K. Zotos, "Computer Algebra Systems & Artificial Intelligence", BRAIN. Broad Research in Artificial Intelligence and Neuroscience, 2024. DOI: 10.18662/brain/15.2/584

[34] B. Buchberger, "Automated programming, symbolic computation, machine learning: my personal view", Annals of Mathematics and Artificial Intelligence, 2023. DOI: 10.1007/s10472-023-09894-7

[35] M. Heddes, Igor Nunes, and T. Givargis, "Hyperdimensional computing: a framework for stochastic computation and symbolic AI", Journal of Big Data, 2024. DOI: 10.1186/s40537-024-01010-8

[36] G. Sarma and Nick J. Hay, "Robust Computer Algebra, Theorem Proving, and Oracle AI", Informatica (Slovenia), 2017. DOI: 10.2139/SSRN.3038545

[37] Daniela Kaufmann and Armin Biere, "Improving AMulet2 for verifying multiplier circuits using SAT solving and computer algebra", International Journal on Software Tools for Technology Transfer, 2023. DOI: 10.1007/s10009-022-00688-6

[38] Alireza Mahzoon, Daniel Große, and Christoph Scholl, "Formal Verification of Modular Multipliers using Symbolic Computer Algebra and Boolean Satisfiability", in 2022 59th ACM/IEEE Design Automation Conference (DAC), 2022. DOI: 10.1145/3489517.3530605

[39] Edward Zulkoski, Vijay Ganesh, and K. Czarnecki, "MathCheck: A Math Assistant via a Combination of Computer Algebra Systems and SAT Solvers", CADE, 2016. DOI: 10.1007/978-3-319-21401-6_41

[40] Jeremy F. Alm and Andrew Ylvisaker, "A fast coset-translation algorithm for computing the cycle structure of Comer relation algebras over Z/pZ", Theor. Comput. Sci., 2017. DOI: 10.1016/J.TCS.2019.05.019

[41] N. Sayols and S. Xambó-Descamps, "Computer Algebra Tales on Goppa Codes and McEliece Cryptography", Mathematics in Computer Science, 2019. DOI: 10.1007/s11786-019-00444-1

[42] E. Combarro, J. Ranilla, and I. F. Rúa, "A Quantum Algorithm for the Commutativity of Finite Dimensional Algebras", in IEEE Access, 2019. DOI: 10.1109/ACCESS.2019.2908785

[43] P. Zhang, Yueming Liu, and Meikang Qiu, "SNC: A Cloud Service Platform for Symbolic-Numeric Computation Using Just-In-Time Compilation", in IEEE Transactions on Cloud Computing, 2018. DOI: 10.1109/TCC.2017.2656088

[44] M. England, Hassan Errami, and D. Grigoriev, "Symbolic Versus Numerical Computation and Visualization of Parameter Regions for Multistationarity of Biological Networks", arXiv preprint, 2017. DOI: 10.1007/978-3-319-66320-3_8

[45] E. Ábrahám, J. Abbott, and B. Becker, "Satisfiability checking and symbolic computation", in ACM Commun. Comput. Algebra, 2016. DOI: 10.1145/3055282.3055285

[46] Edward Zulkoski, Curtis Bright, and A. Heinle, "Combining SAT Solvers with Computer Algebra Systems to Verify Combinatorial Conjectures", Journal of Automated Reasoning, 2016. DOI: 10.1007/s10817-016-9396-y

[47] Curtis Bright, I. Kotsireas, and A. Heinle, "Complex Golay Pairs up to Length 28: A Search via Computer Algebra and Programmatic SAT", arXiv preprint, 2019. DOI: 10.1016/j.jsc.2019.10.013

[48] P. Fontaine, Mizuhito Ogawa, and T. Sturm, "Wrapping Computer Algebra is Surprisingly Successful for Non-Linear SMT", SC-Square@FLOC, 2018

[49] Patrick J. Coles, S. Eidenbenz, and S. Pakin, "Quantum Algorithm Implementations for Beginners", in ACM Transactions on Quantum Computing, 2018. DOI: 10.1145/3517340

[50] Guang Hao Low and Yuan Su, "Quantum Eigenvalue Processing", in 2024 IEEE 65th Annual Symposium on Foundations of Computer Science (FOCS), 2024. DOI: 10.1109/FOCS61266.2024.00070

[51] Iordanis Kerenidis, Jonas Landman, and Alessandro Luongo, "q-means: A quantum algorithm for unsupervised machine learning", Neural Information Processing Systems, 2018

[52] Binh Duc Nguyen, "Simulation of Quantum Computation via MAGMA Computational Algebra System", International Journal of Advanced Trends in Computer Science and Engineering, 2020. DOI: 10.30534/ijatcse/2020/130922020

[53] M. Tamur, Y. S. Ksumah, and D. Juandi, "A Meta-Analysis of the Past Decade of Mathematics Learning Based on the Computer Algebra System (CAS)", in Journal of Physics: Conference Series, 2021. DOI: 10.1088/1742-6596/1882/1/012060

[54] Z. Pardos and Shreya Bhandari, "Learning gain differences between ChatGPT and human tutor generated algebra hints", arXiv preprint arXiv:2302.06871, 2023. DOI: 10.48550/arXiv.2302.06871

[55] Paúl Mejía, L. Martini, and Felipe Grijalva, "CASVI: Computer Algebra System Aimed at Visually Impaired People. Experiments", in IEEE Access, 2021. DOI: 10.1109/ACCESS.2021.3129106

[56] Paúl Mejía, L. Martini, and J. Larco, "CASVI: A Computer Algebra System Aimed at Visually Impaired People", in International Conference on Computers for Handicapped Persons, 2018. DOI: 10.1007/978-3-319-94277-3_89

[57] A. Zambrano, Danilo Pilacuan, and Mateo N. Salvador, "IrisMath: A Blind-Friendly Web-Based Computer Algebra System", in IEEE Access, 2023. DOI: 10.1109/ACCESS.2023.3281761