# 计算机代数系统的算法实现及应用：文献综述

## 引言

计算机代数系统（Computer Algebra System， CAS）是一类能够进行符号数学运算的软件系统，其核心在于对数学表达式进行解析、化简、变换和求解，而不仅仅是数值计算。自20世纪60年代以来，随着计算理论和硬件的发展，CAS已从学术研究工具演变为广泛应用于科学研究、工程计算和教育领域的强大平台[1, 2]。其发展历程见证了从专用系统（如REDUCE、Macsyma）到通用商业系统（如Maple、Mathematica）和开源系统（如Maxima、SymPy）的转变，深刻地影响了数学、物理、工程和计算机科学的研究范式[3, 4]。

计算机代数系统的核心价值在于其算法实现。这些算法涵盖了多项式代数、微积分、微分方程、线性代数、数论和代数几何等众多数学分支。高效的算法是实现CAS功能性和实用性的基础，例如Gröbner基计算、符号积分、微分方程求解和矩阵运算等[5, 6]。近年来，随着计算需求的日益复杂和跨学科融合的加深，CAS的算法不断优化，其应用范围也从传统的数学物理领域扩展至人工智能、量子计算、形式验证和工程优化等新兴前沿[7, 8, 9]。

本综述旨在系统梳理计算机代数系统的核心算法实现及其在多学科领域的应用进展。首先，本文将概述CAS的核心算法与实现技术；其次，重点评述其在数学物理、工程科学、人工智能与机器学习等领域的应用成果；接着，探讨其在教育领域的作用；最后，总结当前面临的挑战并展望未来发展方向。本文引用的文献涵盖了2016年至2025年间的研究成果，力图反映该领域的最新动态。

## 1. 计算机代数系统的核心算法与实现

计算机代数系统的强大功能植根于一系列高效、精确的符号计算算法。这些算法构成了CAS的“引擎”，其设计与优化直接决定了系统的性能和应用范围。

### 1.1 符号计算基础算法

多项式代数是符号计算的基础，其中Gröbner基计算是核心算法之一，广泛应用于方程求解、几何定理证明和密码学。传统的Buchberger算法及其优化变体是计算Gröbner基的标准方法。近年来，机器学习技术被引入以优化算法中的关键步骤，例如S-对选择。Peifer等人[5]利用强化学习训练策略模型，在特定类型的二项式方程系统上，其学习到的选择策略在多项式加法总数上超越了传统启发式方法，为算法优化提供了新的思路。除了Gröbner基，线性递推关系计算也是符号求和与插值的基础。Berthomieu和Faugère[10]提出了一种基于多项式除法的算法，用于计算序列的线性递推关系理想，该算法完全基于多元多项式算术，避免了传统方法中的线性代数操作，为稀疏多项式插值等问题提供了新途径。

在矩阵计算方面，广义逆（如Drazin逆）的符号计算是线性代数中的重要问题。Sendra[11]以及Stanimirović等人[12]研究了在一般域上通过特殊化等方法符号计算广义逆的表示与算法，这些工作为处理奇异矩阵和病态系统提供了理论工具。

### 1.2 微分方程与积分计算

符号微分方程求解是CAS的标志性功能之一。针对大型常微分方程系统，紧凑且高效的雅可比矩阵符号计算是关键。Kofman等人[13]提出了在大规模ODE系统中计算紧凑稀疏符号雅可比矩阵的方法，这对基于雅可比矩阵的数值求解器（如刚性方程求解器）的效率至关重要。在积分计算领域，Raab[14]研究了参数积分的符号计算，这类积分常见于物理和工程中的特殊函数。在理论物理中，Feynman积分的计算是高能物理精确计算的核心挑战。Wu等人[15]开发的NeatIBP软件包，利用零化和模交技术生成小规模的积分-by-parts（IBP）关系，相比标准的Laporta算法能产生更紧凑的方程组，显著提升了多圈Feynman积分的约化效率。

对于特殊类型的序列和函数，算法也在不断进步。Ablinger[16]通过结合Kovacic算法求解线性微分方程，改进了计算全纯序列的逆Mellin变换的方法。Fox[17]则利用符号计算，开发了搜索Hofstadter类递归方程的线性递归解算法，发现了此类序列的无限族。

### 1.3 程序变换与自动化

除了具体的数学算法，如何将符号计算能力集成到更广泛的程序分析与验证流程中，也是一个重要方向。Lauko等人[6]提出了一种基于程序变换的符号计算方法。该方法通过编译器工具将标准程序转换为能在内部维护和操作符号值的语义等价程序，从而使得不支持符号操作的验证工具也能间接处理符号计算，简化了工具链的构造。

### 1.4 几何代数与张量计算

几何代数（Geometric Algebra, GA）提供了一种统一的数学语言来描述几何对象和变换，在计算机图形学、机器人和物理中有广泛应用。Hildenbrand[18]对几何代数计算进行了系统介绍。在实现层面，Peeters[19]开发的Cadabra2系统专门针对场论中的张量计算问题，提供了直观的输入格式和交互式笔记本界面，极大地简化了拉格朗日量处理、运动方程计算和对称性分析等任务，弥补了主流CAS在张量符号计算方面的不足。

## 2. 计算机代数系统在数学物理中的应用

数学物理是计算机代数系统最早且最深入的应用领域之一。CAS为求解复杂的非线性偏微分方程（PDE）、分析可积系统以及研究引力与场论提供了不可或缺的工具。

### 2.1 非线性偏微分方程解析解

