# 计算机代数系统的算法实现及应用：文献综述

## 引言

计算机代数系统（Computer Algebra System, CAS）是一类能够执行符号计算（symbolic computation）的软件系统，其核心功能在于对数学表达式进行解析、化简、转换和求解，而非仅仅进行数值计算 [1]。自20世纪60年代第一个计算机代数系统如MACSYMA诞生以来，这一领域经历了从专用系统到通用平台，从单机应用到云端服务，从纯粹符号计算到与数值计算、机器学习深度融合的演进历程 [2, 3, 4]。计算机代数系统不仅在数学、物理等基础科学研究中扮演着不可或缺的工具角色，更广泛渗透到工程、教育、生物信息、金融科技等众多领域 [5, 6, 7]。

近年来，随着计算需求的爆炸式增长和算法理论的不断突破，计算机代数系统的研究与开发呈现出多维度的创新态势：一方面，以Maxima [5]、Cadabra2 [6]、SymPy [8]、OSCAR [9] 为代表的经典与新兴系统在功能、性能和可扩展性上持续优化；另一方面，符号计算与SAT求解 [10, 11, 12]、机器学习 [13, 14, 15, 16]、量子计算 [17, 18, 19] 等领域的交叉融合催生了全新的研究范式和应用场景。本综述旨在系统梳理2016年至2025年间计算机代数系统在算法实现及应用方面的研究进展，通过对292篇代表性文献的分析，归纳核心算法、总结应用成果、辨识研究趋势，并探讨未来面临的挑战与发展方向。

## 计算机代数系统的发展与实现

### 主要CAS系统概述

当前主流的计算机代数系统可分为商业软件（如Maple、Mathematica、MATLAB）和开源软件两大阵营。开源CAS因其透明性、可定制性和社区驱动的特性，在研究和教育领域日益受到青睐。Maxima作为源自MACSYMA的开源后继者，提供了从微积分、线性代数到微分方程求解的广泛功能，并在教学场景中得到了重点应用 [5, 20, 21, 22]。SymPy是一个纯Python库，因其与Python生态系统的无缝集成和易于扩展的特性，在科学计算和工程领域迅速普及 [23, 8]。Cadabra2则是专为张量场论问题设计的CAS，采用类似数学记法的输入格式和Python交互环境，极大地方便了广义相对论、高能物理等领域的研究 [6, 24]。

新兴系统如OSCAR（Open Source Computer Algebra Research）致力于整合代数、数论和几何计算的最先进算法，构建下一代高性能计算机代数系统 [9]。HPC-GAP项目则通过设计新的并行编程抽象和领域特定骨架，使GAP系统能够有效利用从多核节点到超大规模集群的计算资源，开启了符号计算高性能化的新篇章 [3]。

### 算法实现与优化

计算机代数系统的核心性能取决于其底层算法的效率。多项式运算是CAS的基础，Gröbner基计算、多项式因式分解等算法的优化一直是研究重点。Peifer等人 [25] 将强化学习应用于Buchberger算法中的S-对选择策略，展示了机器学习优化经典符号计算算法的潜力。在积分计算方面，Barket等人 [26] 比较了LSTM和TreeLSTM模型在符号积分算法选择中的应用，发现能够捕捉表达式树结构的TreeLSTM模型性能显著更优。

对于线性代数运算，符号与数值方法的结合成为趋势。Stanimirović等人 [27] 研究了域上广义逆的表示与符号计算，而Prodanov [28] 则给出了计算非退化Clifford代数中最小多项式和多向量逆的算法。在处理大规模ODE系统时，Kofman等人 [29] 提出了紧凑稀疏符号Jacobian计算方法，显著提高了计算效率。

### 新系统与架构创新

模块化与可扩展性成为现代CAS设计的重要原则。MathPartner系统采用Mathpar编程语言，支持在分布式内存超级计算机上进行符号计算 [7]。SNC平台利用即时编译（JIT）技术，将用户描述的符号表达式编译为机器码，实现了跨云平台的符号-数值计算服务 [4]。面向特殊需求的CAS也得到发展，如为视障人士设计的CASVI [30, 31] 和IrisMath [32] 系统，通过支持LaTeX、CMathML、JSON和音频等多种输出格式，显著改善了视觉障碍者学习数学和工程的体验。

此外，领域特定语言（DSL）与CAS的结合催生了如SymForce这样的库，它通过符号计算和代码生成，为机器人学中的计算机视觉、运动规划和控制提供了高效的优化解决方案 [33]。

## 符号计算算法研究

### 多项式与代数算法

多项式系统求解是计算机代数的基础问题。Berthomieu和Faugère [34] 提出了基于多项式除法的线性递推关系计算新算法，相比传统的Berlekamp-Massey算法和Scalar-FGLM算法，在多变量序列的线性递推关系猜测问题上表现出优势。在多项式理想方面，Ohara和Tajima [35] 针对形状基情形，给出了计算Grothendieck局部留数的算法。

在代数结构研究中，Alm和Ylvisaker [36] 提出了快速陪集平移算法，用于计算Comer关系代数在Z/pZ上的循环结构，将时间复杂度从O(p²)降低到O(p)。Brooksbank等人 [37] 则给出了李代数亏格为2的群的快速同构测试算法。

### 微分方程求解算法

微分方程的符号求解是CAS的核心功能之一。Krasil'shchik等人 [38] 系统阐述了偏微分方程可积结构的符号计算方法。Cheviakov [39] 提出了非线性物理模型等价变换和参数约化的系统符号计算流程，并通过Maple中的GeM软件包实现。对于分数阶微分方程，Guner和Bekir [40] 发展了一种使用符号计算的新方法。

在微分等价性方面，Cardelli等人 [41] 引入了微分等价关系的概念，并提供了通过可满足性模理论进行分区优化的符号过程，可用于连续时间马尔可夫链的约简、化学反应网络的互模拟等。

### 特殊函数与积分算法

特殊函数的计算与变换是许多科学计算的基础。Ablinger [42] 描述了如何通过扩展Kovacic算法来改进计算全纯序列的逆Mellin变换的方法。Raab [43] 探讨了参数积分的符号计算。在级数计算方面，Masjed-Jamei和Koepf [44] 研究了幂三角级数的符号计算。

对于物理学中至关重要的费曼积分计算，Wu等人 [45] 开发了NeatIBP包，通过syzygy和模交技术自动生成小尺寸的积分-by-parts恒等式，相比标准的Laporta算法能产生更小的IBP系统。Chen [46] 进一步提出了在参数表示中约化张量费曼积分的两种方法。

