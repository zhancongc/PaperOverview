# computer algebra system的算法实现及应用

# 计算机代数系统的算法实现及应用：文献综述

## 1. 引言

计算机代数系统（Computer Algebra System，CAS）是一类能够以符号形式处理数学表达式、执行代数运算、求解方程、进行微积分计算以及完成其他数学操作的软件系统。自20世纪60年代诞生以来，CAS已从早期的专用符号计算程序演变为功能强大、涵盖广泛数学领域的综合性工具，如Maple、Mathematica、Maxima、SymPy等。这些系统不仅在纯数学研究中发挥关键作用，更在物理学、工程学、计算机科学、教育等众多领域得到广泛应用[1, 2, 3]。

随着计算技术的飞速发展，CAS的算法实现不断优化，应用边界持续拓展。一方面，核心算法如Gröbner基计算、符号积分、微分方程求解等经历了从理论基础到高效实现的漫长演进[4, 5, 6]。另一方面，CAS与其他计算范式的交叉融合催生了新的研究方向，如符号计算与可满足性（SAT）求解的结合[7, 8, 9]、与机器学习的交互[10]、以及量子计算对代数算法的重塑[11, 12, 13]。此外，CAS在具体学科中的应用日益深入，从求解非线性偏微分方程[14, 15, 16]到验证硬件电路[5, 17]，从辅助数学教学[18, 19]到支持科学可视化[20, 21]，其影响力不断扩大。

本综述旨在系统梳理近年来计算机代数系统在**算法实现**和**跨领域应用**两方面的研究进展。通过对近300篇相关文献的分析，我们将重点探讨以下主题：（1）CAS核心算法的创新与优化；（2）CAS在数学与理论物理中的前沿应用；（3）CAS在工程与科学计算中的实践；（4）CAS在教育与可视化中的角色；（5）量子计算、人工智能与符号计算融合的新兴趋势。最后，本文将指出当前研究的不足与未来可能的发展方向。

## 2. 计算机代数系统的核心算法与实现

计算机代数系统的核心在于其处理符号数学问题的算法。近年来，研究者们在算法的效率、可靠性和通用性方面取得了显著进展，特别是在多项式代数、自动推理、硬件验证及与数值方法的结合上。

### 2.1 多项式代数与Gröbner基算法
Gröbner基是多项式理想的标准生成集，在代数几何、编码理论、机器人运动学等领域有根本性作用。传统Buchberger算法在变量选择和S-对处理上存在优化空间。Peifer等人[4]首次将强化学习引入Buchberger算法，训练智能体学习S-对选择策略，在特定问题域上超越了传统启发式方法，展示了机器学习优化符号计算算法的潜力。在实现层面，HPC‐GAP项目[22]通过设计新的并行抽象和领域特定骨架，成功将GAP系统扩展到高性能计算环境，在多达32000核心的系统上实现了良好的可扩展性，为解决大规模符号计算问题提供了基础设施支持。

### 2.2 符号计算与自动推理的结合
符号计算与布尔可满足性（SAT）求解的交叉是近年来的研究热点。Abraham等人[7]发起的SC²项目旨在加强这两个社区的联系，推动算术理论决策过程的发展。Zulkoski等人[8]开发了MathCheck系统，将CAS与SAT求解器结合以验证组合猜想，证明了这种混合方法的有效性。Bright等人[9]进一步探讨了“可满足性求解遇上符号计算”的科学内涵，指出这种结合能解决传统单一方法难以处理的问题。Li等人[23]则利用SAT求解器和计算机代数系统（CAS）协同攻击最小Kochen-Specker问题，通过生成可验证的证明，将三维空间中的KS向量系统下界提升至24，展示了组合搜索与代数推理结合的力量。

### 2.3 形式验证与硬件正确性证明
在硬件设计，特别是密码学和残数数系统（RNS）中，模块化乘法器的正确性验证至关重要。Mahzoon等人[17]提出了一种结合符号计算机代数（SCA）和布尔可满足性（SAT）的形式验证器，用于证明\(2^n-1\)和\(2^n+1\)模块化乘法器的正确性。Kaufmann和Biere[6]开发了AMulet2工具，通过将乘法器建模为多项式集并应用基于Gröbner基的预处理技术，实现了整数乘法器的全自动验证。Kaufmann等人还提出了一种增量列式验证算术电路的方法，利用Gröbner基进行多项式推理，显著提高了验证效率。这些工作表明，符号计算方法已成为确保复杂硬件电路功能正确性的重要手段。