寻找非线性PDE的精确解（如孤子、怪波和块状解）是数学物理中的核心课题。符号计算通过自动化李对称分析、双线性方法、试探函数法等，极大地推动了这个领域的发展。大量研究集中在各类可积系统上，例如：
- **Kadomtsev-Petviashvili (KP) 类方程**：Yang和Ma[20]利用符号计算求解了BKP方程的块状解。Lü等人[21]研究了扩展的KP类方程的有理解。Adem[22]结合李对称分析和扩展tanh方法，求解了耦合KP方程的精确解。
- **Boussinesq-Burgers系统**：Gao等人[23]针对高阶Boussinesq-Burgers系统，从二维Bell多项式出发构造了非自Bäcklund变换，并从Painlevé-Bäcklund格式得到了自Bäcklund变换和孤子解，并将其应用于地球、土卫二和土卫六的水波研究。
- **(2+1)维和(3+1)维系统**：Gao在一系列工作中系统地运用符号计算方法研究了多个(2+1)维变系数系统，如Sawada-Kotera系统[24]、广义非线性演化系统[25]、广义变系数Boiti–Leon–Pempinelli系统[26]以及广义色散长波系统[27]，揭示了它们在流体力学、等离子体物理和非线性光学中的应用。Kumar等人[28, 29]则求解了新的(3+1)维Painlevé可积广义非线性演化方程和KdV-BBM方程的怪波与块状解。
- **怪波与可控中心**：Zhaqilao[30]和Liu等人[31]分别提出了构造具有可控中心的怪波和寻找变系数非线性系统多怪波解的符号计算途径。

### 2.2 可积系统与对称性分析

除了求解，CAS还用于研究方程本身的可积结构和对称性。Krasil'shchik等人[32]的专著系统阐述了PDE可积结构的符号计算。Cheviakov和Cheviakov[33]开发了用于非线性物理模型等价变换和参数约简的符号计算工具。Adem等人[34]对一个广义色散水波系统进行了守恒律计算、对称约化和行波解研究，展示了符号计算在系统分析中的综合应用。

### 2.3 引力理论与场论

在广义相对论和量子场论中，涉及繁重的张量计算。MacCallum[35]综述了计算机代数在引力研究中的应用，包括精确解、摄动计算和数值相对论的准备工作。Cadabra2[19]即是专门为此领域设计的CAS。在量子电动力学等领域，Shirokov[36]展示了计算机代数在超对称电动力学计算中的应用。Korolkova等人[37]则利用空间-时间代数形式对麦克斯韦方程进行了符号研究。

### 2.4 天体力学与动力系统

CAS也被用于探索基础物理问题。Mogavero等人[38]通过计算机代数揭示了太阳系混沌的起源。在动力系统方面，Huang等人[39, 40]利用符号计算方法分析快返排斥子和微分方程定性理论，Song[41]则对Lorenz-84系统进行了定性研究。

## 3. 计算机代数系统在工程与科学计算中的应用

计算机代数系统在工程领域的应用主要体现在建模、分析、优化和验证等方面，其符号推导能力能够帮助工程师获得更深刻的理解和更可靠的设计。

### 3.1 控制系统与机器人学

在控制领域，符号计算可用于推导系统模型和设计控制器。Jiang[42]将符号计算用于自主海洋水面船的非线性模型预测控制。Do[43]提出了用于串行柔性关节机器人逆动力学的符号微分算法，提高了计算效率。在机器人运动学中，Chablat等人[44]通过计算机代数和实代数几何算法，判定机械臂的尖点性。结构分析方面，Hang[45]利用共形几何代数对并联机构进行了结构分析。

### 3.2 电路设计与形式验证

集成电路（IC）设计，特别是模拟IC设计，严重依赖于专家经验。Shi等人[46]调查了利用符号计算实现模拟IC设计自动推理的进展。在数字电路，尤其是算术电路的验证方面，符号计算与SAT求解器结合成为了强大工具。Mahzoon等人[47]使用符号计算机代数和布尔可满足性形式验证了模乘器。Kaufmann等人[48]通过结合SAT求解和计算机代数改进了AMulet2乘法器验证工具。Rao等人[49]则利用计算机代数技术对整数运算电路进行校正。Li等人[50, 51]甚至利用SAT求解器和计算机代数攻击了最小的Kochen-Specker问题。

### 3.3 科学计算与多物理场建模

在计算流体动力学（CFD）中，Cordesse[52]应用计算机代数推导了带非保守项非线性PDE系统的熵补充守恒律，用于复杂流体流动的建模与分析。Vorozhtsov等人[53]利用计算机代数手段比较了分子动力学问题中高阶差分格式的精度。
在航空航天领域，Gutnik等人[54, 55, 56, 57]系列工作应用计算机代数方法研究连接体系统在轨道或引力场中的平稳运动。Prokopenya[58, 59]则用CAS研究变质量多体问题中的演化方程。

### 3.4 优化与设计空间探索

符号计算有助于理解和优化复杂系统。Kim[60]通过集成接口利用符号计算进行复杂系统的高效设计优化。Zhao[61]提出通过自适应采样和符号计算来描述设计空间。

## 4. 计算机代数系统在人工智能与机器学习中的新兴应用

人工智能，特别是机器学习，与符号计算正经历着深刻的交叉融合，催生了神经符号计算等新范式，同时也利用CAS来增强机器学习模型的能力和可解释性。

### 4.1 从符号AI到神经符号AI

