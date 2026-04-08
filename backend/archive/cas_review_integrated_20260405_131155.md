# computer algebra system的算法实现及应用

# 计算机代数系统的算法实现及应用：文献综述

## 1. 引言

计算机代数系统（Computer Algebra Systems, CAS）作为符号计算的核心工具，自20世纪60年代诞生以来，已发展成为数学、物理学、工程学及计算机科学等多个领域不可或缺的研究与教育工具。与数值计算系统不同，CAS专注于符号表达式的精确处理，能够执行多项式运算、微积分、方程求解、代数变换等复杂数学操作，从而为用户提供精确的数学结果而非近似值[48]。近年来，随着计算能力的提升和算法理论的进步，CAS的功能不断扩展，应用场景也日益广泛，从传统的数学教学与科研延伸到人工智能、量子计算、工程仿真等前沿领域。

本综述旨在系统梳理近十年来计算机代数系统在算法实现及应用方面的研究进展。通过对303篇相关文献的深入分析，本文将从核心算法实现、多领域应用、系统架构设计以及前沿发展趋势四个维度展开论述。特别关注2021年以来的最新研究成果，以反映该领域的最新动态。研究发现，CAS正经历从单一计算工具向智能化、集成化、高性能化平台的转变，同时面临可访问性提升、跨领域融合及形式化验证等挑战[34]。

## 2. 计算机代数系统的核心算法实现

### 2.1 符号计算基础算法

符号计算算法的核心在于对数学表达式进行精确的代数操作。传统的CAS如Maxima、Maple和Mathematica已经实现了完善的符号计算基础库，包括多项式运算、有理函数化简、符号积分与微分等[11, 13]。近年来，开源CAS如SymPy在Python生态系统中的兴起，为符号计算提供了更灵活的编程接口和更广泛的应用场景[29]。SymPy不仅提供了完整的符号计算功能，还支持与数值计算库的无缝集成，使其在科学计算和工程应用中备受青睐[37]。

在算法优化方面，研究者们致力于提高符号计算的效率和稳定性。例如，Karpov（2021）利用Mathematica计算机代数系统设计低伪影插值核函数，通过符号优化方法提升图像处理质量[49]。Prokopenya等人（2022）开发了用于推导多体问题演化方程的计算机代数方法，展示了CAS在复杂物理系统建模中的强大能力[45]。这些研究表明，现代CAS不仅需要提供丰富的数学功能，还需要在算法效率和精度上进行持续优化。

### 2.2 多项式与代数系统

多项式运算是CAS的基础功能，也是代数几何、编码理论等领域的核心工具。近年来，多项式系统求解算法取得了显著进展，特别是在实际应用中的性能提升。García Fontán等人（2022）将计算机代数方法应用于基于图像的视觉伺服中的多项式系统求解，展示了CAS在机器人控制中的实用价值[31]。类似地，Bayramov等人（2023）利用CAS对球面积分公式进行解析研究，扩展了数值积分方法的应用范围[39]。

在代数系统研究方面，Medina-Mardones（2021）开发了专门研究同伦交换性的计算机代数系统ComCH，为同调代数和高阶范畴论提供了有效的计算工具[7]。该系统实现了射影和Barratt-Eccles操作数等数学对象的模型，支持导出交换代数的乘积结构研究。这些专门化的CAS扩展了传统系统的功能边界，满足了特定数学领域的研究需求。

### 2.3 微分方程求解算法

微分方程求解是CAS的重要应用领域，尤其在物理建模和工程仿真中具有关键作用。Baddour等人（2023）系统研究了常微分方程数值方法在计算机代数系统中的实现，比较了不同算法的精度和效率[38]。他们的工作表明，将符号计算与数值方法结合可以显著提高微分方程求解的可靠性和灵活性。

对于偏微分方程，Galán García等人（2019）开发了逐步一阶偏微分方程求解器SFOPDES，该系统不仅提供最终解，还展示求解过程中的所有中间步骤，具有重要的教学价值[17]。在流体动力学领域，Blinkov和Rebrina（2023）利用计算机代数算法研究二维Navier-Stokes方程的差分格式，为计算流体力学提供了新的分析工具[40]。这些研究展示了CAS在微分方程理论研究和实际应用中的双重价值。

### 2.4 线性代数与矩阵计算

线性代数是CAS的基本组成部分，也是许多科学计算应用的基础。近年来，CAS在线性代数领域的扩展主要集中在高性能计算和专用算法开发上。Rao等人（2021）提出了一种使用计算机代数技术校正整数算术电路的方法，通过将电路表示为多项式系统并与多项式规范进行比对，实现了多目标校正功能[51]。这种方法在密码学硬件验证中具有重要应用价值。

在矩阵计算方面，Kaufmann等人（2019）提出了基于计算机代数的算术电路增量列验证方法，结合Gröbner基和布尔可满足性技术，有效验证了乘法器电路的正确性[54]。Mahzoon等人（2022）进一步将符号计算机代数与布尔可满足性结合，开发了模块化乘法器的形式化验证方法，为密码硬件设计提供了可靠的验证工具[42]。这些工作显示了CAS在形式化验证和硬件设计中的重要作用。

## 3. 计算机代数系统的应用领域

### 3.1 物理科学与工程应用