### 2.4 符号-数值混合计算
纯符号计算在处理大规模或复杂问题时可能遇到表达式膨胀问题，而纯数值计算则可能丢失重要的结构性信息。符号-数值混合计算旨在结合二者优势。Zhang等人[24]提出了SNC云服务平台，利用即时编译技术为符号-数值计算提供高效执行环境。Iavernaro等人[25]利用“无穷计算机”算术，提出了一种计算高阶Lie导数的新方法，即使函数的解析表达式未知也能工作，为符号与数值方法之间架起了桥梁。England等人[26]则通过符号计算与数值连续化方法的结合，可视化和分析了生物网络中多稳态性的参数区域，展示了混合方法在系统生物学中的应用价值。

## 3. 计算机代数系统在数学与理论物理中的应用

计算机代数系统已成为数学和理论物理研究中不可或缺的工具，特别是在非线性科学、可积系统、广义相对论和粒子物理等领域，CAS极大地促进了复杂问题的解析求解和性质分析。

### 3.1 非线性偏微分方程与孤子理论
符号计算在求解非线性偏微分方程（PDE）方面成果丰硕。Gao及其合作者进行了一系列系统性工作，将符号计算方法应用于描述流体动力学、等离子体物理和非线性光学的各类(2+1)维和(3+1)维系统。例如，他们对变系数Sawada-Kotera系统[14]、广义非线性演化系统[15]、广义变系数Boiti–Leon–Pempinelli水波系统[16]以及广义色散长波系统[27]进行了研究，构造了双线性形式、Bäcklund变换和精确孤子解。Kumar等人[5, 28]利用符号计算研究了(3+1)维非线性演化方程中的中心可控畸形波（rogue wave）和 lump 解，这些解在等离子体和流体力学中有重要意义。Ma等人[13, 29]则专注于线性PDE的 lump 解和相互作用解，揭示了线性系统中也存在丰富的局域波结构。

### 3.2 可积结构与对称性分析
探究微分方程的可积结构是数学物理的核心课题。Krasil'shchik等人[30]深入探讨了偏微分方程可积结构的符号计算。Cheviakov[31]提出了计算非线性物理模型等价变换和参数约化的系统化符号计算程序，并应用于超弹性纤维增强介质中的非线性波方程。Adem等人[25, 32]运用李对称分析和扩展tanh方法，研究耦合KP方程和广义色散水波系统的精确解、对称约化和守恒律。这些工作表明，CAS不仅能帮助寻找特定解，还能系统化地研究方程的深层数学结构。

### 3.3 引力理论与广义相对论
在广义相对论和引力研究中，张量计算的复杂性使得计算机代数成为必需。MacCallum[33]全面综述了计算机代数在引力研究中的应用历史、现有工具包（如Cadabra2、xAct、GRTensorII）以及主要应用方向。Cadabra2系统[34]专门为张量场论问题设计，支持拉格朗日量操作、运动方程计算和对称性分析，其输入格式接近标准数学记号，降低了使用门槛。Birkandan等人[28]比较了SageMath（含SageManifolds）、Maxima（含ctensor）和Python（含GraviPy）在广义相对论计算中的性能，并利用SageManifolds推导和分析了无质量Klein-Gordon方程的解和测地线运动，展示了开源CAS在引力研究中的实用价值。

### 3.4 粒子物理与场论
在高能物理中，CAS被广泛用于费曼图计算、振幅简化和非微扰计算。Wu等人[35]开发了NeatIBP包，利用零化子和模交技术为费曼积分生成小尺寸的积分-by-parts（IBP）关系，比标准的Laporta算法产生的系统更小。Chen[36]进一步发展了参数表示下费曼积分的约化方法，包括张量积分的处理。Alnuqaydan等人[37]则探索了机器学习在高能物理符号计算中的应用，开发了SYMBA模型，使用Transformer架构预测散射振幅的平方，速度比传统符号计算框架快数个数量级，且准确率超过97%，为自动化计算开辟了新途径。Peeters[34]开发的Cadabra2系统也特别适用于场论中的符号计算。