传统的符号AI基于逻辑和规则，而深度学习则在感知任务上表现出色。将两者结合的神经符号AI旨在获得兼具学习能力和推理能力的系统。Liang[62]回顾了从符号AI到神经符号AI的演进。Pisano[63]提出了一个用于可解释AI（XAI）的统一神经符号计算模型。在认知科学层面，Cho等人[64]将梯度符号计算用于句子处理的增量解析，建立了连续动力系统与离散符号结构之间的桥梁。

### 4.2 符号回归与机器学习辅助计算

符号回归旨在从数据中发现简洁的数学表达式，是机器学习与符号计算结合的典型例子。Fox[65]探讨了如何利用计算机代数系统将背景知识融入符号回归过程。Sun[66]提出了符号回归辅助的离线数据驱动进化计算。在材料科学中，Wang[67]通过维度同步计算进行符号回归，以发现材料性质的本构关系。在算法层面，Barket[68]利用长短期记忆网络（LSTM）和树LSTM来选择符号积分算法，展示了机器学习优化符号计算流程的潜力。

### 4.3 自动定理证明与形式验证

SAT（可满足性）求解器与计算机代数的结合是形式验证领域的强大组合。Ábrahám等人[69, 70]和Davenport等人[71]系统探讨了可满足性检查与符号计算的结合。Bright等人[72]也综述了这一交叉领域。Zulkoski等人[73, 74]开发了MathCheck，一个结合CAS和SAT求解器的数学助手，用于验证组合猜想和充当数学助手。在信息论中，Guo[75]利用符号计算证明信息不等式和恒等式。

### 4.4 量子计算算法实现

量子计算作为一种新的计算范式，其算法设计和模拟也受益于CAS。Kerenedis等人[8]提出了用于无监督机器学习的量子q-means算法。Coles等人[76]为初学者提供了量子算法实现的教程。Camps等人[77]给出了特定稀疏矩阵块编码的显式量子电路。Shao[78]提出了在量子计算机上计算可对角化矩阵特征值的算法。Combarro等人[79]提出了判断有限维代数交换性的量子算法。Nguyen[80]则通过MAGMA计算代数系统模拟量子计算。

## 5. 计算机代数系统在教育与可视化中的角色

计算机代数系统不仅是研究工具，也是强大的教育辅助手段，能够改变数学和工程学科的教学与学习方式，并促进教育的可及性。

### 5.1 数学教育辅助工具

大量研究探讨了CAS在数学教学中的效果和应用模式。Tamur等人[81]对过去十年基于CAS的数学学习进行了元分析，总体肯定了其积极影响。具体应用包括：
- **微积分与线性代数**：Kamalov等人[82]通过案例研究展示了在微积分课程中利用SymPy带来的成绩显著提升。Karjanto[83]通过结合SageMath和免费电子书，在翻转课堂中教授线性代数。
- **微分方程**：Zeynivandnezhad[84]探讨了在微分方程中运用CAS来阐释数学思维。Lohgheswary[85]讨论了将CAS纳入微分方程教学大纲。
- **特定数学分支**：Olenev[86, 87]展示了使用Maple CAS教授数学归纳法、集合论和组合学基础。Velychko[88]探讨了在未来数学教师培训过程中使用Maxima。
- **动态几何与证明**：Hasek[89]将动态几何软件辅以CAS作为证明工具。Brown[90]则探讨了CAS是否准备好用于课堂中几何不等式的猜想与证明。

### 5.2 可视化、可访问性与系统开发

对于视觉障碍学习者，CAS的可访问性至关重要。Mejía等人[91, 92]和Zambrano[93]分别开发了面向视障人士的CAS系统CASVI和IrisMath，并进行了实验评估。在可视化方面，Petković等人[94, 95]将符号计算和计算机图形学作为工具，用于开发和研宄新的求根方法。在系统开发上，Karjanto[96, 97]积极推广开源CAS Maxima在教学中的应用。

### 5.3 评估与互动学习

CAS也被用于创建形成性评估。Herbert[98]利用LaTeX、PDF表单和计算机代数创建数学形成性评估。Pardos和Bhandari[99]则评估了ChatGPT与人类导师生成的代数提示在学习增益上的差异，发现人类提示仍具显著优势，这为AI教育工具的研发提供了重要参考。

## 结论与展望

本文系统综述了计算机代数系统的算法实现及其在数学物理、工程科学、人工智能和教育等领域的广泛应用。文献表明，经过数十年的发展，CAS已经从强大的符号计算引擎演变为支撑多学科研究和创新的基础性工具。

**主要进展总结如下**：
1.  **算法核心不断强化**：经典算法（如Gröbner基计算）通过机器学习等方法得到优化；新算法（如基于多项式除法的递推关系计算[10]）不断涌现；专门领域系统（如Cadabra2）针对张量场论等需求提供了高效解决方案。
2.  **应用边界持续拓展**：在数学物理中，CAS已成为求解非线性PDE、分析可积系统和研究引力理论的标准工具[4-7, 15, 48]。在工程中，它深入到控制、机器人、电路验证等核心环节[42, 44, 49]。与AI的融合催生了神经符号计算[62, 63]、符号回归[67, 65]和机器学习辅助的算法选择[68]等新方向。
3.  **教育角色日益凸显**：CAS作为教学辅助、探究工具和可访问性解决方案，正在重塑数学教育[81, 82]，并为特殊需求学生提供支持[91, 93]。