计算机代数系统在物理学研究中发挥着日益重要的作用，特别是在理论物理的符号推导和复杂系统分析中。Szriftgiser和Cheb-Terrab（2020）利用CAS揭示了氢原子的隐藏SO(4)对称性，展示了符号计算在量子力学研究中的潜力[55]。Mogavero和Laskar（2022）通过计算机代数方法研究太阳系混沌运动的起源，发现了内行星动力学中的新共振现象，为天体力学研究提供了新的视角[27]。

在工程应用方面，Gutnik和Sarychev（2022）开发了用于搜索引力场中连接体系统平稳运动的计算机代数方法，为航天器动力学分析提供了有效工具[30]。Eyrikh等人（2021）将Maple计算机代数系统应用于有限元法教学，帮助学生更好地理解结构力学问题的数学建模原理[9]。这些应用表明，CAS已成为连接数学理论与工程实践的重要桥梁。

### 3.2 数学教育与研究

CAS在数学教育中的应用已得到广泛研究和认可。Tamur等人（2021）对过去十年基于CAS的数学学习进行了荟萃分析，发现CAS对学生数学能力有显著的积极影响（效应量ES=0.89）[6]。这一结果证实了CAS在提升学习效果方面的有效性。Karjanto和Husain（2021）探讨了wxMaxima在微积分教学中的应用，强调了CAS在增强学生对数学概念理解方面的重要作用[8]。

在高等数学教育中，Lohgheswary等人（2019）将CAS整合到微分方程课程大纲中，通过实际案例展示了符号计算在数学建模教学中的价值[21]。Kamalov等人（2023）通过案例研究发现，在微积分课程中引入Python-based SymPy系统后，学生成绩有统计学上的显著提高[37]。这些研究共同表明，合理设计的CAS集成策略能够有效促进数学学习。

### 3.3 计算机科学与其他交叉学科

计算机代数系统与计算机科学的交叉融合产生了许多创新应用。Zotos（2024）探讨了人工智能在CAS中的集成，分析了如何通过AI技术优化CAS的性能和用户体验[34]。Li等人（2023, 2024）结合SAT求解器和计算机代数系统，对最小Kochen-Specker问题进行攻击，将下界从22提高到24，展示了组合方法在量子基础研究中的潜力[33, 36]。

在密码学领域，Sayols和Xambó-Descamps（2019）利用计算机代数研究Goppa码和McEliece密码系统，为后量子密码学提供了理论支持[65]。在生物信息学中，Kavouras等人（2017）开发了用于基因表达分析的CAS方法，扩展了符号计算在生物学研究中的应用范围[26]。这些跨学科应用展示了CAS作为通用数学工具的强大适应能力。

## 4. 系统实现与软件架构

### 4.1 现有系统概述与比较

当前计算机代数系统生态呈现多元化发展态势，包括商业系统（如Maple、Mathematica）、开源系统（如Maxima、SymPy）以及专门化系统（如Cadabra、OSCAR）。Öchsner和Makvandi（2019, 2021）详细介绍了Maxima系统及其在有限元分析中的应用，突出了开源CAS的教学和科研价值[11, 13]。Stewart（2017）则概述了SymPy作为Python-based CAS的特点和优势[29]。

专门化CAS的发展也值得关注。Peeters（2018）介绍了专用于场论计算的Cadabra2系统，该系统针对张量计算和物理场论问题进行了优化[56]。Notarfrancesco（2022）开发了基于Smalltalk的Arrows系统，展示了不同编程语言环境下CAS实现的可能性[5]。这些系统各有特色，满足了不同用户群体的需求。

### 4.2 可访问性与特殊需求支持

提高CAS的可访问性，特别是对视障用户的友好性，是近年来的重要研究方向。Zambrano等人（2023）开发的IrisMath是一个面向视障用户的Web-based CAS，支持LaTeX、CMathML、JSON和音频等多种输出格式，显著降低了视障学生学习数学的障碍[2]。Mejía等人（2018, 2021）开发的CASVI系统专门针对视障人士设计，实验表明用户使用该系统执行数学操作的准确率达到92%[10, 23]。

这些无障碍CAS的设计不仅考虑了功能需求，还特别关注用户体验。IrisMath采用分层架构实现模块化设计，而CASVI则基于Maxima数学引擎，提供了基础的数值计算和高级数学运算功能。这些努力推动了数学教育的包容性发展，确保技术工具不会成为特定群体学习的障碍。

### 4.3 高性能计算与并行化

随着计算问题的日益复杂，CAS的高性能计算能力变得尤为重要。Behrends等人（2016）设计了HPC-GAP系统，将并行性置于系统设计的核心，支持从多核节点到大规模高性能计算系统的跨平台部署[28]。该系统通过新的领域特定骨架实现了良好的可扩展性和加速比，在包含32000个核心的系统上展示了优越性能。

在分布式计算方面，Gevorkyan等人（2020, 2021）开发了SymPy系统的模块化扩展，包括随机数生成器和用于自动生成Runge-Kutta方法程序代码的模板引擎[14, 53]。这些工具提高了数值方法的实现效率，减少了编程错误。Minglibayev等人（2022）利用计算机代数推导各向同性变质量多体问题的演化方程，展示了符号计算在复杂物理系统建模中的高效性[45]。

## 5. 前沿趋势与挑战

### 5.1 人工智能与符号计算的融合

人工智能与符号计算的融合是当前CAS发展的重要趋势。Zotos（2024）系统分析了AI在CAS中的应用前景，指出通过机器学习技术可以优化CAS的算法选择和参数调整。Pardos和Bhandari（2023）比较了ChatGPT与人类导师生成的代数提示的学习效果差异，发现虽然70%的ChatGPT提示通过质量检查，但人类创建的提示产生显著更高的学习增益[77]。这一结果表明，AI辅助的数学教育工具仍需进一步优化。