## 4. 计算机代数系统在工程与科学计算中的应用

超越纯理论数学，CAS在解决工程和跨学科科学计算问题中发挥着越来越重要的作用，涉及控制理论、机器人学、计算流体力学、系统优化等多个领域。

### 4.1 机器人学与运动规划
机器人运动学分析常涉及复杂的多项式系统求解。Martiros等人[38]推出了SymForce库，专为机器人学中的符号计算和代码生成设计，结合了符号数学的开发速度与自动生成优化代码的性能，可用于计算机视觉、运动规划和控制中的非线性优化。Capco等人[39]利用计算机代数分析了“Universal Robots”系列机器人的运动学奇点，通过半代数集连通性查询算法，证明了该系列通用机器人奇点互补集的连通分量数为8。Chablat等人[40]则通过计算机代数和实代数几何算法，解决了判断机械手是否具有尖点性的决策问题。

### 4.2 控制系统与优化
符号计算为控制系统设计和优化提供了强有力的工具。Jiang等人[41]将符号计算用于自主海洋水面船舶的非线性模型预测控制（NMPC）。Devaraj等人[42]提出了用于功耗感知实时调度的监控控制方法及其符号计算实现，通过基于二叉决策图的符号计算控制状态空间复杂性，保证了多核平台上满足峰值功率约束。Kim等人[43]开发了一个集成接口，利用符号计算、方差分析和代理模型，对复杂系统（如战斗车辆）进行高效设计优化，显著缩短了优化时间。

### 4.3 计算流体力学与科学计算
在计算流体力学中，CAS可用于推导和验证数值格式。Houston和Sime[44]为间断伽辽金有限元方法实现了自动符号计算，利用统一形式语言（UFL）在FEniCS包中实现了高阶抽象，简化了耦合非线性PDE系统的离散化。Vorozhtsov等人[45]使用计算机代数工具比较了分子动力学问题中高阶差分格式的精度。Cordesse[46]将计算机代数应用于包含非守恒项的非线性PDE系统的熵补充守恒律建模与分析，用于复杂流体流动研究。这些工作凸显了CAS在连接连续数学理论与离散数值算法之间的桥梁作用。

### 4.4 几何代数在工程中的算法实现
几何代数提供了一种统一的数学框架来处理几何对象和变换。Hildenbrand[47]系统介绍了几何代数计算的基本原理和应用。Wang等人[48]对几何代数最小均方自适应滤波器进行了瞬态性能分析，为3D点云配准和计算机视觉中的旋转估计提供了理论 foundation。Papaefthymiou等人[45, 49]提出了基于共形几何代数的GPU动画插值与变形算法，以及远距离照明下的实时渲染方法。Skala[50]利用几何代数优化了E²空间中的直线和线段裁剪算法，避免了向欧氏空间坐标的转换，提升了效率。

## 5. 计算机代数系统在教育与可视化中的角色

计算机代数系统不仅是研究工具，也是强大的教学辅助和知识可视化平台，特别是在数学、物理和工程教育中，CAS能够帮助学生深化概念理解、克服计算障碍、并探索复杂现象。

### 5.1 数学教学与概念深化
大量研究表明，CAS能有效增强学生对数学概念的理解。Tamur等人[18]对过去十年基于CAS的数学学习进行了元分析，涵盖31篇文章36个效应值，发现CAS对学生的数学能力有大的积极影响（效应值ES=0.89）。Zeynivandnezhad和Bates[51]探讨了在微分方程教学中使用CAS来阐明数学思维。Olenev等人[19]展示了如何利用Maple CAS帮助学生克服数学归纳法证明中的代数变换困难，将注意力集中在理解归纳原理本身。Karjanto和Husain[52]则专门介绍了wxMaxima在微积分教学中的应用，强调其在增强概念理解方面的优势与局限。

### 5.2 动态几何与可视化
将动态几何软件与CAS结合，可以创建强大的探索和证明环境。Hasek[53]探讨了动态几何软件辅以CAS作为证明工具的价值。Petkovic等人[20, 21]利用符号计算和计算机图形学作为开发和研究生根新方法的工具，特别是针对未知重数的多根情况。这些工具使学生能够直观地观察数学对象的行为和算法的收敛过程，将抽象概念具象化。