### 几何代数算法

几何代数（Geometric Algebra）提供了一种统一的数学框架来处理几何对象和变换，相关算法研究日益活跃。Hildenbrand等人 [47] 系统介绍了几何代数计算的基本原理。在计算机图形学中，Papaefthymiou等人 [48, 49] 提出了基于共形几何代数的GPU动画插值变形算法和远距离光照实时渲染方法。Wang等人 [50] 分析了几何代数最小均方自适应滤波器的瞬态性能，为3D点云注册、计算机视觉中的旋转估计等应用提供了理论依据。

计算几何方面，Yin等人 [51] 基于几何代数提出了三维空间对象顶点凹凸性检测方法，该框架能够统一处理二维简单多边形和三维简单多面体。Li等人 [52] 则开发了基于几何代数的多光谱图像快速视网膜关键点提取算法（GA-FREAK），在实时性应用中表现出优势。

## 计算机代数在科学与工程中的应用

### 数学物理与偏微分方程

符号计算在非线性偏微分方程的精确解研究中发挥了不可替代的作用。Gao及其合作者在这一领域做出了系统性的贡献，他们利用符号计算方法研究了从Boussinesq-Burgers系统 [53]、广义变量系数Boiti–Leon–Pempinelli系统 [54] 到Zakharov-Kuznetsov-Burgers方程 [55] 等一系列描述水波、等离子体、非线性光学等现象的方程，构造了孤子、怪波（rogue wave）和 lump解 [56, 57, 58, 59, 60]。Ma等人 [61, 62] 同样在寻找线性PDE的 lump解和相互作用解方面取得了丰硕成果。

在可积系统方面，Kumar等人 [63, 64] 发展了一种直接符号计算方法来构造等离子体中新的Painlevé可积(3+1)维广义非线性演化方程的中心控制怪波。Shen等人 [65] 研究了在非线性光学、流体动力学和等离子体物理中出现的(2+1)维扩展Calogero–Bogoyavlenskii–Schiff系统。

### 流体力学与等离子体物理

计算流体力学中的许多问题可以通过符号计算获得解析见解或简化模型。Vorozhtsov和Kiselev [66] 使用计算机代数方法比较了分子动力学问题中高阶差分格式的精度。Blinkov和Rebrina [67] 研究了二维Navier-Stokes方程差分格式的计算机代数算法。Cordesse和Massot [68] 将计算机代数应用于具有非保守项的非线性PDE系统的熵补充守恒律推导，以建模和分析复杂流体流动。

在等离子体物理中，符号计算被用于分析磁流体动力学方程、描述泡状液体的Kudryashov-Sinelshchikov方程 [59] 以及各种非线性演化系统 [58, 63]。

### 相对论与引力研究

计算机代数是广义相对论研究中不可或缺的工具。MacCallum [69] 综述了计算机代数在引力研究中的应用，包括张量计算、精确解分类、扰动计算等。Birkandan等人 [70] 比较了SageMath（含SageManifolds包）、Maxima（含ctensor包）和Python（含GraviPy模块）在广义相对论计算中的表现。Cadabra2系统因其对张量场论问题的专门支持，成为该领域的重要工具 [6, 24]。

Korolkova等人 [71] 利用计算机代数对时空代数形式下的麦克斯韦方程进行了符号研究，展示了几何代数在理论物理中的强大表达和计算能力。

### 控制系统与机器人学

在控制系统领域，符号计算被用于非线性模型预测控制器的设计和分析。Jiang等人 [72] 开发了基于符号计算的自持海洋表面车辆非线性模型预测控制方法。Devaraj等人 [73] 提出了功耗感知实时调度的监督控制方法及其符号计算实现。

机器人学中的运动学、动力学和控制问题也广泛受益于符号计算。Do等人 [74] 提出了用于具有柔性关节的串联机器人逆动力学的符号微分算法，可自动生成便携和优化的代码。Chablat等人 [75] 通过计算机代数和实代数几何算法，来判断机械手的尖点（cuspidality）特性。SymForce库 [33] 更是将符号计算和代码生成专门应用于机器人学中的优化问题。

### 航空航天与天体力学

天体力学中的多体问题因其高度非线性而难以解析处理，计算机代数提供了有效的辅助手段。Gutnik及其合作者 [76, 77, 78, 79] 系统应用计算机代数方法研究了连接体系统在引力场中的运动、陀螺卫星的定常运动等问题。Prokopenya等人 [80, 81] 则关注变质量三体问题中的行星运动，通过计算机代数推导演化方程。

Mogavero和Laskar [82] 通过计算机代数系统TRIP实现正则摄动理论，追溯了内行星长期动力学中起作用的长期共振，揭示了太阳系混沌运动的起源。Perminov和Kuznetsov [83, 84] 使用计算机代数系统Piranha，通过Hori-Deprit方法构建了行星运动理论的平均化方程。

## 计算机代数在教育中的应用

### 数学教学

计算机代数系统在数学教育中的应用已成为一个成熟的研究领域。Tamur等人 [85] 对过去十年基于CAS的数学学习进行了元分析，涵盖2010-2020年间31篇文章中的36个效应值，发现CAS的使用对学生的数学能力有大的积极影响（效应值ES = 0.89）。Karakuş和Aydın [86] 的研究表明，CAS能够显著提高本科生的空间可视化能力。

在教学实践中，Karjanto等人 [20, 22, 87] 探索了在微积分和线性代数课程中使用wxMaxima、SageMath等开源CAS的多种模式，包括翻转课堂。Kamalov等人 [23] 的案例研究显示，在微积分课程中引入SymPy后，学生成绩有统计显著的提高。Olenev等人 [88, 89] 则开发了Maple应用程序和框架，帮助学生掌握集合论、组合数学等离散数学概念。

### 工程与科学教育

在工程教育中，CAS被用于教授有限元方法 [90]、非线性规划 [91]、微分方程 [92] 等核心内容。Eyrikh等人 [90] 在七年的教育实验中，将Maple CAS融入“结构力学中的有限元方法”模块，发现参与的学生在后续硕士课程中表现出更高的数学熟练度和使用高端结构计算软件系统的技能。

跨学科连接方面，Bécar等人 [93] 提出了一种使用CAS连接数学和科学的方法。Herbert等人 [94] 开发了结合LaTeX、PDF表单和计算机代数创建数学形成性评估的新方法，能够生成个性化且自动评分的作业。