**当前挑战与未来方向**：
尽管成果丰硕，该领域仍面临诸多挑战，未来研究可能在以下方向取得突破：
1.  **可扩展性与性能**：处理大规模、高复杂度问题（如极高阶PDE系统、超大矩阵）时，符号计算仍面临组合爆炸和内存限制。未来需要结合高性能计算、并行算法和混合符号-数值方法[100, 101]。
2.  **算法的智能化与自动化**：如何让CAS更智能地选择算法、猜测表达式形式、甚至自动发现新的数学关系，是一个长期目标。深度学习和符号计算的深度融合将是一个关键路径[102, 103, 104]。
3.  **跨范式集成的鲁棒性**：神经符号系统、SAT与代数混合求解器等集成系统的理论完备性和实际鲁棒性仍需加强[72, 71, 105]。需要发展更坚实的数学基础来保证这些复杂系统的可靠性。
4.  **量子计算时代的适配**：随着量子计算硬件的发展，需要开发适用于量子算法设计、分析和验证的新型符号计算工具[76, 106]，并探索量子计算机代数系统的新形态。
5.  **用户体验与普及**：降低专业CAS的使用门槛，开发更直观的交互界面（如自然语言输入），并将其更无缝地嵌入到科研工作流和教育环境中，对于扩大其影响力至关重要[9]。

计算机代数系统正处于一个充满活力的交叉点。它不仅是执行复杂数学计算的工具，更已成为连接纯数学、应用科学和计算智能的桥梁。面对日益复杂的科学问题和工程挑战，持续推动计算机代数算法的创新与应用边界的拓展，对于加速科学发现和技术进步具有不可替代的意义。未来的CAS将更加智能、强大和普及，继续在人类探索未知世界的征程中扮演关键角色。



## References

[1] Bruno Salvy, "SYMBOLIC COMPUTATION," Applied Numerical Methods Using Matlab®, 2020. DOI: 10.1002/9781119626879.app7

[2] W. Koepf, "Introduction to Computer Algebra," Springer Undergraduate Texts in Mathematics and Technology, 2021. DOI: 10.1007/978-3-030-78017-3_1

[3] E. Roanes-Lozano, José Luis Galán García, and Carmen Solano-Macías, "Some Reflections About the Success and Impact of the Computer Algebra System DERIVE with a 10-Year Time Perspective," Mathematics in Computer Science, 2019. DOI: 10.1007/s11786-019-00404-9

[4] V. Gerdt, Wolfram Koepf, Werner M. Seiler, et al., "Computer Algebra in Scientific Computing," Lecture Notes in Computer Science, 2018. DOI: 10.1007/978-3-319-99639-4

[5] Dylan Peifer, M. Stillman, and Daniel Halpern-Leistner, "Learning selection strategies in Buchberger's algorithm," in International Conference on Machine Learning, 2020

[6] Henrich Lauko, P. Ročkai, and J. Barnat, "Symbolic Computation via Program Transformation," arXiv preprint, 10.1007/978-3-030-02508-3_17, 2018

[7] Gaurav Kumar, R. Banerjee, Deepak Kr Singh, et al., "Mathematics for Machine Learning," Journal of Mathematical Sciences & Computational Mathematics, 2020. DOI: 10.1017/9781108679930

[8] Iordanis Kerenidis, Jonas Landman, Alessandro Luongo, et al., "q-means: A quantum algorithm for unsupervised machine learning," Neural Information Processing Systems, 2018

[9] Hayk Martiros, Aaron Miller, Nathan Bucki, et al., "SymForce: Symbolic Computation and Code Generation for Robotics," arXiv preprint, 10.15607/RSS.2022.XVIII.041, 2022

[10] Jérémy Berthomieu and J. Faugère, "A Polynomial-Division-Based Algorithm for Computing Linear Recurrence Relations," in Proceedings of the 2018 ACM International Symposium on Symbolic and Algebraic Computation, 2018. DOI: 10.1145/3208976.3209017

[11] J. Sendra and J. Sendra, "Symbolic computation of Drazin inverses by specializations," J. Comput. Appl. Math., 2016. DOI: 10.1016/j.cam.2016.01.059

[12] P. Stanimirović, M. Ciric, A. Lastra, et al., "Representations and symbolic computation of generalized inverses over fields," Appl. Math. Comput., 2021. DOI: 10.1016/j.amc.2021.126287

[13] E. Kofman, Joaquín Fernández, and Denise Marzorati, "Compact sparse symbolic Jacobian computation in large systems of ODEs," Appl. Math. Comput., 2021. DOI: 10.1016/j.amc.2021.126181

[14] C. Raab, "Symbolic Computation of Parameter Integrals," in Proceedings of the 2016 ACM International Symposium on Symbolic and Algebraic Computation, 2016. DOI: 10.1145/2930889.2930940

[15] Zihao Wu, J. Boehm, Rourou Ma, et al., "NeatIBP 1.0, a package generating small-size integration-by-parts relations for Feynman integrals," Comput. Phys. Commun., 2023. DOI: 10.1016/j.cpc.2023.108999

[16] J. Ablinger, "Computing the Inverse Mellin Transform of Holonomic Sequences using Kovacic's Algorithm," arXiv preprint, 10.22323/1.290.0001, 2018

[17] Nathan Fox, "Discovering linear-recurrent solutions to Hofstadter-like recurrences using symbolic computation," J. Symb. Comput., 2018. DOI: 10.1016/j.jsc.2017.06.002

