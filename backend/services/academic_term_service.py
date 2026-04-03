"""
学术术语服务
提供术语管理和查询功能
"""
from typing import List, Dict, Optional
from database import db


class AcademicTermService:
    """学术术语服务"""

    def __init__(self):
        self.db = db

    def get_session(self):
        """获取数据库会话"""
        return self.db.get_session()

    def search_keywords_from_topic(self, topic: str) -> List[str]:
        """
        从主题中提取关键词，使用术语库进行增强

        Args:
            topic: 论文主题

        Returns:
            关键词列表
        """
        import re

        keywords = []

        session_gen = self.get_session()
        session = next(session_gen)

        try:
            from services.academic_term_dao import AcademicTermDAO
            dao = AcademicTermDAO(session)

            # 1. 从术语库中搜索所有活跃术语
            all_terms = dao.search_terms(limit=1000)

            # 2. 构建搜索映射
            term_mapping = {}
            for term in all_terms:
                # 添加中文术语
                term_mapping[term.chinese_term.lower()] = term.english_terms
                # 添加英文术语
                for eng_term in term.english_terms:
                    term_mapping[eng_term.lower()] = term.english_terms
                # 添加别名
                if term.aliases:
                    for alias in term.aliases:
                        term_mapping[alias.lower()] = term.english_terms

            # 3. 在主题中查找匹配的术语
            topic_lower = topic.lower()

            # 查找中文术语
            for chinese, english_list in term_mapping.items():
                if chinese in topic_lower:
                    keywords.extend(english_list)
                    print(f"[术语库] 匹配到中文术语: {chinese} -> {english_list}")

            # 4. 查找特殊格式（如 6mA、DNA）
            special_patterns = [
                r'\d+[A-Z][a-z]',      # 如 6mA, 5mC
                r'[A-Z]{2,}(?![a-z])',  # 如 DNA, RNA
            ]
            for pattern in special_patterns:
                matches = re.findall(pattern, topic)
                for match in matches:
                    keywords.append(match.lower())

            # 5. 查找英文单词（通过术语库验证）
            english_words = re.findall(r'[a-zA-Z]{2,}', topic)
            for word in english_words:
                word_lower = word.lower()
                # 如果这个词在术语库的英文术语中，保留
                if word_lower in term_mapping:
                    keywords.extend(term_mapping[word_lower])

            # 6. 去重
            unique_keywords = list(set(keywords))

            print(f"[术语库] 从主题提取到 {len(unique_keywords)} 个关键词")

            return unique_keywords

        finally:
            try:
                next(session_gen)
            except StopIteration:
                pass

    def get_term_suggestions(self, partial: str, limit: int = 10) -> List[Dict]:
        """
        获取术语建议（用于自动补全）

        Args:
            partial: 部分输入
            limit: 返回数量限制

        Returns:
            建议列表
        """
        with self.get_session() as session:
            from services.academic_term_dao import AcademicTermDAO
            dao = AcademicTermDAO(session)

            terms = dao.search_terms(keyword=partial, limit=limit)

            suggestions = []
            for term in terms:
                suggestions.append({
                    "chinese": term.chinese_term,
                    "english": term.english_terms,
                    "category": term.category,
                    "description": term.description
                })

            return suggestions

    def initialize_default_terms(self) -> Dict:
        """
        初始化默认术语数据

        Returns:
            导入结果统计
        """
        default_terms = self._get_default_terms_data()

        session_gen = self.get_session()
        session = next(session_gen)

        try:
            from services.academic_term_dao import AcademicTermDAO
            dao = AcademicTermDAO(session)

            result = dao.batch_import_terms(default_terms)
            print(f"[术语库] 初始化完成: 成功 {result['success']}, 跳过 {result['skipped']}, 错误 {result['errors']}")
            return result
        finally:
            try:
                next(session_gen)
            except StopIteration:
                pass

    def _get_default_terms_data(self) -> List[Dict]:
        """获取默认术语数据"""
        return [
            # 深度学习
            {
                "chinese_term": "深度学习",
                "english_terms": ["deep learning", "dl"],
                "category": "dl",
                "subcategory": "general",
                "aliases": ["深层学习"],
                "description": "一种基于人工神经网络的机器学习方法",
                "priority": 100
            },
            {
                "chinese_term": "卷积神经网络",
                "english_terms": ["cnn", "convolutional neural network", "convnet"],
                "category": "dl",
                "subcategory": "architecture",
                "aliases": ["CNN"],
                "description": "一种专门处理网格结构数据（如图像）的神经网络",
                "priority": 100
            },
            {
                "chinese_term": "循环神经网络",
                "english_terms": ["rnn", "recurrent neural network"],
                "category": "dl",
                "subcategory": "architecture",
                "aliases": ["RNN"],
                "description": "一种用于处理序列数据的神经网络",
                "priority": 100
            },
            {
                "chinese_term": "长短期记忆网络",
                "english_terms": ["lstm", "long short-term memory"],
                "category": "dl",
                "subcategory": "architecture",
                "aliases": ["LSTM"],
                "description": "一种特殊的RNN，能够学习长期依赖关系",
                "priority": 100
            },
            {
                "chinese_term": "双向长短期记忆网络",
                "english_terms": ["bilstm", "bidirectional lstm", "bi-lstm"],
                "category": "dl",
                "subcategory": "architecture",
                "aliases": ["BiLSTM", "双向LSTM"],
                "description": "双向LSTM，由两个LSTM组成，分别从前向和后向处理序列",
                "priority": 100
            },
            {
                "chinese_term": "Transformer",
                "english_terms": ["transformer"],
                "category": "dl",
                "subcategory": "architecture",
                "aliases": ["transformer模型", "注意力机制"],
                "description": "基于自注意力机制的神经网络架构",
                "priority": 100
            },
            {
                "chinese_term": "注意力机制",
                "english_terms": ["attention", "attention mechanism"],
                "category": "dl",
                "subcategory": "mechanism",
                "aliases": [],
                "description": "一种让神经网络关注输入数据重要部分的机制",
                "priority": 90
            },
            {
                "chinese_term": "BERT",
                "english_terms": ["bert", "bidirectional encoder representations from transformers"],
                "category": "dl",
                "subcategory": "model",
                "aliases": ["BERT模型"],
                "description": "基于Transformer的预训练语言模型",
                "priority": 90
            },
            {
                "chinese_term": "GAN",
                "english_terms": ["gan", "generative adversarial network"],
                "category": "dl",
                "subcategory": "architecture",
                "aliases": ["生成对抗网络"],
                "description": "由生成器和判别器组成的神经网络架构",
                "priority": 90
            },

            # 生物信息学
            {
                "chinese_term": "表观遗传",
                "english_terms": ["epigenetic", "epigenetics"],
                "category": "bio",
                "subcategory": "general",
                "aliases": [],
                "description": "研究基因表达的遗传学分支",
                "priority": 100
            },
            {
                "chinese_term": "甲基化",
                "english_terms": ["methylation"],
                "category": "bio",
                "subcategory": "modification",
                "aliases": [],
                "description": "在DNA或RNA上添加甲基基团的化学修饰",
                "priority": 100
            },
            {
                "chinese_term": "DNA甲基化",
                "english_terms": ["dna methylation"],
                "category": "bio",
                "subcategory": "modification",
                "aliases": [],
                "description": "DNA分子上的甲基化修饰",
                "priority": 100
            },
            {
                "chinese_term": "6mA",
                "english_terms": ["6mA", "n6-methyladenine", "n6-methyladenine"],
                "category": "bio",
                "subcategory": "modification",
                "aliases": ["N6-甲基腺嘌呤"],
                "description": "DNA N6-甲基腺嘌呤，一种重要的表观遗传修饰",
                "priority": 100
            },
            {
                "chinese_term": "5mC",
                "english_terms": ["5mc", "5-methylcytosine", "5-methylcytosine"],
                "category": "bio",
                "subcategory": "modification",
                "aliases": ["5-甲基胞嘧啶"],
                "description": "DNA 5-甲基胞嘧啶",
                "priority": 100
            },
            {
                "chinese_term": "基因组",
                "english_terms": ["genome", "genomic"],
                "category": "bio",
                "subcategory": "general",
                "aliases": [],
                "description": "生物体的全部遗传物质",
                "priority": 90
            },
            {
                "chinese_term": "转录组",
                "english_terms": ["transcriptome", "transcriptomic"],
                "category": "bio",
                "subcategory": "omics",
                "aliases": [],
                "description": "细胞内所有RNA的集合",
                "priority": 90
            },
            {
                "chinese_term": "蛋白质组",
                "english_terms": ["proteome", "proteomic"],
                "category": "bio",
                "subcategory": "omics",
                "aliases": [],
                "description": "细胞内所有蛋白质的集合",
                "priority": 90
            },

            # 通用技术
            {
                "chinese_term": "机器学习",
                "english_terms": ["machine learning", "ml"],
                "category": "ml",
                "subcategory": "general",
                "aliases": ["ML"],
                "description": "让计算机自动学习和改进的算法",
                "priority": 100
            },
            {
                "chinese_term": "监督学习",
                "english_terms": ["supervised learning"],
                "category": "ml",
                "subcategory": "type",
                "aliases": [],
                "description": "使用标记数据训练的机器学习方法",
                "priority": 80
            },
            {
                "chinese_term": "无监督学习",
                "english_terms": ["unsupervised learning"],
                "category": "ml",
                "subcategory": "type",
                "aliases": [],
                "description": "使用未标记数据训练的机器学习方法",
                "priority": 80
            },
            {
                "chinese_term": "强化学习",
                "english_terms": ["reinforcement learning", "rl"],
                "category": "ml",
                "subcategory": "type",
                "aliases": ["RL"],
                "description": "通过奖励机制学习的机器学习方法",
                "priority": 80
            },
            {
                "chinese_term": "迁移学习",
                "english_terms": ["transfer learning"],
                "category": "ml",
                "subcategory": "technique",
                "aliases": [],
                "description": "将已训练模型的知识应用到新任务",
                "priority": 80
            },
            {
                "chinese_term": "特征工程",
                "english_terms": ["feature engineering"],
                "category": "ml",
                "subcategory": "technique",
                "aliases": [],
                "description": "从原始数据中提取特征的过程",
                "priority": 70
            },

            # 生物医学
            {
                "chinese_term": "癌症",
                "english_terms": ["cancer", "tumor", "carcinoma"],
                "category": "medical",
                "subcategory": "disease",
                "aliases": ["肿瘤", "恶性肿瘤"],
                "description": "恶性肿瘤",
                "priority": 90
            },
            {
                "chinese_term": "免疫",
                "english_terms": ["immune", "immunity", "immunology"],
                "category": "medical",
                "subcategory": "general",
                "aliases": ["免疫系统"],
                "description": "生物体的防御系统",
                "priority": 90
            },
            {
                "chinese_term": "炎症",
                "english_terms": ["inflammation", "inflammatory"],
                "category": "medical",
                "subcategory": "condition",
                "aliases": [],
                "description": "生物组织的免疫反应",
                "priority": 80
            },

            # 计算机科学通用
            {
                "chinese_term": "算法",
                "english_terms": ["algorithm"],
                "category": "cs",
                "subcategory": "general",
                "aliases": [],
                "description": "解决问题的步骤序列",
                "priority": 70
            },
            {
                "chinese_term": "数据结构",
                "english_terms": ["data structure"],
                "category": "cs",
                "subcategory": "general",
                "aliases": [],
                "description": "计算机存储和组织数据的方式",
                "priority": 70
            },
            {
                "chinese_term": "优化",
                "english_terms": ["optimization"],
                "category": "cs",
                "subcategory": "general",
                "aliases": [],
                "description": "寻找最优解的过程",
                "priority": 70
            },
        ]