### 特殊需求教育

为视障学习者设计的CAS取得了显著进展。Mejía等人 [30, 31] 开发的CASVI系统基于Maxima引擎，允许视障用户进行基本和高级数值计算，在实验中实现了92%的操作准确率。Zambrano等人 [32] 设计的IrisMath是一个基于Web的盲人友好型CAS，提供多种输出格式（LaTex、CMathML、JSON和音频），经过功能、非功能和可用性需求的广泛评估，显示出作为工程专业视障学生工具的潜力。

## 跨学科融合与新兴方向

### 计算机代数与SAT求解

符号计算（Symbolic Computation）与可满足性检查（Satisfiability Checking）两个社区的融合催生了SC²项目 [10, 95]，旨在为算术理论的决策过程开发共同平台和路线图。这种融合产生了强大的问题解决能力：Zulkoski等人 [96, 97] 开发了MathCheck，一个结合CAS和SAT求解器的数学助手；Bright等人 [98] 通过计算机代数和可编程SAT的组合搜索，将复杂Golay对的存在性验证扩展到长度28；Li等人 [99, 100] 利用SAT求解器和计算机代数的组合攻击，将最小Kochen-Specker问题的下界从22提高到24，并生成了首个计算机可验证的证明证书。

在硬件验证领域，Kaufmann和Biere [101] 提出的AMulet2工具结合SAT求解和计算机代数来验证乘法器电路。Mahzoon等人 [102] 则开发了用于模乘法器形式验证的符号计算机代数与布尔可满足性结合的方法。

### 符号计算与机器学习

符号计算与机器学习的交叉呈现出双向融合的趋势。一方面，机器学习技术被用来优化符号计算算法。Pickering等人 [14] 利用可解释AI（XAI）技术分析机器学习模型如何选择柱形代数分解（CAD）的变量序，从而启发新的启发式方法。Peifer等人 [25] 使用强化学习训练Buchberger算法中的S-对选择策略。Barket等人 [26] 则用机器学习进行符号积分算法选择。

另一方面，符号计算方法也增强了机器学习的能力。Fox等人 [103] 探索了在符号回归中使用CAS整合背景知识。Sun等人 [104] 提出了符号回归辅助的离线数据驱动进化计算。Alnuqaydan等人 [105] 开发的SYMBA框架利用序列到序列模型（transformer）进行高能物理中平方振幅的符号计算，预测正确率达到97.6%（QCD）和99%（QED），速度比现有符号计算框架快几个数量级。

神经符号计算（Neural-Symbolic Computation）作为连接符号AI与神经计算的新兴范式，正受到越来越多的关注 [13, 106]。Buchberger [15] 从自动编程的角度，将符号计算和机器学习视为解决两种完全不同问题规约方式的互补方法。

### 量子计算中的代数方法

量子计算的发展为计算机代数带来了新的应用场景和算法挑战。Kerenidis等人 [17] 提出了用于无监督机器学习的量子算法q-means。Coles等人 [18] 为初学者提供了量子算法实现的全面介绍。Low和Su [19] 开发的量子本征值处理（QEP）框架，能够对块编码非正规算子的本征值应用任意多项式变换。

在量子线性代数方面，Camps等人 [107] 为某些稀疏矩阵的块编码提供了显式量子电路。Shao [108] 研究了在量子计算机上计算可对角化矩阵特征值的算法。Nguyen [109] 则通过MAGMA计算代数系统模拟量子计算，验证量子稳定子码的参数。

量子纠错中的代数结构也受到关注。Wolanski和Barber [110] 提出了用于qLDPC码解码的模糊聚类算法，相比BP-OSD解码器速度提高达27倍。Li等人 [111] 利用符号计算证明了信息论中的线性不等式和恒等式。

### 神经形态计算与超维计算

受大脑启发的新型计算架构为符号计算提供了新的实现平台。Cotteret等人 [112] 证明了分布式表示能够在神经形态硬件中实现稳健的多时间尺度符号计算。他们通过将有限状态机嵌入到递归脉冲神经网络的动力学中，展示了在不需参数微调的情况下，在神经形态硬件中实现稳健符号计算的可行性。

超维计算（Hyperdimensional Computing）作为一种基于高维分布式表示的框架，为随机计算和符号AI提供了统一的数学模型 [113]。Furlong和Eliasmith [114] 则利用向量符号架构（Vector Symbolic Architectures）来建模神经概率计算。

## 结论与展望

### 主要研究成果总结

通过对2016-2025年间292篇文献的系统分析，可以发现计算机代数系统的研究呈现出以下显著特征：

1. **系统多样化与专业化**：从通用系统如Maxima、SymPy到领域特定系统如Cadabra2（场论）、OSCAR（代数计算），CAS生态系统日益丰富和专业化 [5, 6, 9, 8]。开源CAS的兴起降低了使用门槛，促进了教育和研究领域的普及 [20, 22, 23]。

2. **算法创新与性能提升**：核心算法如多项式运算 [25, 34]、积分计算 [45, 26]、微分方程求解 [38, 39] 等持续优化，同时与机器学习技术的结合为算法选择与优化提供了新思路 [14, 103, 16]。

3. **应用领域深度拓展**：符号计算在数学物理 [4-8, 17, 20]、流体力学 [59, 60, 67]、相对论 [69, 70]、机器人学 [33, 75, 74] 等传统领域的应用更加深入，同时在量子计算 [17, 18, 19]、神经形态计算 [112]、生物信息学 [115] 等新兴领域开辟了新阵地。

4. **交叉融合成为创新源泉**：符号计算与SAT求解 [10, 99, 11]、机器学习 [13, 105, 14]、量子计算 [19, 108] 的深度融合，催生了全新的问题解决范式和方法论。

5. **教育应用走向成熟与普惠**：基于CAS的数学教育研究积累了充分证据支持其有效性 [85]，面向特殊需求的教育工具开发取得了实质性进展 [30, 31, 32]，技术促进教育公平的作用日益凸显。

### 当前挑战与不足

尽管取得了显著进展，计算机代数系统的发展仍面临多重挑战：

1. **可扩展性与性能瓶颈**：许多符号计算算法具有极高的计算复杂度，在处理大规模问题时面临严重的性能挑战。虽然HPC-GAP等项目在高性能计算方面取得了进展 [3]，但如何有效利用异构计算架构（GPU、量子处理器等）仍是未解决的问题。