[18] D. Hildenbrand, "Introduction to Geometric Algebra Computing", 2018. DOI: 10.1201/9781315152172

[19] K. Peeters, "Cadabra2: computer algebra for field theory revisited," J. Open Source Softw., 2018. DOI: 10.21105/JOSS.01118

[20] Jingyuan Yang and W. Ma, "Lump solutions to the BKP equation by symbolic computation," International Journal of Modern Physics B, 2016. DOI: 10.1142/S0217979216400282

[21] Xing Lü, W. Ma, Yuan Zhou, et al., "Rational solutions to an extended Kadomtsev-Petviashvili-like equation with symbolic computation," Comput. Math. Appl., 2016. DOI: 10.1016/j.camwa.2016.02.017

[22] A. Adem, "Symbolic computation on exact solutions of a coupled Kadomtsev-Petviashvili equation: Lie symmetry analysis and extended tanh method," Comput. Math. Appl., 2017. DOI: 10.1016/j.camwa.2017.06.049

[23] Xin-Yi Gao, Yongjiang Guo, and Wen-Rui Shan, "Water-wave symbolic computation for the Earth, Enceladus and Titan: The higher-order Boussinesq-Burgers system, auto- and non-auto-Bäcklund transformations," Appl. Math. Lett., 2020. DOI: 10.1016/j.aml.2019.106170

[24] Xin-Yi Gao, "In plasma physics and fluid dynamics: Symbolic computation on a (2+1)-dimensional variable-coefficient Sawada-Kotera system," Appl. Math. Lett., 2024. DOI: 10.1016/j.aml.2024.109262

[25] Xin-Yi Gao, "Symbolic Computation on a (2+1)-Dimensional Generalized Nonlinear Evolution System in Fluid Dynamics, Plasma Physics, Nonlinear Optics and Quantum Mechanics," Qualitative Theory of Dynamical Systems, 2024. DOI: 10.1007/s12346-024-01045-5

[26] Xin-Yi Gao, Yongjiang Guo, and Wen-Rui Shan, "Symbolic computation on a (2+1)-dimensional generalized variable-coefficient Boiti–Leon–Pempinelli system for the water waves," Chaos Solitons & Fractals, 2021. DOI: 10.1016/J.CHAOS.2021.111066

[27] Xin-Yi Gao, Y. Guo, and Wen-Rui Shan, "Oceanic shallow-water symbolic computation on a (2+1)-dimensional generalized dispersive long-wave system," Physics Letters A, 2022. DOI: 10.1016/j.physleta.2022.128552

[28] S Kumar and B. Mohan, "A direct symbolic computation of center-controlled rogue waves to a new Painlevé-integrable (3+1)-D generalized nonlinear evolution equation in plasmas," Nonlinear Dynamics, 2023. DOI: 10.1007/s11071-023-08683-5

[29] S Kumar, B. Mohan, and Raj Kumar, "Newly formed center-controlled rouge wave and lump solutions of a generalized (3+1)-dimensional KdV-BBM equation via symbolic computation approach," Physica Scripta, 2023. DOI: 10.1088/1402-4896/ace862

[30] Zhaqilao, "A symbolic computation approach to constructing rogue waves with a controllable center in the nonlinear systems," Comput. Math. Appl., 2018. DOI: 10.1016/j.camwa.2018.02.001

[31] Jian‐Guo Liu, Wen-Hui Zhu, and Yan He, "Variable-coefficient symbolic computation approach for finding multiple rogue wave solutions of nonlinear system with variable coefficients," Zeitschrift für angewandte Mathematik und Physik, 2019. DOI: 10.1007/s00033-021-01584-w

[32] Joseph Krasil'shchik, A. Verbovetsky, and R. Vitolo, "The Symbolic Computation of Integrability Structures for Partial Differential Equations," Texts & Monographs in Symbolic Computation, 2018. DOI: 10.1007/978-3-319-71655-8

[33] A. Cheviakov, "Symbolic computation of equivalence transformations and parameter reduction for nonlinear physical models," Comput. Phys. Commun., 2017. DOI: 10.1016/j.cpc.2017.06.013

[34] A. Adem, T. S. Moretlo, and B. Muatjetjeja, "A generalized dispersive water waves system: Conservation laws; symmetry reduction; travelling wave solutions; symbolic computation," Partial Differential Equations in Applied Mathematics, 2022. DOI: 10.1016/j.padiff.2022.100465

[35] M. MacCallum, "Computer algebra in gravity research," Living Reviews in Relativity, 2018. DOI: 10.1007/s41114-018-0015-6

[36] I. Shirokov, "Computer Algebra Calculations in Supersymmetric Electrodynamics," Programming and Computer Software, 2022. DOI: 10.1134/S0361768823020147

[37] A. V. Korolkova, M. Gevorkyan, Arseny V. Fedorov, et al., "Symbolic Studies of Maxwell’s Equations in Space-Time Algebra Formalism," Programming and Computer Software, 2024. DOI: 10.1134/S0361768824020087

[38] F. Mogavero and J. Laskar, "The origin of chaos in the Solar System through computer algebra," Astronomy &amp; Astrophysics, 2022. DOI: 10.1051/0004-6361/202243327

[39] Bo Huang and W. Niu, "Analysis of Snapback Repellers Using Methods of Symbolic Computation," Int. J. Bifurc. Chaos, 2019. DOI: 10.1142/S0218127419500548

[40] Bo Huang, W. Niu, and Dongming Wang, "Symbolic computation for the qualitative theory of differential equations," Acta Mathematica Scientia, 2022. DOI: 10.1007/s10473-022-0617-7