### 3.3 无障碍访问与包容性教育
确保CAS对所有学习者（包括视障人士）的可访问性是一个重要的伦理和技术挑战。Mejía等人[54, 55]开发了CASVI系统，这是一个基于Maxima引擎、面向视障人士的计算机代数系统，实验表明视障用户通过CASVI执行数学操作的准确率达到92%。Zambrano等人[56]进一步推出了IrisMath，一个基于Web的、对盲人友好的CAS。这些努力致力于消除STEM教育中的访问壁垒，促进教育公平。

### 5.4 特定教学工具与课程整合
众多研究探索了CAS在具体课程或主题中的应用。Herbert[57]介绍了利用LaTeX、PDF表单和计算机代数创建数学形成性评估的方法。Roanes-Lozano等人[58]回顾了计算机代数系统DERIVE的成功与影响。Karjanto等人[59, 60]探讨了在数学教学中采用Maxima作为开源CAS，以及在线性代数翻转课堂中利用SageMath和免费电子书。这些实践表明，CAS的整合需要精心设计教学活动和材料，才能最大化其教育效益。

## 6. 新兴方向：量子计算、人工智能与符号计算的融合

当前，计算机代数系统正与量子计算和人工智能等前沿领域深度融合，催生了新的算法范式、问题解决方法和跨学科研究课题。

### 6.1 量子算法与代数计算
量子计算为解决特定代数问题提供了指数级加速的潜力。Kerenidis等人[11]提出了q-means量子算法用于无监督机器学习聚类。Coles等人[12]为初学者系统介绍了量子算法的实现。Low和Su[13]提出了量子特征值处理框架，用于对块编码的非正规算子的特征值应用任意多项式变换。Shao[61]则研究了在量子计算机上计算可对角化矩阵特征值的算法。Dash等人[62]在IBM量子计算机上实现了分解大双素数和一个三素数的精确搜索算法。这些研究预示着量子计算可能在未来彻底改变某些符号计算任务的复杂度格局。

### 6.2 神经-符号人工智能
神经-符号AI旨在结合神经网络的学习能力和符号系统的推理能力。Liang等人[63]系统综述了从符号AI到神经-符号AI的发展，提出了按表示形式、任务结构和应用语境组织的三维分类法。Pickering等人[10]进行了一项案例研究，利用可解释AI技术分析机器学习模型如何选择柱形代数分解的变量序，从而启发新的启发式规则设计。Fox[64]探讨了如何在符号回归中利用计算机代数系统融入背景知识。Buchberger[65]则从个人视角阐述了自动编程、符号计算和机器学习之间的关系。这些工作试图打通连接亚符号连接主义与符号主义之间的鸿沟。

### 6.3 符号回归与自动建模
符号回归旨在从数据中发现潜在的数学表达式。Wang等人[1]提出了一种“维度同步计算”方法用于材料科学中的符号回归。Zhao等人[66]将自适应采样与符号计算（柱形代数分解）相结合，用于描述药物研发中的设计空间。Sun[67]研究了符号回归辅助的离线数据驱动进化计算。这些方法将CAS的数据处理能力与机器学习的数据驱动发现能力相结合，有望实现从数据到可解释模型的自动构建。

### 6.4 超维计算与新型计算范式
超维计算是一种受大脑信息处理启发的计算框架，它将符号表示与分布式、高维向量联系起来。Heddes等人[68]阐述了超维计算作为随机计算和符号AI框架的原理。Furlong和Eliasmith[29]利用向量符号架构对神经概率计算进行建模。Cotteret等人[69]展示了分布式表示如何在神经形态硬件中实现鲁棒的多时间尺度符号计算。这些新兴范式试图为符号处理提供新的物理实现和计算基础。

## 7. 结论：研究不足与未来方向

通过对近300篇文献的系统回顾，本文梳理了计算机代数系统在算法实现及其跨领域应用方面的最新进展。尽管成果丰硕，但当前研究仍存在一些显著不足和挑战，同时也指明了充满机遇的未来方向。