2. **数值稳定性与可靠性**：符号-数值混合计算中的误差传播、条件数恶化和数值不稳定问题需要更系统的理论分析和算法保障 [4, 66]。

3. **易用性与可访问性**：大多数CAS仍然需要较高的专业知识才能有效使用。虽然面向视障用户的系统已取得进展 [30, 32]，但更广泛的可访问性设计（如自然语言接口、可视化编程）仍有待加强。

4. **验证与正确性保障**：随着CAS在安全关键系统（如航空航天、医疗设备）中的应用增加，如何形式化验证CAS实现的核心算法的正确性成为重要课题 [116, 117]。

5. **知识表示与推理的局限性**：当前CAS主要擅长代数操作和公式推导，但在高层次数学概念理解、定理自动证明、创造性问题求解等方面能力有限 [118, 116]。

### 未来发展方向

基于当前研究趋势和挑战，未来计算机代数系统的发展可能聚焦于以下方向：

1. **智能符号计算系统**：深度融合机器学习（特别是大语言模型）与符号推理，构建能够理解数学语义、自动选择策略、解释推理过程的下一代智能CAS [13, 14, 15]。类似ChatGPT的AI助手与CAS的集成可能彻底改变数学工作流程 [119]。

2. **云端与分布式符号计算**：利用云原生架构、容器化和微服务技术，构建可弹性扩展的符号计算服务平台 [4]。区块链技术可能用于确保分布式符号计算的可验证性和可追溯性。

3. **量子增强符号计算**：探索量子算法在符号计算问题（如多项式因式分解、Gröbner基计算）中的应用潜力，发展量子-经典混合符号计算框架 [17, 18, 19]。

4. **形式化验证与可信CAS**：基于定理证明器（如Isabelle、Coq）开发形式化验证的CAS核心算法库，为安全关键应用提供经过数学证明的可信计算基 [116, 117]。

5. **跨模态交互与协同计算**：发展支持自然语言、手写公式、图表等多种输入方式，并能够生成丰富可视化输出的交互式CAS环境。增强现实（AR）与CAS的结合可能创造沉浸式的数学探索体验。

6. **教育智能体与个性化学习**：基于CAS构建能够诊断学生错误概念、提供个性化反馈和适应性学习路径的数学教育智能体 [119, 94]。

7. **领域特定语言与生成式编程**：进一步发展嵌入在通用编程语言中的领域特定符号计算语言，支持从高层数学描述自动生成高效代码 [33, 120]。

计算机代数系统正站在从“计算工具”向“智能数学伙伴”转型的关键节点。随着算法理论的突破、计算架构的演进和跨学科融合的深化，符号计算必将在科学研究、工程创新和教育变革中发挥更加核心的作用。未来的研究需要在保持数学严谨性的同时，拥抱智能化、云原生化、可信化和人本化的技术趋势，使计算机代数真正成为人类数学思维的自然延伸和增强。

---
**参考文献**（文中引用编号对应的文献索引见原始列表1-292）

## References

[1] W. Koepf, "Introduction to Computer Algebra," Springer Undergraduate Texts in Mathematics and Technology, 2021. DOI: 10.1007/978-3-030-78017-3_1

[2] Bruno Salvy, "SYMBOLIC COMPUTATION," Applied Numerical Methods Using Matlab®, 2020. DOI: 10.1002/9781119626879.app7

[3] R. Behrends, K. Hammond, V. Janjić, et al., "HPC‐GAP: engineering a 21st‐century high‐performance computer algebra system," Concurrency and Computation: Practice and Experience, 2016. DOI: 10.1002/cpe.3746

[4] P. Zhang, Yueming Liu, and Meikang Qiu, "SNC: A Cloud Service Platform for Symbolic-Numeric Computation Using Just-In-Time Compilation," in IEEE Transactions on Cloud Computing, 2018. DOI: 10.1109/TCC.2017.2656088

[5] A. Öchsner and R. Makvandi, "Maxima—A Computer Algebra System," Finite Elements Using Maxima, 2019. DOI: 10.1007/978-3-030-17199-5_2

[6] K. Peeters, "Cadabra2: computer algebra for field theory revisited," J. Open Source Softw., 2018. DOI: 10.21105/JOSS.01118

[7] G. Malaschonok, "MathPartner computer algebra," Programming and Computer Software, 2017. DOI: 10.1134/S0361768817020086

[8] J. Stewart, "SymPy: A Computer Algebra System", 2017. DOI: 10.1017/9781108120241.009

[9] 佚名, "The Computer Algebra System OSCAR," Algorithms and Computation in Mathematics, 2025. DOI: 10.1007/978-3-031-62127-7

[10] E. Ábrahám, J. Abbott, B. Becker, et al., "Satisfiability Checking meets Symbolic Computation (Project Paper)," in International Conference on Intelligent Computer Mathematics, 2016. DOI: 10.1007/978-3-319-42547-4_3

[11] Curtis Bright, I. Kotsireas, and Vijay Ganesh, "When satisfiability solving meets symbolic computation," in Communications of the ACM, 2022. DOI: 10.1145/3500921

[12] J. Davenport, M. England, A. Griggio, et al., "Symbolic computation and satisfiability checking," J. Symb. Comput., 2020. DOI: 10.1016/J.JSC.2019.07.017

[13] Baoyu Liang, Yucheng Wang, and Chao Tong, "AI Reasoning in Deep Learning Era: From Symbolic AI to Neural–Symbolic AI," Mathematics, 2025. DOI: 10.3390/math13111707

[14] Lynn Pickering, Tereso Del Rio Almajano, M. England, et al., "Explainable AI Insights for Symbolic Computation: A case study on selecting the variable ordering for cylindrical algebraic decomposition," arXiv preprint, 10.1016/j.jsc.2023.102276, 2023

[15] B. Buchberger, "Automated programming, symbolic computation, machine learning: my personal view," Annals of Mathematics and Artificial Intelligence, 2023. DOI: 10.1007/s10472-023-09894-7

[16] Tereso del R'io and Matthew England, "Lessons on Datasets and Paradigms in Machine Learning for Symbolic Computation: A Case Study on CAD," Mathematics in Computer Science, 2024. DOI: 10.1007/s11786-024-00591-0

[17] Iordanis Kerenidis, Jonas Landman, Alessandro Luongo, et al., "q-means: A quantum algorithm for unsupervised machine learning," Neural Information Processing Systems, 2018