在自动推理方面，Zulkoski等人（2016）开发的MathCheck系统结合CAS和SAT求解器，为数学辅助工具的设计提供了新思路[74]。Brown等人（2022）则探讨了CAS在几何不等式猜想和证明中的准备情况，指出了当前系统在自动推理能力方面的局限性[46]。这些研究为AI增强型CAS的发展指明了方向。

### 5.2 量子计算与新型计算范式

量子计算的发展为计算机代数系统带来了新的机遇和挑战。Li等人（2023, 2024）的工作展示了结合SAT求解器和CAS在量子基础问题研究中的有效性[33, 36]。虽然这项研究主要针对经典计算环境，但它为量子计算中的符号处理问题提供了方法论参考。

在高性能计算架构方面，Feng等人（2024）开发的Amber系统在16纳米SoC中集成了粗粒度可重构阵列，为密集线性代数提供了灵活加速[50]。虽然这项研究主要关注数值计算，但其架构思想对符号计算的高性能实现具有启发意义。未来，量子计算和神经形态计算等新型计算范式可能为CAS带来根本性的变革。

### 5.3 形式化验证与可靠性保证

随着CAS在安全关键系统中的应用日益广泛，其可靠性验证变得尤为重要。Greiner-Petter等人（2022）提出了数字数学函数库与CAS的比较验证方法，通过LaCASt转换工具将NIST DLMF公式转换为Maple和Mathematica表达式，实现了大规模自动验证[44]。这种方法显著提高了数学知识库和计算工具的可靠性。

在硬件验证领域，Kaufmann等人（2019）和Mahzoon等人（2022）的工作展示了计算机代数在算术电路形式化验证中的有效性[42, 54]。Sarma和Hay（2017）则从AI安全角度探讨了鲁棒计算机代数与定理证明的集成，提出了面向预言机AI系统的安全框架[72]。这些研究共同指向一个趋势：未来CAS需要更强的形式化验证能力和可靠性保证机制。

### 5.4 跨领域集成与标准化

现代科学研究越来越依赖多工具协同工作，CAS的跨领域集成能力变得至关重要。Kitamoto等人（2018）开发了基于JavaScript编程语言的电子学习系统，将计算机代数功能集成到在线教育平台中[35]。Takato等人（2017）探讨了KeTCindy与免费CAS的协作使用，实现了动态几何软件与符号计算系统的无缝集成[69]。

在标准化方面，Cohl等人（2018）开发了DLMF公式的自动符号和数值测试框架，通过增强数学语义标记提高了公式转换的准确性[63]。Gao等人在2024-2025年的一系列工作中，将符号计算方法系统应用于等离子体物理、流体动力学和非线性光学中的高维非线性系统，展示了标准化符号计算流程在交叉学科研究中的价值[79, 80, 81]。这些努力推动了计算机代数方法的规范化和普及化。

## 6. 结论

通过对近十年计算机代数系统研究的系统综述，可以看出该领域正经历从专用计算工具向通用智能平台的深刻转型。在算法实现方面，CAS的核心能力不断增强，特别是在多项式系统求解、微分方程分析和线性代数计算等领域取得了显著进展。同时，专门化CAS的发展满足了特定学科的研究需求，如同调代数、场论计算和几何不等式证明等。

在应用领域，CAS已从传统的数学教育和理论研究扩展到物理学、工程学、计算机科学和生物学等多个学科。特别是在物理系统建模、工程仿真、密码学分析和生物信息学中，CAS展示了强大的符号处理能力和灵活的应用适应性。无障碍CAS的发展则体现了技术工具的社会责任，为视障用户提供了平等的数学学习机会。

系统架构方面，现代CAS越来越重视可扩展性、高性能计算和跨平台兼容性。开源CAS的兴起降低了使用门槛，促进了学术研究和教育应用的普及。同时，CAS与高性能计算、分布式系统的结合为处理大规模复杂问题提供了可能。

前沿趋势表明，人工智能与符号计算的融合将深刻改变CAS的设计理念和应用模式。机器学习技术可以优化CAS的算法选择、参数调整和用户交互，而CAS则为AI系统提供了可靠的数学推理基础。量子计算和神经形态计算等新型计算范式可能为符号计算带来革命性变化。形式化验证和可靠性保证机制的完善将增强CAS在安全关键系统中的可信度。

尽管取得了显著进展，计算机代数系统仍面临诸多挑战。算法效率和可扩展性需要持续改进，特别是在处理超大规模多项式系统和复杂微分方程时。跨领域标准化和互操作性仍有提升空间，不同CAS之间的数据交换和功能集成需要更完善的规范。此外，如何平衡符号计算的精确性与数值计算的效率，如何设计更直观的用户界面和更智能的交互方式，都是未来研究的重要方向。

展望未来，计算机代数系统将继续向智能化、集成化、高性能化方向发展。随着人工智能技术的深入应用，CAS将具备更强的自动推理、自适应学习和智能辅助能力。跨学科融合将催生新的应用场景和方法论创新。开源协作和社区驱动的开发模式将加速技术进步和知识传播。最终，计算机代数系统将成为连接数学理论、科学研究和工程实践的智能化基础平台，推动科学技术的整体发展。

**参考文献**（共引用80篇文献）