### 7.1 当前研究的主要不足
1.  **算法可扩展性瓶颈**：虽然在高性能计算方面已有探索[22]，但许多核心符号算法（如大规模Gröbner基计算）面对超大规模多项式系统时，仍受限于时间和内存复杂度，其并行化和分布式实现尚不成熟。
2.  **跨平台与互操作性障碍**：不同的CAS（如Maple、Mathematica、Maxima、SageMath）各有其语法、数据结构和内部表示，导致代码复用和结果互认困难。尽管存在OpenMath等交换标准，但广泛采用仍然不足。
3.  **验证与可靠性挑战**：符号计算本身可能产生极其复杂的中间表达式，使得最终结果的正确性验证变得困难。尤其是在形式验证领域，如何为CAS生成的证明提供可被独立验证的证明凭证（Proof Certificate）仍是一个开放问题[23]。
4.  **人工智能融合的深度不足**：目前机器学习与符号计算的结合多停留在利用ML优化算法参数或加速特定计算[37]的层面，如何实现深度互补，让神经网络学习符号推理规则，或让符号系统处理模糊、不完整信息，仍需突破。
5.  **教育与普及的差距**：尽管CAS教育应用研究众多，但其有效整合进入主流课程仍面临教师培训、评估方式、技术设施等多重障碍。针对不同能力背景学生的差异化支持工具也有待开发。

### 7.2 未来研究方向
1.  **云原生与协作式CAS**：未来CAS可能向云端服务发展，支持实时协作、版本控制和可重复研究。结合容器化技术和WebAssembly，可以实现跨平台、免安装的轻量级CAS访问。
2.  **量子-经典混合代数算法**：探索量子计算优势（如线性代数加速）与经典符号计算协同工作的混合算法，用于求解代数方程、群论和表示论中的特定难题。
3.  **神经-符号统一架构**：发展能够无缝集成神经网络子符号感知和符号系统抽象推理的统一计算架构。这可能涉及新型编程语言、知识表示和训练范式。
4.  **形式化验证的CAS内核**：开发经过形式化验证（例如使用Coq、Isabelle/HOL）的CAS核心算法库[70]，从根本上保证基本运算（如多项式化简、符号积分）的正确性，为上层应用提供可靠基石。
5.  **领域特定语言与自动生成**：针对物理、工程等特定领域，开发高级领域特定语言，并能自动编译为高效的符号-数值混合代码，如同SymForce[38]在机器人学中所做的一样，降低专家使用高级数学工具的门槛。
6.  **增强的可解释性与可视化**：结合沉浸式可视化（如VR/AR）和交互式叙事，将CAS的求解过程和结果以更直观、可解释的方式呈现，特别是在教育和高维几何等领域。

### 7.3 总结
计算机代数系统已从数学家的专用工具演变为支撑科学发现、工程创新和教育变革的通用性基础设施。其未来发展将不仅依赖于算法本身的进步，更取决于其与高性能计算、量子计算、人工智能等新兴范式的深度交融，以及对社会需求（如教育公平、科学可重复性）的积极回应。通过跨学科社区的持续合作，计算机代数系统有望在解开自然与数学的复杂性的征程中，发挥更为关键和引人入胜的作用。

---


## References

[1] A. Olenev, K. A. Kirichek, E. V. Potekhina, et al., "Capabilities of the Maple computer algebra system in the study of set theory and combinatorics," in Journal of Physics: Conference Series, 2020. DOI: 10.1088/1742-6596/1691/1/012097

[2] A. Olenev, A. Shuvaev, M V Migacheva, et al., "Using the Maple computer algebra system to study mathematical induction," in Journal of Physics: Conference Series, 2020. DOI: 10.1088/1742-6596/1691/1/012102

[3] "Computer algebra system codes," Exploring Continued Fractions, 2021. DOI: 10.1090/dol/053/27

[4] N. Lohgheswary, Z. Nopiah, Effandi Zakaria, et al., "Incorporating Computer Algebra System in Differential Equations Syllabus," Journal of Engineering and Applied Sciences, 2019. DOI: 10.36478/jeasci.2019.7475.7480

[5] N. Eyrikh, N. Markova, Aijarkyn Zhunusakunova, et al., "Using Computer Algebra System Maple for Teaching the Basics of the Finite Element Method," in 2021 International Conference on Quality Management, Transport and Information Security, Information Technologies (IT&QM&IS), 2021. DOI: 10.1109/ITQMIS53292.2021.9642878