[18] Patrick J. Coles, S. Eidenbenz, S. Pakin, et al., "Quantum Algorithm Implementations for Beginners," in ACM Transactions on Quantum Computing, 2018. DOI: 10.1145/3517340

[19] Guang Hao Low and Yuan Su, "Quantum Eigenvalue Processing," in 2024 IEEE 65th Annual Symposium on Foundations of Computer Science (FOCS), 2024. DOI: 10.1109/FOCS61266.2024.00070

[20] N. Karjanto and H. S. Husain, "Not another computer algebra system: Highlighting wxMaxima in calculus," arXiv preprint, 10.3390/math9011317, 2021

[21] V. Velychko, A. V. Stopkin, and Olena H. Fedorenko, "USE OF COMPUTER ALGEBRA SYSTEM MAXIMA IN THE PROCESS OF TEACHING FUTURE MATHEMATICS TEACHERS," Information Technologies and Learning Tools, 2019. DOI: 10.33407/ITLT.V69I1.2284

[22] N. Karjanto and H. S. Husain, "Adopting Maxima as an Open-Source Computer Algebra System into Mathematics Teaching and Learning", 2017. DOI: 10.1007/978-3-319-62597-3_128

[23] F. Kamalov, David Santandreu, Ho-Hon Leung, et al., "Leveraging computer algebra systems in calculus: a case study with SymPy," in 2023 IEEE Global Engineering Education Conference (EDUCON), 2023. DOI: 10.1109/EDUCON54358.2023.10125196

[24] Dmitry S. Kulyabov, A. V. Korolkova, and L. A. Sevastyanov, "New Features in the Second Version of the Cadabra Computer Algebra System," Programming and Computer Software, 2019. DOI: 10.1134/S0361768819020063

[25] Dylan Peifer, M. Stillman, and Daniel Halpern-Leistner, "Learning selection strategies in Buchberger's algorithm," in International Conference on Machine Learning, 2020

[26] Rashid Barket, Matthew England, and Jurgen Gerhard, "Symbolic Integration Algorithm Selection with Machine Learning: LSTMs vs Tree LSTMs," arXiv preprint, 10.48550/arXiv.2404.14973, 2024

[27] P. Stanimirović, M. Ciric, A. Lastra, et al., "Representations and symbolic computation of generalized inverses over fields," Appl. Math. Comput., 2021. DOI: 10.1016/j.amc.2021.126287

[28] D. Prodanov, "Computation of Minimal Polynomials and Multivector Inverses in Non-Degenerate Clifford Algebras," Mathematics, 2025. DOI: 10.3390/math13071106

[29] E. Kofman, Joaquín Fernández, and Denise Marzorati, "Compact sparse symbolic Jacobian computation in large systems of ODEs," Appl. Math. Comput., 2021. DOI: 10.1016/j.amc.2021.126181

[30] Paúl Mejía, L. Martini, Felipe Grijalva, et al., "CASVI: Computer Algebra System Aimed at Visually Impaired People. Experiments," in IEEE Access, 2021. DOI: 10.1109/ACCESS.2021.3129106

[31] Paúl Mejía, L. Martini, J. Larco, et al., "CASVI: A Computer Algebra System Aimed at Visually Impaired People," in International Conference on Computers for Handicapped Persons, 2018. DOI: 10.1007/978-3-319-94277-3_89

[32] A. Zambrano, Danilo Pilacuan, Mateo N. Salvador, et al., "IrisMath: A Blind-Friendly Web-Based Computer Algebra System," in IEEE Access, 2023. DOI: 10.1109/ACCESS.2023.3281761

[33] Hayk Martiros, Aaron Miller, Nathan Bucki, et al., "SymForce: Symbolic Computation and Code Generation for Robotics," arXiv preprint, 10.15607/RSS.2022.XVIII.041, 2022

[34] Jérémy Berthomieu and J. Faugère, "A Polynomial-Division-Based Algorithm for Computing Linear Recurrence Relations," in Proceedings of the 2018 ACM International Symposium on Symbolic and Algebraic Computation, 2018. DOI: 10.1145/3208976.3209017

[35] Katsuyoshi Ohara and S. Tajima, "An Algorithm for Computing Grothendieck Local Residues I: Shape Basis Case," Mathematics in Computer Science, 2019. DOI: 10.1007/s11786-019-00399-3

[36] Jeremy F. Alm and Andrew Ylvisaker, "A fast coset-translation algorithm for computing the cycle structure of Comer relation algebras over Z/pZ," Theor. Comput. Sci., 2017. DOI: 10.1016/J.TCS.2019.05.019

[37] P. Brooksbank, J. Maglione, and James B. Wilson, "A fast isomorphism test for groups whose Lie algebra has genus 2," Journal of Algebra, 2017. DOI: 10.1016/J.JALGEBRA.2016.12.007

[38] Joseph Krasil'shchik, A. Verbovetsky, and R. Vitolo, "The Symbolic Computation of Integrability Structures for Partial Differential Equations," Texts & Monographs in Symbolic Computation, 2018. DOI: 10.1007/978-3-319-71655-8

[39] A. Cheviakov, "Symbolic computation of equivalence transformations and parameter reduction for nonlinear physical models," Comput. Phys. Commun., 2017. DOI: 10.1016/j.cpc.2017.06.013

[40] Ozkan Guner and A. Bekir, "A novel method for nonlinear fractional differential equations using symbolic computation," Waves in Random and Complex Media, 2017. DOI: 10.1080/17455030.2016.1213462

[41] L. Cardelli, M. Tribastone, Max Tschaikowski, et al., "Symbolic computation of differential equivalences," in Proceedings of the 43rd Annual ACM SIGPLAN-SIGACT Symposium on Principles of Programming Languages, 2016. DOI: 10.1145/2837614.2837649

[42] J. Ablinger, "Computing the Inverse Mellin Transform of Holonomic Sequences using Kovacic's Algorithm," arXiv preprint, 10.22323/1.290.0001, 2018

[43] C. Raab, "Symbolic Computation of Parameter Integrals," in Proceedings of the 2016 ACM International Symposium on Symbolic and Algebraic Computation, 2016. DOI: 10.1145/2930889.2930940

[44] M. Masjed‐Jamei and W. Koepf, "Symbolic computation of some power-trigonometric series," J. Symb. Comput., 2017. DOI: 10.1016/j.jsc.2016.03.004