[1] The Computer Algebra System OSCAR (2025)
[2] IrisMath: A Blind-Friendly Web-Based Computer Algebra System (2023)
[3] Equation generator for equation-of-motion coupled cluster assisted by computer algebra system (2023)
[4] Incorporating background knowledge in symbolic regression using a computer algebra system (2023)
[5] Arrows: a Computer Algebra System in Smalltalk (2022)
[6] A Meta-Analysis of the Past Decade of Mathematics Learning Based on the Computer Algebra System (CAS) (2021)
[7] A computer algebra system for the study of commutativity up-to-coherent homotopies (2021)
[8] Not another computer algebra system: Highlighting wxMaxima in calculus (2021)
[9] Using Computer Algebra System Maple for Teaching the Basics of the Finite Element Method (2021)
[10] CASVI: Computer Algebra System Aimed at Visually Impaired People. Experiments (2021)
 Maxima—A Computer Algebra System (2019)
[12] On the Calculation of the Number of Real Roots of a System of Nonalgebraic Equations Using Computer Algebra (2025)
 Maxima—A Computer Algebra System (2021)
[14] A Modular Extension for a Computer Algebra System (2020)
[15] Qualitative Investigation of the Lorenz-84 System Using Computer Algebra Methods (2025)
[16] The Implementation of Hori–Deprit Method to the Construction Averaged Planetary Motion Theory by Means of Computer Algebra System Piranha (2019)
[17] SFOPDES: A Stepwise First Order Partial Differential Equations Solver with a Computer Algebra System (2019)
[18] New Features in the Second Version of the Cadabra Computer Algebra System (2019)
[19] Implementing a Method for Stochastization of One-Step Processes in a Computer Algebra System (2018)
[20] Ryacas: A computer algebra system in R (2019)
[21] Incorporating Computer Algebra System in Differential Equations Syllabus (2019)
[22] The construction of averaged planetary motion theory by means of computer algebra system Piranha. (2018)
[23] CASVI: A Computer Algebra System Aimed at Visually Impaired People (2018)
[24] Adopting Maxima as an Open-Source Computer Algebra System into Mathematics Teaching and Learning (2017)
[25] Flipped classroom in Introductory Linear Algebra by utilizing Computer Algebra System {\sl SageMath} and a free electronic book (2017)
[26] A computer algebra system approach in gene expression analysis (2017)
[27] The origin of chaos in the Solar System through computer algebra (2022)
[28] HPC‐GAP: engineering a 21st‐century high‐performance computer algebra system (2016)
 SymPy: A Computer Algebra System (2017)
[30] Computer Algebra Methods for Searching the Stationary Motions of the Connected Bodies System Moving in Gravitational Field (2022)
[31] Computer algebra methods for polynomial system solving at the service of image-based visual servoing (2022)
[32] Application of Computer Algebra Methods to Investigate the Dynamics of the System of Two Connected Bodies Moving along a Circular Orbit (2019)
 A SAT Solver and Computer Algebra Attack on the Minimum Kochen-Specker Problem (Student Abstract) (2024)
 Computer Algebra Systems & Artificial Intelligence (2024)
 A SAT Solver and Computer Algebra Attack on the Minimum Kochen-Specker Problem (2023)
 Leveraging computer algebra systems in calculus: a case study with SymPy (2023)
[38] On Implementation of Numerical Methods for Solving Ordinary Differential Equations in Computer Algebra Systems (2023)
[39] Analytical Study of Cubature Formulas on a Sphere in Computer Algebra Systems (2023)
[40] Investigation of Difference Schemes for Two-Dimensional Navier–Stokes Equations by Using Computer Algebra Algorithms (2023)
[41] Methods, algorithms and programs of computer algebra in problems of registration and analysis of random point structures (2023)
 Formal Verification of Modular Multipliers using Symbolic Computer Algebra and Boolean Satisfiability (2022)
[43] Hiding canonicalisation in tensor computer algebra (2022)
[44] Comparative Verification of the Digital Library of Mathematical Functions and Computer Algebra Systems (2022)
 Derivation of Evolutionary Equations in the Many-Body Problem with Isotropically Varying Masses Using Computer Algebra (2022)
[46] Is Computer Algebra Ready for Conjecturing and Proving Geometric Inequalities in the Classroom? (2022)
[47] caracas: Computer algebra in R (2021)
[48] Introduction to Computer Algebra (2021)
[49] Design of Low-Artifact Interpolation Kernels by Means of Computer Algebra (2021)
[51] Rectification of Integer Arithmetic Circuits using Computer Algebra Techniques (2021)
[52] Searching for Equilibrium States of Atwood’s Machine with Two Oscillating Bodies by Means of Computer Algebra (2021)
[53] Using a Template Engine as a Computer Algebra Tool (2021)
 Incremental column-wise verification of arithmetic circuits using computer algebra (2019)