[41] Jichao Song, Wei Niu, Bo Huang, et al., "Qualitative Investigation of the Lorenz-84 System Using Computer Algebra Methods," Mathematics in Computer Science, 2025. DOI: 10.1007/s11786-025-00605-5

[42] Xiaoyong Jiang, Langyue Huang, Mengle Peng, et al., "Nonlinear model predictive control using symbolic computation on autonomous marine surface vehicle," Journal of Marine Science and Technology, 2021. DOI: 10.1007/s00773-021-00847-5

[43] T. Do, V. Vu, and Zhaoheng Liu, "Symbolic differentiation algorithm for inverse dynamics of serial robots with flexible joints," Journal of Mechanisms and Robotics, 2021. DOI: 10.1115/1.4051355

[44] D. Chablat, Rémi Prébet, M. S. E. Din, et al., "Deciding Cuspidality of Manipulators through Computer Algebra and Algorithms in Real Algebraic Geometry," in Proceedings of the 2022 International Symposium on Symbolic and Algebraic Computation, 2022. DOI: 10.1145/3476446.3535477

[45] Lubin Hang, Chengwei Shen, and Tingli Yang, "Structural Analysis of Parallel Mechanisms Using Conformal Geometric Algebra," in International Conference on Intelligent Robotics and Applications, 2016. DOI: 10.1007/978-3-319-43506-0_14

[46] G. Shi, "Toward automated reasoning for analog IC design by symbolic computation - A survey," Integr., 2018. DOI: 10.1016/j.vlsi.2017.08.005

[47] Alireza Mahzoon, Daniel Große, Christoph Scholl, et al., "Formal Verification of Modular Multipliers using Symbolic Computer Algebra and Boolean Satisfiability," in 2022 59th ACM/IEEE Design Automation Conference (DAC), 2022. DOI: 10.1145/3489517.3530605

[48] Daniela Kaufmann and Armin Biere, "Improving AMulet2 for verifying multiplier circuits using SAT solving and computer algebra," International Journal on Software Tools for Technology Transfer, 2023. DOI: 10.1007/s10009-022-00688-6

[49] V. Rao, Haden Ondricek, P. Kalla, et al., "Rectification of Integer Arithmetic Circuits using Computer Algebra Techniques," in 2021 IEEE 39th International Conference on Computer Design (ICCD), 2021. DOI: 10.1109/ICCD53106.2021.00039

[50] Zhengyu Li, Curtis Bright, and Vijay Ganesh, "A SAT Solver and Computer Algebra Attack on the Minimum Kochen-Specker Problem," in International Joint Conference on Artificial Intelligence, 2023. DOI: 10.24963/ijcai.2024/210

[51] Zhengyu Li, Curtis Bright, and Vijay Ganesh, "A SAT Solver and Computer Algebra Attack on the Minimum Kochen-Specker Problem (Student Abstract)," in AAAI Conference on Artificial Intelligence, 2024. DOI: 10.1609/aaai.v38i21.30472

[52] Pierre Cordesse and M. Massot, "Entropy supplementary conservation law for non-linear systems of PDEs with non-conservative terms: application to the modelling and analysis of complex fluid flows using computer algebra," arXiv preprint, 10.4310/CMS.2020.V18.N2.A10, 2019

[53] E. V. Vorozhtsov and S. Kiselev, "Comparative Study of the Accuracy of Higher-Order Difference Schemes for Molecular Dynamics Problems Using the Computer Algebra Means," Computer Algebra in Scientific Computing, 2020. DOI: 10.1007/978-3-030-60026-6_35

[54] S. Gutnik and V. Sarychev, "Application of Computer Algebra Methods to Investigate the Dynamics of the System of Two Connected Bodies Moving along a Circular Orbit," Programming and Computer Software, 2019. DOI: 10.1134/S0361768819020051

[55] S. Gutnik and V. Sarychev, "Application of computer algebra methods for investigation of stationary motions of a gyrostat satellite," Programming and Computer Software, 2017. DOI: 10.1134/S0361768817020050

[56] S. Gutnik and V. Sarychev, "Application of Computer Algebra Methods to Investigation of Stationary Motions of a System of Two Connected Bodies Moving in a Circular Orbit," Computational Mathematics and Mathematical Physics, 2020. DOI: 10.1134/S0965542520010091

[57] S. Gutnik and V. Sarychev, "Computer Algebra Methods for Searching the Stationary Motions of the Connected Bodies System Moving in Gravitational Field," Mathematics in Computer Science, 2022. DOI: 10.1007/s11786-022-00535-6

[58] A. Prokopenya, M. Minglibayev, and S. Shomshekova, "Applications of Computer Algebra in the Study of the Two-Planet Problem of Three Bodies with Variable Masses," Programming and Computer Software, 2019. DOI: 10.1134/S0361768819020087

[59] A. Prokopenya, M. Minglibayev, and Aiken Kosherbayeva, "Derivation of Evolutionary Equations in the Many-Body Problem with Isotropically Varying Masses Using Computer Algebra," Programming and Computer Software, 2022. DOI: 10.1134/S0361768822020098

[60] Hansu Kim, Shinyu Kim, Taekyun Kim, et al., "Efficient design optimization of complex system through an integrated interface using symbolic computation," Adv. Eng. Softw., 2018. DOI: 10.1016/J.ADVENGSOFT.2018.09.006