[45] Zihao Wu, J. Boehm, Rourou Ma, et al., "NeatIBP 1.0, a package generating small-size integration-by-parts relations for Feynman integrals," Comput. Phys. Commun., 2023. DOI: 10.1016/j.cpc.2023.108999

[46] Wen Chen, "Reduction of Feynman integrals in the parametric representation II: reduction of tensor integrals," The European Physical Journal. C, Particles and Fields, 2019. DOI: 10.1140/epjc/s10052-021-09036-5

[47] D. Hildenbrand, "Introduction to Geometric Algebra Computing", 2018. DOI: 10.1201/9781315152172

[48] M. Papaefthymiou, D. Hildenbrand, and G. Papagiannakis, "An inclusive Conformal Geometric Algebra GPU animation interpolation and deformation algorithm," The Visual Computer, 2016. DOI: 10.1007/s00371-016-1270-8

[49] M. Papaefthymiou and G. Papagiannakis, "Real‐time rendering under distant illumination with conformal geometric algebra," Mathematical Methods in the Applied Sciences, 2018. DOI: 10.1002/mma.4560

[50] Wenyuan Wang and K. Doğançay, "Transient Performance Analysis of Geometric Algebra Least Mean Square Adaptive Filter," in IEEE Transactions on Circuits and Systems II: Express Briefs, 2021. DOI: 10.1109/TCSII.2021.3069390

[51] Pengcheng Yin, Ji-yi Zhang, Xiying Sun, et al., "A Vertex Concavity-Convexity Detection Method for Three-Dimensional Spatial Objects Based on Geometric Algebra," ISPRS Int. J. Geo Inf., 2020. DOI: 10.3390/ijgi9010025

[52] Yanping Li, "A Novel Fast Retina Keypoint Extraction Algorithm for Multispectral Images Using Geometric Algebra," in IEEE Access, 2019. DOI: 10.1109/ACCESS.2019.2954081

[53] Xin-Yi Gao, Yongjiang Guo, and Wen-Rui Shan, "Water-wave symbolic computation for the Earth, Enceladus and Titan: The higher-order Boussinesq-Burgers system, auto- and non-auto-Bäcklund transformations," Appl. Math. Lett., 2020. DOI: 10.1016/j.aml.2019.106170

[54] Xin-Yi Gao, Yongjiang Guo, and Wen-Rui Shan, "Symbolic computation on a (2+1)-dimensional generalized variable-coefficient Boiti–Leon–Pempinelli system for the water waves," Chaos Solitons & Fractals, 2021. DOI: 10.1016/J.CHAOS.2021.111066

[55] Xin-Yi Gao, Xiu-Qing Chen, Y. Guo, et al., "Cosmic-Plasma Environment, Singular Manifold and Symbolic Computation for a Variable-Coefficient (2+1)-Dimensional Zakharov-Kuznetsov-Burgers Equation," Qualitative Theory of Dynamical Systems, 2025. DOI: 10.1007/s12346-024-01200-y

[56] Jingyuan Yang and W. Ma, "Lump solutions to the BKP equation by symbolic computation," International Journal of Modern Physics B, 2016. DOI: 10.1142/S0217979216400282

[57] Xin-Yi Gao, "In plasma physics and fluid dynamics: Symbolic computation on a (2+1)-dimensional variable-coefficient Sawada-Kotera system," Appl. Math. Lett., 2024. DOI: 10.1016/j.aml.2024.109262

[58] Xin-Yi Gao, "Symbolic Computation on a (2+1)-Dimensional Generalized Nonlinear Evolution System in Fluid Dynamics, Plasma Physics, Nonlinear Optics and Quantum Mechanics," Qualitative Theory of Dynamical Systems, 2024. DOI: 10.1007/s12346-024-01045-5

[59] Xin-Yi Gao, "Density-fluctuation symbolic computation on the (3+1)-dimensional variable-coefficient Kudryashov-Sinelshchikov equation for a bubbly liquid with experimental support," Modern Physics Letters B, 2016. DOI: 10.1142/S0217984916502171

[60] Xin-Yi Gao, Y. Guo, and Wen-Rui Shan, "Oceanic shallow-water symbolic computation on a (2+1)-dimensional generalized dispersive long-wave system," Physics Letters A, 2022. DOI: 10.1016/j.physleta.2022.128552

[61] W. Ma, "Lump and interaction solutions to linear PDEs in 2+1 dimensions via symbolic computation," Modern Physics Letters B, 2019. DOI: 10.1142/s0217984919504578

[62] Sumayah Batwa and W. Ma, "Lump solutions to a generalized Hietarinta-type equation via symbolic computation," Frontiers of Mathematics in China, 2020. DOI: 10.1007/s11464-020-0844-y

[63] S Kumar and B. Mohan, "A direct symbolic computation of center-controlled rogue waves to a new Painlevé-integrable (3+1)-D generalized nonlinear evolution equation in plasmas," Nonlinear Dynamics, 2023. DOI: 10.1007/s11071-023-08683-5

[64] S Kumar, B. Mohan, and Raj Kumar, "Newly formed center-controlled rouge wave and lump solutions of a generalized (3+1)-dimensional KdV-BBM equation via symbolic computation approach," Physica Scripta, 2023. DOI: 10.1088/1402-4896/ace862

[65] Yuan Shen, B. Tian, and Tian-Yu Zhou, "In nonlinear optics, fluid dynamics and plasma physics: symbolic computation on a (2+1)-dimensional extended Calogero–Bogoyavlenskii–Schiff system," The European Physical Journal Plus, 2021. DOI: 10.1140/epjp/s13360-021-01323-0

[66] E. V. Vorozhtsov and S. Kiselev, "Comparative Study of the Accuracy of Higher-Order Difference Schemes for Molecular Dynamics Problems Using the Computer Algebra Means," Computer Algebra in Scientific Computing, 2020. DOI: 10.1007/978-3-030-60026-6_35

[67] Y. Blinkov and A. Rebrina, "Investigation of Difference Schemes for Two-Dimensional Navier–Stokes Equations by Using Computer Algebra Algorithms," Programming and Computer Software, 2023. DOI: 10.1134/S0361768823010024

[68] Pierre Cordesse and M. Massot, "Entropy supplementary conservation law for non-linear systems of PDEs with non-conservative terms: application to the modelling and analysis of complex fluid flows using computer algebra," arXiv preprint, 10.4310/CMS.2020.V18.N2.A10, 2019