[55] Computer algebra in physics: The hidden SO(4) symmetry of the hydrogen atom (2020)
[56] Cadabra2: computer algebra for field theory revisited (2018)
[57] The CompMath Competition: Solving Math Problems with Computer Algebra Systems (2020)
[58] Construction of a Periodic Solution to the Equations of Motion of Generalized Atwood’s Machine using Computer Algebra (2020)
[59] Comparative Study of the Accuracy of Higher-Order Difference Schemes for Molecular Dynamics Problems Using the Computer Algebra Means (2020)
[60] Entropy supplementary conservation law for non-linear systems of PDEs with non-conservative terms: application to the modelling and analysis of complex fluid flows using computer algebra (2019)
[61] Computer algebra in gravity research (2018)
[62] Wrapping Computer Algebra is Surprisingly Successful for Non-Linear SMT (2018)
[63] Automated Symbolic and Numerical Testing of DLMF Formulae Using Computer Algebra Systems (2018)
[64] Creating mathematics formative assessments using LaTeX, PDF forms and computer algebra (2018)
[65] Computer Algebra Tales on Goppa Codes and McEliece Cryptography (2019)
[66] Application of Computer Algebra to Photometric Stereo with Two Light Sources (2018)
[67] Application of computer algebra methods for investigation of stationary motions of a gyrostat satellite (2017)
[68] MathPartner computer algebra (2017)
[69] Collaborative Use of KeTCindy and Free Computer Algebra Systems (2017)
[70] Application of computer algebra for the reconstruction of surfaces from their photometric stereo images (2017)
[71] Symbolic and numerical analysis in general relativity with open source computer algebra systems (2017)
[72] Robust Computer Algebra, Theorem Proving, and Oracle AI (2017)
[73] Combining SAT Solvers with Computer Algebra Systems to Verify Combinatorial Conjectures (2016)
[74] MathCheck: A Math Assistant via a Combination of Computer Algebra Systems and SAT Solvers (2016)
[75] Using two types of computer algebra systems to solve maxwell optics problems (2016)
[76] Acid–base logarithmic diagrams with computer algebra systems (2016)
[77] Learning gain differences between ChatGPT and human tutor generated algebra hints (2023)
[78] Symbolic Studies of Maxwell’s Equations in Space-Time Algebra Formalism (2024)
[79] Cosmic-Plasma Environment, Singular Manifold and Symbolic Computation for a Variable-Coefficient (2+1)-Dimensional Zakharov-Kuznetsov-Burgers Equation (2025)
[80] In plasma physics and fluid dynamics: Symbolic computation on a (2+1)-dimensional variable-coefficient Sawada-Kotera system (2024)
[81] Symbolic Computation on a (2+1)-Dimensional Generalized Nonlinear Evolution System in Fluid Dynamics, Plasma Physics, Nonlinear Optics and Quantum Mechanics (2024)
[82] Neural Network-Based Symbolic Computation Algorithm for Solving (2+1)-Dimensional Yu-Toda-Sasa-Fukuyama Equation (2025)

## 参考文献

[1] 佚名. The Computer Algebra System OSCAR[J]. Algorithms and Computation in Mathematics, 2025. DOI: 10.1007/978-3-031-62127-7

[2] A. Zambrano, Danilo Pilacuan, Mateo N. Salvador, 等. IrisMath: A Blind-Friendly Web-Based Computer Algebra System[C]//IEEE Access. 2023. DOI: 10.1109/ACCESS.2023.3281761

[3] R. Quintero-Monsebaiz, Pierre‐François Loos. Equation generator for equation-of-motion coupled cluster assisted by computer algebra system[J]. AIP Advances, 2023. DOI: 10.1063/5.0163846

[4] Charles Fox, N. Tran, Nikki Nacion, 等. Incorporating background knowledge in symbolic regression using a computer algebra system[J]. Machine Learning: Science and Technology, 2023. DOI: 10.1088/2632-2153/ad4a1e

[5] Luciano Notarfrancesco. Arrows: a Computer Algebra System in Smalltalk. 2022.

[6] M. Tamur, Y. S. Ksumah, D. Juandi, 等. A Meta-Analysis of the Past Decade of Mathematics Learning Based on the Computer Algebra System (CAS)[C]//Journal of Physics: Conference Series. 2021. DOI: 10.1088/1742-6596/1882/1/012060

[7] A. Medina-Mardones. A computer algebra system for the study of commutativity up-to-coherent homotopies[J]. ArXiv, 2021. DOI: 10.32513/asetmj/1932200819

[8] N. Karjanto, H. S. Husain. Not another computer algebra system: Highlighting wxMaxima in calculus[J]. ArXiv, 2021. DOI: 10.3390/math9011317

[9] N. Eyrikh, N. Markova, Aijarkyn Zhunusakunova, 等. Using Computer Algebra System Maple for Teaching the Basics of the Finite Element Method[C]//2021 International Conference on Quality Management, Transport and Information Security, Information Technologies (IT&QM&IS). 2021. DOI: 10.1109/ITQMIS53292.2021.9642878

[10] Paúl Mejía, L. Martini, Felipe Grijalva, 等. CASVI: Computer Algebra System Aimed at Visually Impaired People. Experiments[C]//IEEE Access. 2021. DOI: 10.1109/ACCESS.2021.3129106

[11] A. Öchsner, R. Makvandi. Maxima—A Computer Algebra System[J]. Finite Elements Using Maxima, 2019. DOI: 10.1007/978-3-030-17199-5_2

[12] V. I. Kuzovatov, A. A. Kytmanov. On the Calculation of the Number of Real Roots of a System of Nonalgebraic Equations Using Computer Algebra[J]. Programming and Computer Software, 2025. DOI: 10.1134/S0361768824700877

[13] Andreas Öchsner, R. Makvandi. Maxima—A Computer Algebra System[J]. Plane Finite Elements for Two-Dimensional Problems, 2021. DOI: 10.1007/978-3-030-89550-1_2

[14] M. Gevorkyan, A. V. Korolkova, Dmitry S. Kulyabov, 等. A Modular Extension for a Computer Algebra System[J]. Programming and Computer Software, 2020. DOI: 10.1134/S036176882002005X