[61] Fei Zhao, I. Grossmann, Salvador García Muñoz, et al., "Design Space Description through Adaptive Sampling and Symbolic Computation," AIChE Journal, 2022. DOI: 10.1002/aic.17604

[62] Baoyu Liang, Yucheng Wang, and Chao Tong, "AI Reasoning in Deep Learning Era: From Symbolic AI to Neural–Symbolic AI," Mathematics, 2025. DOI: 10.3390/math13111707

[63] Giuseppe Pisano, Giovanni Ciatto, Roberta Calegari, et al., "Neuro-symbolic Computation for XAI: Towards a Unified Model," in Workshop From Objects to Agents, 2020

[64] Pyeong Whan Cho, M. Goldrick, and P. Smolensky, "Incremental parsing in a continuous dynamical system: sentence processing in Gradient Symbolic Computation," Linguistics Vanguard, 2017. DOI: 10.1515/lingvan-2016-0105

[65] Charles Fox, N. Tran, Nikki Nacion, et al., "Incorporating background knowledge in symbolic regression using a computer algebra system," Machine Learning: Science and Technology, 2023. DOI: 10.1088/2632-2153/ad4a1e

[66] Yuhong Sun, Ting Huang, Jinghui Zhong, et al., "Symbolic Regression-Assisted Offline Data-Driven Evolutionary Computation," in IEEE Transactions on Evolutionary Computation, 2025. DOI: 10.1109/TEVC.2024.3482326

[67] Changxin Wang, Y. Zhang, Cheng Wen, et al., "Symbolic regression in materials science via dimension-synchronous-computation," Journal of Materials Science &amp; Technology, 2022. DOI: 10.1016/j.jmst.2021.12.052

[68] Rashid Barket, Matthew England, and Jurgen Gerhard, "Symbolic Integration Algorithm Selection with Machine Learning: LSTMs vs Tree LSTMs," arXiv preprint, 10.48550/arXiv.2404.14973, 2024

[69] E. Ábrahám, J. Abbott, B. Becker, et al., "Satisfiability Checking meets Symbolic Computation (Project Paper)," in International Conference on Intelligent Computer Mathematics, 2016. DOI: 10.1007/978-3-319-42547-4_3

[70] E. Ábrahám, J. Abbott, B. Becker, et al., "Satisfiability checking and symbolic computation," in ACM Commun. Comput. Algebra, 2016. DOI: 10.1145/3055282.3055285

[71] J. Davenport, M. England, A. Griggio, et al., "Symbolic computation and satisfiability checking," J. Symb. Comput., 2020. DOI: 10.1016/J.JSC.2019.07.017

[72] Curtis Bright, I. Kotsireas, and Vijay Ganesh, "When satisfiability solving meets symbolic computation," in Communications of the ACM, 2022. DOI: 10.1145/3500921

[73] Edward Zulkoski, Curtis Bright, A. Heinle, et al., "Combining SAT Solvers with Computer Algebra Systems to Verify Combinatorial Conjectures," Journal of Automated Reasoning, 2016. DOI: 10.1007/s10817-016-9396-y

[74] Edward Zulkoski, Vijay Ganesh, and K. Czarnecki, "MathCheck: A Math Assistant via a Combination of Computer Algebra Systems and SAT Solvers," CADE, 2016. DOI: 10.1007/978-3-319-21401-6_41

[75] Laigang Guo, R. Yeung, and Xiao-Shan Gao, "Proving Information Inequalities and Identities with Symbolic Computation," in 2022 IEEE International Symposium on Information Theory (ISIT), 2022. DOI: 10.1109/ISIT50566.2022.9834774

[76] Patrick J. Coles, S. Eidenbenz, S. Pakin, et al., "Quantum Algorithm Implementations for Beginners," in ACM Transactions on Quantum Computing, 2018. DOI: 10.1145/3517340

[77] Daan Camps, Lin Lin, R. Beeumen, et al., "Explicit Quantum Circuits for Block Encodings of Certain Sparse Matrice," arXiv preprint, 10.48550/arXiv.2203.10236, 2022

[78] Changpeng Shao, "Computing Eigenvalues of Diagonalizable Matrices on a Quantum Computer," in ACM Transactions on Quantum Computing, 2022. DOI: 10.1145/3527845

[79] E. Combarro, J. Ranilla, and I. F. Rúa, "A Quantum Algorithm for the Commutativity of Finite Dimensional Algebras," in IEEE Access, 2019. DOI: 10.1109/ACCESS.2019.2908785

[80] Binh Duc Nguyen, "Simulation of Quantum Computation via MAGMA Computational Algebra System," International Journal of Advanced Trends in Computer Science and Engineering, 2020. DOI: 10.30534/ijatcse/2020/130922020

[81] M. Tamur, Y. S. Ksumah, D. Juandi, et al., "A Meta-Analysis of the Past Decade of Mathematics Learning Based on the Computer Algebra System (CAS)," in Journal of Physics: Conference Series, 2021. DOI: 10.1088/1742-6596/1882/1/012060

[82] F. Kamalov, David Santandreu, Ho-Hon Leung, et al., "Leveraging computer algebra systems in calculus: a case study with SymPy," in 2023 IEEE Global Engineering Education Conference (EDUCON), 2023. DOI: 10.1109/EDUCON54358.2023.10125196

[83] N. Karjanto and S. Lee, "Flipped classroom in Introductory Linear Algebra by utilizing Computer Algebra System {\sl SageMath} and a free electronic book," arXiv preprint, 2017