[69] M. MacCallum, "Computer algebra in gravity research," Living Reviews in Relativity, 2018. DOI: 10.1007/s41114-018-0015-6

[70] T. Birkandan, Ceren Güzelgün, Elif Şirin, et al., "Symbolic and numerical analysis in general relativity with open source computer algebra systems," General Relativity and Gravitation, 2017. DOI: 10.1007/s10714-018-2486-x

[71] A. V. Korolkova, M. Gevorkyan, Arseny V. Fedorov, et al., "Symbolic Studies of Maxwell’s Equations in Space-Time Algebra Formalism," Programming and Computer Software, 2024. DOI: 10.1134/S0361768824020087

[72] Xiaoyong Jiang, Langyue Huang, Mengle Peng, et al., "Nonlinear model predictive control using symbolic computation on autonomous marine surface vehicle," Journal of Marine Science and Technology, 2021. DOI: 10.1007/s00773-021-00847-5

[73] R. Devaraj, A. Sarkar, and S. Biswas, "Supervisory Control Approach and its Symbolic Computation for Power-Aware RT Scheduling," in IEEE Transactions on Industrial Informatics, 2019. DOI: 10.1109/TII.2018.2824564

[74] T. Do, V. Vu, and Zhaoheng Liu, "Symbolic differentiation algorithm for inverse dynamics of serial robots with flexible joints," Journal of Mechanisms and Robotics, 2021. DOI: 10.1115/1.4051355

[75] D. Chablat, Rémi Prébet, M. S. E. Din, et al., "Deciding Cuspidality of Manipulators through Computer Algebra and Algorithms in Real Algebraic Geometry," in Proceedings of the 2022 International Symposium on Symbolic and Algebraic Computation, 2022. DOI: 10.1145/3476446.3535477

[76] S. Gutnik and V. Sarychev, "Application of Computer Algebra Methods to Investigate the Dynamics of the System of Two Connected Bodies Moving along a Circular Orbit," Programming and Computer Software, 2019. DOI: 10.1134/S0361768819020051

[77] S. Gutnik and V. Sarychev, "Application of computer algebra methods for investigation of stationary motions of a gyrostat satellite," Programming and Computer Software, 2017. DOI: 10.1134/S0361768817020050

[78] S. Gutnik and V. Sarychev, "Application of Computer Algebra Methods to Investigation of Stationary Motions of a System of Two Connected Bodies Moving in a Circular Orbit," Computational Mathematics and Mathematical Physics, 2020. DOI: 10.1134/S0965542520010091

[79] S. Gutnik and V. Sarychev, "Computer Algebra Methods for Searching the Stationary Motions of the Connected Bodies System Moving in Gravitational Field," Mathematics in Computer Science, 2022. DOI: 10.1007/s11786-022-00535-6

[80] A. Prokopenya, M. Minglibayev, and S. Shomshekova, "Applications of Computer Algebra in the Study of the Two-Planet Problem of Three Bodies with Variable Masses," Programming and Computer Software, 2019. DOI: 10.1134/S0361768819020087

[81] A. Prokopenya, M. Minglibayev, and Aiken Kosherbayeva, "Derivation of Evolutionary Equations in the Many-Body Problem with Isotropically Varying Masses Using Computer Algebra," Programming and Computer Software, 2022. DOI: 10.1134/S0361768822020098

[82] F. Mogavero and J. Laskar, "The origin of chaos in the Solar System through computer algebra," Astronomy &amp; Astrophysics, 2022. DOI: 10.1051/0004-6361/202243327

[83] A. Perminov and E. Kuznetsov, "The Implementation of Hori–Deprit Method to the Construction Averaged Planetary Motion Theory by Means of Computer Algebra System Piranha," Mathematics in Computer Science, 2019. DOI: 10.1007/s11786-019-00441-4

[84] A. Perminov and E. Kuznetsov, "The construction of averaged planetary motion theory by means of computer algebra system Piranha.," arXiv preprint, 2018

[85] M. Tamur, Y. S. Ksumah, D. Juandi, et al., "A Meta-Analysis of the Past Decade of Mathematics Learning Based on the Computer Algebra System (CAS)," in Journal of Physics: Conference Series, 2021. DOI: 10.1088/1742-6596/1882/1/012060

[86] Fatih Karakuş and Bünyamin Aydın, "The Effects of Computer Algebra System on Undergraduate Students’ Spatial Visualization Skills in a Calculus Course," Malaysian Online Journal of Educational Technology, 2017

[87] N. Karjanto and S. Lee, "Flipped classroom in Introductory Linear Algebra by utilizing Computer Algebra System {\sl SageMath} and a free electronic book," arXiv preprint, 2017

[88] A. Olenev, K. A. Kirichek, E. V. Potekhina, et al., "Capabilities of the Maple computer algebra system in the study of set theory and combinatorics," in Journal of Physics: Conference Series, 2020. DOI: 10.1088/1742-6596/1691/1/012097

[89] K. T. Tyncherov, A. Olenev, M. V. Selivanova, et al., "Modeling set theory laws using maple computer algebra system," in Journal of Physics: Conference Series, 2020. DOI: 10.1088/1742-6596/1661/1/012086

[90] N. Eyrikh, N. Markova, Aijarkyn Zhunusakunova, et al., "Using Computer Algebra System Maple for Teaching the Basics of the Finite Element Method," in 2021 International Conference on Quality Management, Transport and Information Security, Information Technologies (IT&QM&IS), 2021. DOI: 10.1109/ITQMIS53292.2021.9642878

[91] Wlodzimierz Wojas and Jan Krupa, "Teaching Students Nonlinear Programming with Computer Algebra System," Mathematics in Computer Science, 2018. DOI: 10.1007/s11786-018-0374-0

[92] N. Lohgheswary, Z. Nopiah, Effandi Zakaria, et al., "Incorporating Computer Algebra System in Differential Equations Syllabus," Journal of Engineering and Applied Sciences, 2019. DOI: 10.36478/jeasci.2019.7475.7480

[93] J. Bécar, J. Canonne, L. Vermeiren, et al., "A METHOD TO CONNECT MATHEMATICS AND SCIENCES USING A COMPUTER ALGEBRA SYSTEM", 2017. DOI: 10.21125/EDULEARN.2017.2336