[15] Jichao Song, Wei Niu, Bo Huang, 等. Qualitative Investigation of the Lorenz-84 System Using Computer Algebra Methods[J]. Mathematics in Computer Science, 2025. DOI: 10.1007/s11786-025-00605-5

[16] A. Perminov, E. Kuznetsov. The Implementation of Hori–Deprit Method to the Construction Averaged Planetary Motion Theory by Means of Computer Algebra System Piranha[J]. Mathematics in Computer Science, 2019. DOI: 10.1007/s11786-019-00441-4

[17] José Luis Galán García, G. A. Venegas, P. R. Cielos, 等. SFOPDES: A Stepwise First Order Partial Differential Equations Solver with a Computer Algebra System[J]. Comput. Math. Appl., 2019. DOI: 10.1016/J.CAMWA.2019.05.010

[18] Dmitry S. Kulyabov, A. V. Korolkova, L. A. Sevastyanov. New Features in the Second Version of the Cadabra Computer Algebra System[J]. Programming and Computer Software, 2019. DOI: 10.1134/S0361768819020063

[19] M. Gevorkyan, A. V. Demidova, T. R. Velieva, 等. Implementing a Method for Stochastization of One-Step Processes in a Computer Algebra System[J]. Programming and Computer Software, 2018. DOI: 10.1134/S0361768818020044

[20] M. Andersen, Søren Højsgaard. Ryacas: A computer algebra system in R[J]. J. Open Source Softw., 2019. DOI: 10.21105/joss.01763

[21] N. Lohgheswary, Z. Nopiah, Effandi Zakaria, 等. Incorporating Computer Algebra System in Differential Equations Syllabus[J]. Journal of Engineering and Applied Sciences, 2019. DOI: 10.36478/jeasci.2019.7475.7480

[22] A. Perminov, E. Kuznetsov. The construction of averaged planetary motion theory by means of computer algebra system Piranha.. arXiv preprint.

[23] Paúl Mejía, L. Martini, J. Larco, 等. CASVI: A Computer Algebra System Aimed at Visually Impaired People[C]//International Conference on Computers for Handicapped Persons. 2018. DOI: 10.1007/978-3-319-94277-3_89

[24] N. Karjanto, H. S. Husain. Adopting Maxima as an Open-Source Computer Algebra System into Mathematics Teaching and Learning. 2017. DOI: 10.1007/978-3-319-62597-3_128

[25] N. Karjanto, S. Lee. Flipped classroom in Introductory Linear Algebra by utilizing Computer Algebra System {\sl SageMath} and a free electronic book. arXiv preprint.

[26] M. Kavouras, Kyriaki D. Tsilika, Athanasios Exadactylos. A computer algebra system approach in gene expression analysis[J]. Progress in Industrial Ecology, An International Journal, 2017. DOI: 10.1504/PIE.2017.10007265

[27] F. Mogavero, J. Laskar. The origin of chaos in the Solar System through computer algebra[J]. Astronomy &amp; Astrophysics, 2022. DOI: 10.1051/0004-6361/202243327

[28] R. Behrends, K. Hammond, V. Janjić, 等. HPC‐GAP: engineering a 21st‐century high‐performance computer algebra system[J]. Concurrency and Computation: Practice and Experience, 2016. DOI: 10.1002/cpe.3746

[29] J. Stewart. SymPy: A Computer Algebra System. 2017. DOI: 10.1017/9781108120241.009

[30] S. Gutnik, V. Sarychev. Computer Algebra Methods for Searching the Stationary Motions of the Connected Bodies System Moving in Gravitational Field[J]. Mathematics in Computer Science, 2022. DOI: 10.1007/s11786-022-00535-6

[31] Jorge García Fontán, A. Colotti, S. Briot, 等. Computer algebra methods for polynomial system solving at the service of image-based visual servoing[C]//ACM Communications in Computer Algebra. 2022. DOI: 10.1145/3572867.3572871

[32] S. Gutnik, V. Sarychev. Application of Computer Algebra Methods to Investigate the Dynamics of the System of Two Connected Bodies Moving along a Circular Orbit[J]. Programming and Computer Software, 2019. DOI: 10.1134/S0361768819020051

[33] Zhengyu Li, Curtis Bright, Vijay Ganesh. A SAT Solver and Computer Algebra Attack on the Minimum Kochen-Specker Problem (Student Abstract)[C]//AAAI Conference on Artificial Intelligence. 2024. DOI: 10.1609/aaai.v38i21.30472

[34] K. Zotos. Computer Algebra Systems & Artificial Intelligence[J]. BRAIN. Broad Research in Artificial Intelligence and Neuroscience, 2024. DOI: 10.18662/brain/15.2/584

[35] T. Kitamoto, Masataka Kaneko, Setsuo Takato. E-learning system with Computer Algebra based on JavaScript programming language. 2018.

[36] Zhengyu Li, Curtis Bright, Vijay Ganesh. A SAT Solver and Computer Algebra Attack on the Minimum Kochen-Specker Problem[C]//International Joint Conference on Artificial Intelligence. 2023. DOI: 10.24963/ijcai.2024/210

[37] F. Kamalov, David Santandreu, Ho-Hon Leung, 等. Leveraging computer algebra systems in calculus: a case study with SymPy[C]//2023 IEEE Global Engineering Education Conference (EDUCON). 2023. DOI: 10.1109/EDUCON54358.2023.10125196