[6] Paúl Mejía, L. Martini, Felipe Grijalva, et al., "CASVI: Computer Algebra System Aimed at Visually Impaired People. Experiments," in IEEE Access, 2021. DOI: 10.1109/ACCESS.2021.3129106

[7] Paúl Mejía, L. Martini, J. Larco, et al., "CASVI: A Computer Algebra System Aimed at Visually Impaired People," in International Conference on Computers for Handicapped Persons, 2018. DOI: 10.1007/978-3-319-94277-3_89

[8] Fereshteh Zeynivandnezhad and Rachel Bates, "Explicating mathematical thinking in differential equations using a computer algebra system," International Journal of Mathematical Education in Science and Technology, 2017. DOI: 10.1080/0020739X.2017.1409368

[9] "The Computer Algebra System OSCAR," Algorithms and Computation in Mathematics, 2025. DOI: 10.1007/978-3-031-62127-7

[10] A. Zambrano, Danilo Pilacuan, Mateo N. Salvador, et al., "IrisMath: A Blind-Friendly Web-Based Computer Algebra System," in IEEE Access, 2023. DOI: 10.1109/ACCESS.2023.3281761

[11] A. Öchsner and R. Makvandi, "Maxima—A Computer Algebra System," Finite Elements Using Maxima, 2019. DOI: 10.1007/978-3-030-17199-5_2

[12] R. Quintero-Monsebaiz and Pierre‐François Loos, "Equation generator for equation-of-motion coupled cluster assisted by computer algebra system," AIP Advances, 2023. DOI: 10.1063/5.0163846

[13] Charles Fox, N. Tran, Nikki Nacion, et al., "Incorporating background knowledge in symbolic regression using a computer algebra system," Machine Learning: Science and Technology, 2023. DOI: 10.1088/2632-2153/ad4a1e

[14] N. Karjanto and H. S. Husain, "Not another computer algebra system: Highlighting wxMaxima in calculus," arXiv preprint, 10.3390/math9011317, 2021

[15] Wlodzimierz Wojas and Jan Krupa, "Teaching Students Nonlinear Programming with Computer Algebra System," Mathematics in Computer Science, 2018. DOI: 10.1007/s11786-018-0374-0

[16] K. T. Tyncherov, A. Olenev, M. V. Selivanova, et al., "Modeling set theory laws using maple computer algebra system," in Journal of Physics: Conference Series, 2020. DOI: 10.1088/1742-6596/1661/1/012086

[17] N. Karjanto and S. Lee, "Flipped classroom in Introductory Linear Algebra by utilizing Computer Algebra System {\sl SageMath} and a free electronic book," arXiv preprint, 2017

[18] "Problems for a computer algebra system," A Bridge to Linear Algebra, 2019. DOI: 10.1142/9789811200236_0011

[19] A. Perminov and E. Kuznetsov, "The construction of averaged planetary motion theory by means of computer algebra system Piranha.," arXiv preprint, 2018

[20] Jorge García Fontán, A. Colotti, S. Briot, et al., "Computer algebra methods for polynomial system solving at the service of image-based visual servoing," in ACM Communications in Computer Algebra, 2022. DOI: 10.1145/3572867.3572871

[21] Dmitry S. Kulyabov, A. V. Korolkova, and L. A. Sevastyanov, "New Features in the Second Version of the Cadabra Computer Algebra System," Programming and Computer Software, 2019. DOI: 10.1134/S0361768819020063

[22] A. Perminov and E. Kuznetsov, "The Implementation of Hori–Deprit Method to the Construction Averaged Planetary Motion Theory by Means of Computer Algebra System Piranha," Mathematics in Computer Science, 2019. DOI: 10.1007/s11786-019-00441-4

[23] M. Gevorkyan, A. V. Korolkova, Dmitry S. Kulyabov, et al., "A Modular Extension for a Computer Algebra System," Programming and Computer Software, 2020. DOI: 10.1134/S036176882002005X

[24] M. Kavouras, Kyriaki D. Tsilika, and Athanasios Exadactylos, "A computer algebra system approach in gene expression analysis," Progress in Industrial Ecology, An International Journal, 2017. DOI: 10.1504/PIE.2017.10007265