[94] Katherine Herbert, D. Demskoi, and Kerrie Cullis, "Creating mathematics formative assessments using LaTeX, PDF forms and computer algebra," Australasian Journal of Educational Technology, 2018. DOI: 10.14742/AJET.4539

[95] E. Ábrahám, J. Abbott, B. Becker, et al., "Satisfiability checking and symbolic computation," in ACM Commun. Comput. Algebra, 2016. DOI: 10.1145/3055282.3055285

[96] Edward Zulkoski, Curtis Bright, A. Heinle, et al., "Combining SAT Solvers with Computer Algebra Systems to Verify Combinatorial Conjectures," Journal of Automated Reasoning, 2016. DOI: 10.1007/s10817-016-9396-y

[97] Edward Zulkoski, Vijay Ganesh, and K. Czarnecki, "MathCheck: A Math Assistant via a Combination of Computer Algebra Systems and SAT Solvers," CADE, 2016. DOI: 10.1007/978-3-319-21401-6_41

[98] Curtis Bright, I. Kotsireas, A. Heinle, et al., "Complex Golay Pairs up to Length 28: A Search via Computer Algebra and Programmatic SAT," arXiv preprint, 10.1016/j.jsc.2019.10.013, 2019

[99] Zhengyu Li, Curtis Bright, and Vijay Ganesh, "A SAT Solver and Computer Algebra Attack on the Minimum Kochen-Specker Problem," in International Joint Conference on Artificial Intelligence, 2023. DOI: 10.24963/ijcai.2024/210

[100] Zhengyu Li, Curtis Bright, and Vijay Ganesh, "A SAT Solver and Computer Algebra Attack on the Minimum Kochen-Specker Problem (Student Abstract)," in AAAI Conference on Artificial Intelligence, 2024. DOI: 10.1609/aaai.v38i21.30472

[101] Daniela Kaufmann and Armin Biere, "Improving AMulet2 for verifying multiplier circuits using SAT solving and computer algebra," International Journal on Software Tools for Technology Transfer, 2023. DOI: 10.1007/s10009-022-00688-6

[102] Alireza Mahzoon, Daniel Große, Christoph Scholl, et al., "Formal Verification of Modular Multipliers using Symbolic Computer Algebra and Boolean Satisfiability," in 2022 59th ACM/IEEE Design Automation Conference (DAC), 2022. DOI: 10.1145/3489517.3530605

[103] Charles Fox, N. Tran, Nikki Nacion, et al., "Incorporating background knowledge in symbolic regression using a computer algebra system," Machine Learning: Science and Technology, 2023. DOI: 10.1088/2632-2153/ad4a1e

[104] Yuhong Sun, Ting Huang, Jinghui Zhong, et al., "Symbolic Regression-Assisted Offline Data-Driven Evolutionary Computation," in IEEE Transactions on Evolutionary Computation, 2025. DOI: 10.1109/TEVC.2024.3482326

[105] Abdulhakim Alnuqaydan, S. Gleyzer, and H. Prosper, "SYMBA: symbolic computation of squared amplitudes in high energy physics with machine learning," Machine Learning: Science and Technology, 2022. DOI: 10.1088/2632-2153/acb2b2

[106] Giuseppe Pisano, Giovanni Ciatto, Roberta Calegari, et al., "Neuro-symbolic Computation for XAI: Towards a Unified Model," in Workshop From Objects to Agents, 2020

[107] Daan Camps, Lin Lin, R. Beeumen, et al., "Explicit Quantum Circuits for Block Encodings of Certain Sparse Matrice," arXiv preprint, 10.48550/arXiv.2203.10236, 2022

[108] Changpeng Shao, "Computing Eigenvalues of Diagonalizable Matrices on a Quantum Computer," in ACM Transactions on Quantum Computing, 2022. DOI: 10.1145/3527845

[109] Binh Duc Nguyen, "Simulation of Quantum Computation via MAGMA Computational Algebra System," International Journal of Advanced Trends in Computer Science and Engineering, 2020. DOI: 10.30534/ijatcse/2020/130922020

[110] Stasiu Wolanski and Ben Barber, "Ambiguity Clustering: an accurate and efficient decoder for qLDPC codes", 2024

[111] Laigang Guo, R. Yeung, and Xiao-Shan Gao, "Proving Information Inequalities and Identities with Symbolic Computation," in 2022 IEEE International Symposium on Information Theory (ISIT), 2022. DOI: 10.1109/ISIT50566.2022.9834774

[112] Madison Cotteret, Hugh Greatorex, Alpha Renner, et al., "Distributed representations enable robust multi-timescale symbolic computation in neuromorphic hardware," Neuromorphic Computing and Engineering, 2024. DOI: 10.1088/2634-4386/ada851

[113] M. Heddes, Igor Nunes, T. Givargis, et al., "Hyperdimensional computing: a framework for stochastic computation and symbolic AI," Journal of Big Data, 2024. DOI: 10.1186/s40537-024-01010-8

[114] P. M. Furlong and Chris Eliasmith, "Modelling neural probabilistic computation using vector symbolic architectures," Cognitive Neurodynamics, 2023. DOI: 10.1007/s11571-023-10031-7

[115] M. Kavouras, Kyriaki D. Tsilika, and Athanasios Exadactylos, "A computer algebra system approach in gene expression analysis," Progress in Industrial Ecology, An International Journal, 2017. DOI: 10.1504/PIE.2017.10007265

[116] G. Sarma and Nick J. Hay, "Robust Computer Algebra, Theorem Proving, and Oracle AI," Informatica (Slovenia), 2017. DOI: 10.2139/SSRN.3038545

[117] René Thiemann, R. Bottesch, Jose Divasón, et al., "Formalizing the LLL Basis Reduction Algorithm and the LLL Factorization Algorithm in Isabelle/HOL," Journal of Automated Reasoning, 2020. DOI: 10.1007/s10817-020-09552-1

[118] Christopher W. Brown, Z. Kovács, T. Recio, et al., "Is Computer Algebra Ready for Conjecturing and Proving Geometric Inequalities in the Classroom?," Mathematics in Computer Science, 2022. DOI: 10.1007/s11786-022-00532-9

[119] Z. Pardos and Shreya Bhandari, "Learning gain differences between ChatGPT and human tutor generated algebra hints," arXiv preprint, 10.48550/arXiv.2302.06871, 2023

[120] P. Houston and N. Sime, "Automatic symbolic computation for discontinuous Galerkin finite element methods," arXiv preprint, 10.1137/17M1129751, 2018