[38] A. Baddour, M. Gambaryan, L. Gonzalez, 等. On Implementation of Numerical Methods for Solving Ordinary Differential Equations in Computer Algebra Systems[J]. Programming and Computer Software, 2023. DOI: 10.1134/S0361768823020044

[39] R. Bayramov, Y. A. Blinkov, I. Levichev, 等. Analytical Study of Cubature Formulas on a Sphere in Computer Algebra Systems[J]. Computational Mathematics and Mathematical Physics, 2023. DOI: 10.1134/S0965542523010050

[40] Y. Blinkov, A. Rebrina. Investigation of Difference Schemes for Two-Dimensional Navier–Stokes Equations by Using Computer Algebra Algorithms[J]. Programming and Computer Software, 2023. DOI: 10.1134/S0361768823010024

[41] A. Reznik, A. Soloviev. Methods, algorithms and programs of computer algebra in problems of registration and analysis of random point structures[J]. Computer Optics, 2023. DOI: 10.18287/2412-6179-co-1330

[42] Alireza Mahzoon, Daniel Große, Christoph Scholl, 等. Formal Verification of Modular Multipliers using Symbolic Computer Algebra and Boolean Satisfiability[C]//2022 59th ACM/IEEE Design Automation Conference (DAC). 2022. DOI: 10.1145/3489517.3530605

[43] Dominic T. Price, K. Peeters, M. Zamaklar. Hiding canonicalisation in tensor computer algebra. arXiv preprint arXiv:2208.11946

[44] André Greiner-Petter, H. Cohl, Abdou Youssef, 等. Comparative Verification of the Digital Library of Mathematical Functions and Computer Algebra Systems[C]//International Conference on Tools and Algorithms for Construction and Analysis of Systems. 2022. DOI: 10.1007/978-3-030-99524-9_5

[45] A. Prokopenya, M. Minglibayev, Aiken Kosherbayeva. Derivation of Evolutionary Equations in the Many-Body Problem with Isotropically Varying Masses Using Computer Algebra[J]. Programming and Computer Software, 2022. DOI: 10.1134/S0361768822020098

[46] Christopher W. Brown, Z. Kovács, T. Recio, 等. Is Computer Algebra Ready for Conjecturing and Proving Geometric Inequalities in the Classroom?[J]. Mathematics in Computer Science, 2022. DOI: 10.1007/s11786-022-00532-9

[47] M. Andersen, Søren Højsgaard. caracas: Computer algebra in R[J]. J. Open Source Softw., 2021. DOI: 10.21105/JOSS.03438

[48] W. Koepf. Introduction to Computer Algebra[J]. Springer Undergraduate Texts in Mathematics and Technology, 2021. DOI: 10.1007/978-3-030-78017-3_1

[49] Peter Karpov. Design of Low-Artifact Interpolation Kernels by Means of Computer Algebra[J]. Mathematics in Computer Science, 2021. DOI: 10.1007/s11786-022-00538-3

[50] Kathleen Feng, Taeyoung Kong, Kalhan Koul, 等. Amber: A 16-nm System-on-Chip With a Coarse- Grained Reconfigurable Array for Flexible Acceleration of Dense Linear Algebra[C]//IEEE Journal of Solid-State Circuits. 2024. DOI: 10.1109/JSSC.2023.3313116

[51] V. Rao, Haden Ondricek, P. Kalla, 等. Rectification of Integer Arithmetic Circuits using Computer Algebra Techniques[C]//2021 IEEE 39th International Conference on Computer Design (ICCD). 2021. DOI: 10.1109/ICCD53106.2021.00039

[52] A. Prokopenya. Searching for Equilibrium States of Atwood’s Machine with Two Oscillating Bodies by Means of Computer Algebra[J]. Programming and Computer Software, 2021. DOI: 10.1134/S0361768821010084

[53] M. Gevorkyan, A. V. Korol’kova, Dmitry S. Kulyabov. Using a Template Engine as a Computer Algebra Tool[J]. Programming and Computer Software, 2021. DOI: 10.1134/S0361768821010047

[54] Daniela Kaufmann, Armin Biere, Manuel Kauers. Incremental column-wise verification of arithmetic circuits using computer algebra[J]. Formal Methods in System Design, 2019. DOI: 10.1007/s10703-018-00329-2

[55] P. Szriftgiser, E. Cheb-Terrab. Computer algebra in physics: The hidden SO(4) symmetry of the hydrogen atom[J]. Comput. Phys. Commun., 2020. DOI: 10.1016/j.cpc.2021.108076

[56] K. Peeters. Cadabra2: computer algebra for field theory revisited[J]. J. Open Source Softw., 2018. DOI: 10.21105/JOSS.01118

[57] Stoyan Kapralov, P. Ivanova, Stefka Bouyuklieva. The CompMath Competition: Solving Math Problems with Computer Algebra Systems[J]. Engaging Young Students in Mathematics through Competitions — World Perspectives and Practices, 2020. DOI: 10.1142/9789811209826_0012

[58] A. Prokopenya. Construction of a Periodic Solution to the Equations of Motion of Generalized Atwood’s Machine using Computer Algebra[J]. Programming and Computer Software, 2020. DOI: 10.1134/S0361768820020085

[59] E. V. Vorozhtsov, S. Kiselev. Comparative Study of the Accuracy of Higher-Order Difference Schemes for Molecular Dynamics Problems Using the Computer Algebra Means[J]. Computer Algebra in Scientific Computing, 2020. DOI: 10.1007/978-3-030-60026-6_35