[84] Fereshteh Zeynivandnezhad and Rachel Bates, "Explicating mathematical thinking in differential equations using a computer algebra system," International Journal of Mathematical Education in Science and Technology, 2017. DOI: 10.1080/0020739X.2017.1409368

[85] N. Lohgheswary, Z. Nopiah, Effandi Zakaria, et al., "Incorporating Computer Algebra System in Differential Equations Syllabus," Journal of Engineering and Applied Sciences, 2019. DOI: 10.36478/jeasci.2019.7475.7480

[86] A. Olenev, A. Shuvaev, M V Migacheva, et al., "Using the Maple computer algebra system to study mathematical induction," in Journal of Physics: Conference Series, 2020. DOI: 10.1088/1742-6596/1691/1/012102

[87] A. Olenev, K. A. Kirichek, E. V. Potekhina, et al., "Capabilities of the Maple computer algebra system in the study of set theory and combinatorics," in Journal of Physics: Conference Series, 2020. DOI: 10.1088/1742-6596/1691/1/012097

[88] V. Velychko, A. V. Stopkin, and Olena H. Fedorenko, "USE OF COMPUTER ALGEBRA SYSTEM MAXIMA IN THE PROCESS OF TEACHING FUTURE MATHEMATICS TEACHERS," Information Technologies and Learning Tools, 2019. DOI: 10.33407/ITLT.V69I1.2284

[89] R. Hasek, "Dynamic Geometry Software Supplemented with a Computer Algebra System as a Proving Tool," Mathematics in Computer Science, 2018. DOI: 10.1007/s11786-018-0369-x

[90] Christopher W. Brown, Z. Kovács, T. Recio, et al., "Is Computer Algebra Ready for Conjecturing and Proving Geometric Inequalities in the Classroom?," Mathematics in Computer Science, 2022. DOI: 10.1007/s11786-022-00532-9

[91] Paúl Mejía, L. Martini, Felipe Grijalva, et al., "CASVI: Computer Algebra System Aimed at Visually Impaired People. Experiments," in IEEE Access, 2021. DOI: 10.1109/ACCESS.2021.3129106

[92] Paúl Mejía, L. Martini, J. Larco, et al., "CASVI: A Computer Algebra System Aimed at Visually Impaired People," in International Conference on Computers for Handicapped Persons, 2018. DOI: 10.1007/978-3-319-94277-3_89

[93] A. Zambrano, Danilo Pilacuan, Mateo N. Salvador, et al., "IrisMath: A Blind-Friendly Web-Based Computer Algebra System," in IEEE Access, 2023. DOI: 10.1109/ACCESS.2023.3281761

[94] I. Petkovic and D. Herceg, "Symbolic computation and computer graphics as tools for developing and studying new root-finding methods," Appl. Math. Comput., 2017. DOI: 10.1016/j.amc.2016.09.025

[95] I. Petkovic and B. Neta, "On an application of symbolic computation and computer graphics to root-finders: The case of multiple roots of unknown multiplicity," J. Comput. Appl. Math., 2016. DOI: 10.1016/j.cam.2016.06.008

[96] N. Karjanto and H. S. Husain, "Not another computer algebra system: Highlighting wxMaxima in calculus," arXiv preprint, 10.3390/math9011317, 2021

[97] N. Karjanto and H. S. Husain, "Adopting Maxima as an Open-Source Computer Algebra System into Mathematics Teaching and Learning", 2017. DOI: 10.1007/978-3-319-62597-3_128

[98] Katherine Herbert, D. Demskoi, and Kerrie Cullis, "Creating mathematics formative assessments using LaTeX, PDF forms and computer algebra," Australasian Journal of Educational Technology, 2018. DOI: 10.14742/AJET.4539

[99] Z. Pardos and Shreya Bhandari, "Learning gain differences between ChatGPT and human tutor generated algebra hints," arXiv preprint, 10.48550/arXiv.2302.06871, 2023

[100] P. Zhang, Yueming Liu, and Meikang Qiu, "SNC: A Cloud Service Platform for Symbolic-Numeric Computation Using Just-In-Time Compilation," in IEEE Transactions on Cloud Computing, 2018. DOI: 10.1109/TCC.2017.2656088

[101] 佚名, "Numerical and Symbolic Computation", 2020. DOI: 10.3390/books978-3-03936-303-2

[102] Lynn Pickering, Tereso Del Rio Almajano, M. England, et al., "Explainable AI Insights for Symbolic Computation: A case study on selecting the variable ordering for cylindrical algebraic decomposition," arXiv preprint, 10.1016/j.jsc.2023.102276, 2023

[103] B. Buchberger, "Automated programming, symbolic computation, machine learning: my personal view," Annals of Mathematics and Artificial Intelligence, 2023. DOI: 10.1007/s10472-023-09894-7

[104] Tereso del R'io and Matthew England, "Lessons on Datasets and Paradigms in Machine Learning for Symbolic Computation: A Case Study on CAD," Mathematics in Computer Science, 2024. DOI: 10.1007/s11786-024-00591-0

[105] G. Sarma and Nick J. Hay, "Robust Computer Algebra, Theorem Proving, and Oracle AI," Informatica (Slovenia), 2017. DOI: 10.2139/SSRN.3038545

[106] O. Alsheikh, Efekan K¨okc¨u, B. Bakalov, et al., "RedCarD: A Quantum Assisted Algorithm for Fixed-Depth Unitary Synthesis via Cartan Decomposition", 2025