[25] Shigeki Kobayashi and Setsuo Takato, "Cooperation of KeTCindy and Computer Algebra System," International Congress on Mathematical Software, 2016. DOI: 10.1007/978-3-319-42432-3_43

[26] M. Tamur, Y. S. Ksumah, D. Juandi, et al., "A Meta-Analysis of the Past Decade of Mathematics Learning Based on the Computer Algebra System (CAS)," in Journal of Physics: Conference Series, 2021. DOI: 10.1088/1742-6596/1882/1/012060

[27] E. Roanes-Lozano, "Looking for Compatible Routes in the Railway Interlocking System of an Overtaking Station Using a Computer Algebra System," Computer Algebra in Scientific Computing, 2020. DOI: 10.1007/978-3-030-60026-6_31

[28] kamhar ngado, R. Rosnawati, Heri Retnawati, et al., "OPTIMALISASI MOTIVASI DAN PRESTASI BELAJAR MENGGUNAKAN MOODLE BERBANTUAN COMPUTER ALGEBRA SYSTEM (CAS)", 2020. DOI: 10.24127/ajpm.v9i1.2657

[29] A. Medina-Mardones, "A computer algebra system for the study of commutativity up-to-coherent homotopies," arXiv preprint, 10.32513/asetmj/1932200819, 2021

[30] Luciano Notarfrancesco, "Arrows: a Computer Algebra System in Smalltalk", 2022

[31] M. Gevorkyan, A. V. Demidova, T. R. Velieva, et al., "Implementing a Method for Stochastization of One-Step Processes in a Computer Algebra System," Programming and Computer Software, 2018. DOI: 10.1134/S0361768818020044

[32] Jichao Song, Wei Niu, Bo Huang, et al., "Qualitative Investigation of the Lorenz-84 System Using Computer Algebra Methods," Mathematics in Computer Science, 2025. DOI: 10.1007/s11786-025-00605-5

[33] V. Velychko, A. V. Stopkin, and Olena H. Fedorenko, "USE OF COMPUTER ALGEBRA SYSTEM MAXIMA IN THE PROCESS OF TEACHING FUTURE MATHEMATICS TEACHERS," Information Technologies and Learning Tools, 2019. DOI: 10.33407/ITLT.V69I1.2284

[34] Fatih Karakuş and Bünyamin Aydın, "The Effects of Computer Algebra System on Undergraduate Students’ Spatial Visualization Skills in a Calculus Course," Malaysian Online Journal of Educational Technology, 2017

[35] T. Kitamoto, Masataka Kaneko, and Setsuo Takato, "E-learning system with Computer Algebra based on JavaScript programming language", 2018

[36] D. Eichmann, "Practical Use Of Mathcad Solving Mathematical Problems With A Computer Algebra System", 2016

[37] M. Andersen and Søren Højsgaard, "Ryacas: A computer algebra system in R," J. Open Source Softw., 2019. DOI: 10.21105/joss.01763

[38] José Luis Galán García, G. A. Venegas, P. R. Cielos, et al., "SFOPDES: A Stepwise First Order Partial Differential Equations Solver with a Computer Algebra System," Comput. Math. Appl., 2019. DOI: 10.1016/J.CAMWA.2019.05.010

[39] R. Hasek, "Dynamic Geometry Software Supplemented with a Computer Algebra System as a Proving Tool," Mathematics in Computer Science, 2018. DOI: 10.1007/s11786-018-0369-x

[40] A. Reznik and A. Soloviev, "Methods, algorithms and programs of computer algebra in problems of registration and analysis of random point structures," Computer Optics, 2023. DOI: 10.18287/2412-6179-co-1330

[41] S. Gutnik and V. Sarychev, "Application of Computer Algebra Methods to Investigate the Dynamics of the System of Two Connected Bodies Moving along a Circular Orbit," Programming and Computer Software, 2019. DOI: 10.1134/S0361768819020051

[42] Tatsuyoshi Hamada, Yoshiyuki Nakagawa, and Makoto Tamura, "Method to Create Multiple Choice Exercises for Computer Algebra System," Mathematical Software – ICMS 2020, 2020. DOI: 10.1007/978-3-030-52200-1_41

[43] J. Bécar, J. Canonne, L. Vermeiren, et al., "A METHOD TO CONNECT MATHEMATICS AND SCIENCES USING A COMPUTER ALGEBRA SYSTEM", 2017. DOI: 10.21125/EDULEARN.2017.2336