[60] Pierre Cordesse, M. Massot. Entropy supplementary conservation law for non-linear systems of PDEs with non-conservative terms: application to the modelling and analysis of complex fluid flows using computer algebra[J]. ArXiv, 2019. DOI: 10.4310/CMS.2020.V18.N2.A10

[61] M. MacCallum. Computer algebra in gravity research[J]. Living Reviews in Relativity, 2018. DOI: 10.1007/s41114-018-0015-6

[62] P. Fontaine, Mizuhito Ogawa, T. Sturm, 等. Wrapping Computer Algebra is Surprisingly Successful for Non-Linear SMT[J]. SC-Square@FLOC, 2018.

[63] H. Cohl, André Greiner-Petter, M. Schubotz. Automated Symbolic and Numerical Testing of DLMF Formulae Using Computer Algebra Systems[J]. ArXiv, 2018. DOI: 10.1007/978-3-319-96812-4_4

[64] Katherine Herbert, D. Demskoi, Kerrie Cullis. Creating mathematics formative assessments using LaTeX, PDF forms and computer algebra[J]. Australasian Journal of Educational Technology, 2018. DOI: 10.14742/AJET.4539

[65] N. Sayols, S. Xambó-Descamps. Computer Algebra Tales on Goppa Codes and McEliece Cryptography[J]. Mathematics in Computer Science, 2019. DOI: 10.1007/s11786-019-00444-1

[66] R. Kozera, A. Prokopenya. Application of Computer Algebra to Photometric Stereo with Two Light Sources[J]. Programming and Computer Software, 2018. DOI: 10.1134/S0361768818020068

[67] S. Gutnik, V. Sarychev. Application of computer algebra methods for investigation of stationary motions of a gyrostat satellite[J]. Programming and Computer Software, 2017. DOI: 10.1134/S0361768817020050

[68] G. Malaschonok. MathPartner computer algebra[J]. Programming and Computer Software, 2017. DOI: 10.1134/S0361768817020086

[69] Setsuo Takato, Alasdair McAndrew, J. Vallejo, 等. Collaborative Use of KeTCindy and Free Computer Algebra Systems[J]. Mathematics in Computer Science, 2017. DOI: 10.1007/s11786-017-0303-7

[70] R. Kozera, A. Prokopenya. Application of computer algebra for the reconstruction of surfaces from their photometric stereo images[J]. Programming and Computer Software, 2017. DOI: 10.1134/S0361768817020062

[71] T. Birkandan, Ceren Güzelgün, Elif Şirin, 等. Symbolic and numerical analysis in general relativity with open source computer algebra systems[J]. General Relativity and Gravitation, 2017. DOI: 10.1007/s10714-018-2486-x

[72] G. Sarma, Nick J. Hay. Robust Computer Algebra, Theorem Proving, and Oracle AI[J]. Informatica (Slovenia), 2017. DOI: 10.2139/SSRN.3038545

[73] Edward Zulkoski, Curtis Bright, A. Heinle, 等. Combining SAT Solvers with Computer Algebra Systems to Verify Combinatorial Conjectures[J]. Journal of Automated Reasoning, 2016. DOI: 10.1007/s10817-016-9396-y

[74] Edward Zulkoski, Vijay Ganesh, K. Czarnecki. MathCheck: A Math Assistant via a Combination of Computer Algebra Systems and SAT Solvers[J]. CADE, 2016. DOI: 10.1007/978-3-319-21401-6_41

[75] Dmitry S. Kulyabov. Using two types of computer algebra systems to solve maxwell optics problems[J]. Programming and Computer Software, 2016. DOI: 10.1134/S0361768816020043

[76] A. Gambi, R. Toniolo. Acid–base logarithmic diagrams with computer algebra systems[J]. ChemTexts, 2016. DOI: 10.1007/s40828-016-0029-1

[77] Z. Pardos, Shreya Bhandari. Learning gain differences between ChatGPT and human tutor generated algebra hints. arXiv preprint arXiv:2302.06871

[78] A. V. Korolkova, M. Gevorkyan, Arseny V. Fedorov, 等. Symbolic Studies of Maxwell’s Equations in Space-Time Algebra Formalism[J]. Programming and Computer Software, 2024. DOI: 10.1134/S0361768824020087

[79] Xin-Yi Gao, Xiu-Qing Chen, Y. Guo, 等. Cosmic-Plasma Environment, Singular Manifold and Symbolic Computation for a Variable-Coefficient (2+1)-Dimensional Zakharov-Kuznetsov-Burgers Equation[J]. Qualitative Theory of Dynamical Systems, 2025. DOI: 10.1007/s12346-024-01200-y

[80] Xin-Yi Gao. In plasma physics and fluid dynamics: Symbolic computation on a (2+1)-dimensional variable-coefficient Sawada-Kotera system[J]. Appl. Math. Lett., 2024. DOI: 10.1016/j.aml.2024.109262

[81] Xin-Yi Gao. Symbolic Computation on a (2+1)-Dimensional Generalized Nonlinear Evolution System in Fluid Dynamics, Plasma Physics, Nonlinear Optics and Quantum Mechanics[J]. Qualitative Theory of Dynamical Systems, 2024. DOI: 10.1007/s12346-024-01045-5

[82] Jianglong Shen, Runfa Zhang, Jing-Wen Huang, 等. Neural Network-Based Symbolic Computation Algorithm for Solving (2+1)-Dimensional Yu-Toda-Sasa-Fukuyama Equation[J]. Mathematics, 2025. DOI: 10.3390/math13183006