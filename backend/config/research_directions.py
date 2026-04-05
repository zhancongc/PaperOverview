"""
研究方向配置

定义系统支持的研究方向，用于提高文献搜索的相关性
"""

RESEARCH_DIRECTIONS = {
    "computer": {
        "id": "computer",
        "name": "计算机科学",
        "name_en": "Computer Science",
        "description": "计算机科学与技术领域，包括人工智能、软件工程、网络安全等",
        "keywords": [
            "人工智能", "机器学习", "深度学习", "自然语言处理", "计算机视觉",
            "软件工程", "程序分析", "符号执行", "形式化验证",
            "网络安全", "密码学", "区块链", "分布式系统",
            "数据库", "大数据", "云计算", "边缘计算",
            "算法", "数据结构", "操作系统", "计算机网络",
            "人机交互", "信息检索", "推荐系统", "计算语言学"
        ],
        "abbreviations": {
            "AI": "Artificial Intelligence",
            "ML": "Machine Learning",
            "DL": "Deep Learning",
            "NLP": "Natural Language Processing",
            "CV": "Computer Vision",
            "SE": "Software Engineering",
            "OS": "Operating System",
            "DB": "Database",
            "API": "Application Programming Interface",
            "GUI": "Graphical User Interface",
            "CLI": "Command Line Interface",
            "CAS": "Computer Algebra System",
        },
        "sub_directions": {
            "ai": "人工智能",
            "se": "软件工程",
            "security": "网络安全",
            "system": "计算机系统",
            "theory": "计算机理论",
            "symbolic_computation": "符号计算与计算机代数系统",
        }
    },
    "materials": {
        "id": "materials",
        "name": "材料科学",
        "name_en": "Materials Science",
        "description": "材料科学与工程领域，包括金属材料、无机非金属材料、高分子材料、复合材料等",
        "keywords": [
            "金属材料", "陶瓷材料", "高分子材料", "复合材料", "纳米材料",
            "半导体材料", "超导材料", "磁性材料", "光学材料",
            "材料表征", "X射线衍射", "电子显微镜", "光谱分析",
            "材料合成", "材料加工", "热处理", "表面处理",
            "材料性能", "力学性能", "电学性能", "热学性能",
            "材料设计", "材料模拟", "计算材料学", "材料基因组"
        ],
        "abbreviations": {
            "XRD": "X-ray Diffraction",
            "SEM": "Scanning Electron Microscopy",
            "TEM": "Transmission Electron Microscopy",
            "EDS": "Energy Dispersive Spectroscopy",
            "XPS": "X-ray Photoelectron Spectroscopy",
            "AFM": "Atomic Force Microscopy",
            "STM": "Scanning Tunneling Microscopy",
            "DFT": "Density Functional Theory",
            "MD": "Molecular Dynamics",
            "FEA": "Finite Element Analysis",
        },
        "sub_directions": {
            "metal": "金属材料",
            "ceramic": "陶瓷材料",
            "polymer": "高分子材料",
            "composite": "复合材料",
            "nanomaterial": "纳米材料",
        }
    },
    "management": {
        "id": "management",
        "name": "管理学",
        "name_en": "Management",
        "description": "管理科学与工程领域，包括运营管理、市场营销、人力资源、战略管理等",
        "keywords": [
            "运营管理", "供应链管理", "物流管理", "质量管理", "项目管理",
            "市场营销", "消费者行为", "品牌管理", "数字营销", "市场调研",
            "人力资源管理", "组织行为学", "领导力", "团队管理", "绩效管理",
            "战略管理", "创新管理", "创业管理", "变革管理", "知识管理",
            "管理信息系统", "决策支持系统", "商业智能", "数据分析",
            "精益管理", "六西格玛", "TOC", "DMAIC", "平衡计分卡"
        ],
        "abbreviations": {
            "SCM": "Supply Chain Management",
            "CRM": "Customer Relationship Management",
            "ERP": "Enterprise Resource Planning",
            "HRM": "Human Resource Management",
            "KPI": "Key Performance Indicator",
            "ROI": "Return on Investment",
            "B2B": "Business to Business",
            "B2C": "Business to Consumer",
            "O2O": "Online to Offline",
            "SaaS": "Software as a Service",
        },
        "sub_directions": {
            "operations": "运营管理",
            "marketing": "市场营销",
            "hr": "人力资源管理",
            "strategy": "战略管理",
            "innovation": "创新管理",
        }
    },
}


def get_all_directions():
    """获取所有研究方向"""
    return list(RESEARCH_DIRECTIONS.values())


def get_direction_by_id(direction_id: str):
    """根据ID获取研究方向"""
    return RESEARCH_DIRECTIONS.get(direction_id)


def get_direction_abbreviations(direction_id: str):
    """获取研究方向的缩写词表"""
    direction = get_direction_by_id(direction_id)
    if direction:
        return direction.get("abbreviations", {})
    return {}


def get_direction_keywords(direction_id: str):
    """获取研究方向的关键词列表"""
    direction = get_direction_by_id(direction_id)
    if direction:
        return direction.get("keywords", [])
    return []


def match_direction_by_text(text: str):
    """
    根据文本内容匹配合适的研究方向

    Args:
        text: 输入文本（如题目、关键词等）

    Returns:
        匹配的研究方向ID，如果没有匹配则返回 None
    """
    text_lower = text.lower()

    # 计算每个方向的匹配得分
    scores = {}
    for direction_id, direction_info in RESEARCH_DIRECTIONS.items():
        score = 0

        # 检查关键词匹配
        for keyword in direction_info.get("keywords", []):
            if keyword.lower() in text_lower:
                score += 10

        # 检查中文名称匹配
        if direction_info.get("name", "") in text:
            score += 20

        # 检查英文名称匹配
        if direction_info.get("name_en", "").lower() in text_lower:
            score += 20

        scores[direction_id] = score

    # 返回得分最高的方向
    if scores:
        best_direction = max(scores, key=scores.get)
        if scores[best_direction] > 0:
            return best_direction

    return None


def expand_abbreviation_by_direction(abbreviation: str, direction_id: str) -> str:
    """
    根据研究方向扩展缩写词

    Args:
        abbreviation: 缩写词
        direction_id: 研究方向ID

    Returns:
        扩展后的完整形式，如果没有找到则返回原缩写
    """
    abbreviations = get_direction_abbreviations(direction_id)
    return abbreviations.get(abbreviation.upper(), abbreviation)


# 导出
__all__ = [
    'RESEARCH_DIRECTIONS',
    'get_all_directions',
    'get_direction_by_id',
    'get_direction_abbreviations',
    'get_direction_keywords',
    'match_direction_by_text',
    'expand_abbreviation_by_direction',
]