[44] R. Behrends, K. Hammond, V. Janjić, et al., "HPC‐GAP: engineering a 21st‐century high‐performance computer algebra system," Concurrency and Computation: Practice and Experience, 2016. DOI: 10.1002/cpe.3746

[45] N. Karjanto and H. S. Husain, "Adopting Maxima as an Open-Source Computer Algebra System into Mathematics Teaching and Learning", 2017. DOI: 10.1007/978-3-319-62597-3_128

[46] Andreas Öchsner and R. Makvandi, "Maxima—A Computer Algebra System," Finite Elements for Truss and Frame Structures, 2018. DOI: 10.1007/978-3-319-94941-3_2

[47] J. Stewart, "SymPy: A Computer Algebra System", 2017. DOI: 10.1017/9781108120241.009

[48] R. Bayramov, Y. A. Blinkov, I. Levichev, et al., "Analytical Study of Cubature Formulas on a Sphere in Computer Algebra Systems," Computational Mathematics and Mathematical Physics, 2023. DOI: 10.1134/S0965542523010050

[49] S. Gutnik and V. Sarychev, "Application of Computer Algebra Methods to Investigation of Stationary Motions of a System of Two Connected Bodies Moving in a Circular Orbit," Computational Mathematics and Mathematical Physics, 2020. DOI: 10.1134/S0965542520010091

[50] Zhengyu Li, Curtis Bright, and Vijay Ganesh, "A SAT Solver and Computer Algebra Attack on the Minimum Kochen-Specker Problem," in International Joint Conference on Artificial Intelligence, 2023. DOI: 10.24963/ijcai.2024/210

[51] E. Roanes-Lozano, José Luis Galán García, and Carmen Solano-Macías, "Some Reflections About the Success and Impact of the Computer Algebra System DERIVE with a 10-Year Time Perspective," Mathematics in Computer Science, 2019. DOI: 10.1007/s11786-019-00404-9

[52] Andreas Öchsner and R. Makvandi, "Maxima—A Computer Algebra System," Plane Finite Elements for Two-Dimensional Problems, 2021. DOI: 10.1007/978-3-030-89550-1_2

[53] V. I. Kuzovatov and A. A. Kytmanov, "On the Calculation of the Number of Real Roots of a System of Nonalgebraic Equations Using Computer Algebra," Programming and Computer Software, 2025. DOI: 10.1134/S0361768824700877

[54] A. Baddour, M. Gambaryan, L. Gonzalez, et al., "On Implementation of Numerical Methods for Solving Ordinary Differential Equations in Computer Algebra Systems," Programming and Computer Software, 2023. DOI: 10.1134/S0361768823020044

[55] F. Kamalov, David Santandreu, Ho-Hon Leung, et al., "Leveraging computer algebra systems in calculus: a case study with SymPy," in 2023 IEEE Global Engineering Education Conference (EDUCON), 2023. DOI: 10.1109/EDUCON54358.2023.10125196

[56] S. Gutnik and V. Sarychev, "Computer Algebra Methods for Searching the Stationary Motions of the Connected Bodies System Moving in Gravitational Field," Mathematics in Computer Science, 2022. DOI: 10.1007/s11786-022-00535-6

[57] Zhengyu Li, Curtis Bright, and Vijay Ganesh, "A SAT Solver and Computer Algebra Attack on the Minimum Kochen-Specker Problem (Student Abstract)," in AAAI Conference on Artificial Intelligence, 2024. DOI: 10.1609/aaai.v38i21.30472

[58] F. Mogavero and J. Laskar, "The origin of chaos in the Solar System through computer algebra," Astronomy &amp; Astrophysics, 2022. DOI: 10.1051/0004-6361/202243327

[59] K. Zotos, "Computer Algebra Systems & Artificial Intelligence," BRAIN. Broad Research in Artificial Intelligence and Neuroscience, 2024. DOI: 10.18662/brain/15.2/584

[60] Y. Blinkov and A. Rebrina, "Investigation of Difference Schemes for Two-Dimensional Navier–Stokes Equations by Using Computer Algebra Algorithms," Programming and Computer Software, 2023. DOI: 10.1134/S0361768823010024