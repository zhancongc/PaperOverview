"""
配置管理模块
从环境变量读取服务端配置
"""
import os
from dotenv import load_dotenv

load_dotenv()


class Config:
    """服务端配置类"""

    # ==================== API 配置 ====================
    DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY")
    DEEPSEEK_BASE_URL = os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com")

    AMINER_API_TOKEN = os.getenv("AMINER_API_TOKEN")

    # ==================== 搜索配置 ====================
    # 综述生成验证失败时的最大重试次数
    MAX_RETRIES = int(os.getenv("MAX_RETRIES", "1"))

    # 触发补充搜索的最小文献数量
    MIN_PAPERS_THRESHOLD = int(os.getenv("MIN_PAPERS_THRESHOLD", "20"))

    # 候选池大小为目标数量的倍数
    CANDIDATE_POOL_MULTIPLIER = int(os.getenv("CANDIDATE_POOL_MULTIPLIER", "2"))

    # 每次API调用返回的论文数量上限
    PAPERS_PER_PAGE = int(os.getenv("PAPERS_PER_PAGE", "100"))

    # ==================== API 速率限制 ====================
    # AMiner API 每秒调用次数限制
    AMINER_RATE_LIMIT = float(os.getenv("AMINER_RATE_LIMIT", "1.0"))

    # OpenAlex API 每秒调用次数限制
    OPENALEX_RATE_LIMIT = float(os.getenv("OPENALEX_RATE_LIMIT", "5.0"))

    # Semantic Scholar API 每秒调用次数限制
    SEMANTIC_SCHOLAR_RATE_LIMIT = float(os.getenv("SEMANTIC_SCHOLAR_RATE_LIMIT", "0.1"))

    # ==================== 质量评分权重 ====================
    # 被引量在质量评分中的权重 (0.0-1.0)
    CITATION_WEIGHT = float(os.getenv("CITATION_WEIGHT", "0.4"))

    # 新近度在质量评分中的权重 (0.0-1.0)
    RECENCY_WEIGHT = float(os.getenv("RECENCY_WEIGHT", "0.3"))

    # 相关性在质量评分中的权重 (0.0-1.0)
    RELEVANCE_WEIGHT = float(os.getenv("RELEVANCE_WEIGHT", "0.3"))

    @classmethod
    def validate(cls):
        """验证配置有效性"""
        errors = []

        # 验证必需的 API Key
        if not cls.DEEPSEEK_API_KEY:
            errors.append("DEEPSEEK_API_KEY is required")

        # 验证权重总和
        total_weight = cls.CITATION_WEIGHT + cls.RECENCY_WEIGHT + cls.RELEVANCE_WEIGHT
        if abs(total_weight - 1.0) > 0.01:
            errors.append(f"Weights sum to {total_weight}, should be 1.0")

        # 验证数值范围
        if cls.MAX_RETRIES < 0 or cls.MAX_RETRIES > 5:
            errors.append("MAX_RETRIES should be between 0 and 5")

        if cls.MIN_PAPERS_THRESHOLD < 10 or cls.MIN_PAPERS_THRESHOLD > 100:
            errors.append("MIN_PAPERS_THRESHOLD should be between 10 and 100")

        return errors


class UserConfig:
    """用户配置类（从前端表单获取）"""

    # 默认值和范围
    DEFAULTS = {
        "target_count": {"default": 50, "min": 10, "max": 100, "type": "int",
                            "name": "目标文献数量", "description": "综述中引用的文献总数"},
        "recent_years_ratio": {"default": 0.5, "min": 0.1, "max": 1.0, "type": "float",
                              "name": "近5年文献占比", "description": "最近5年发表的文献占比"},
        "english_ratio": {"default": 0.3, "min": 0.1, "max": 1.0, "type": "float",
                         "name": "英文文献占比", "description": "英文文献的占比"},
        "search_years": {"default": 10, "min": 5, "max": 30, "type": "int",
                        "name": "搜索年份范围", "description": "搜索最近N年的文献"},
        "max_search_queries": {"default": 8, "min": 1, "max": 20, "type": "int",
                              "name": "最多搜索查询数", "description": "最多使用多少个搜索查询"},
    }

    @classmethod
    def get_schema(cls):
        """获取前端表单配置 Schema"""
        return {
            "fields": [
                {
                    "key": "target_count",
                    "label": cls.DEFAULTS["target_count"]["name"],
                    "type": "number",
                    "default": cls.DEFAULTS["target_count"]["default"],
                    "min": cls.DEFAULTS["target_count"]["min"],
                    "max": cls.DEFAULTS["target_count"]["max"],
                    "description": cls.DEFAULTS["target_count"]["description"],
                    "required": True
                },
                {
                    "key": "recent_years_ratio",
                    "label": cls.DEFAULTS["recent_years_ratio"]["name"],
                    "type": "slider",
                    "default": cls.DEFAULTS["recent_years_ratio"]["default"],
                    "min": cls.DEFAULTS["recent_years_ratio"]["min"],
                    "max": cls.DEFAULTS["recent_years_ratio"]["max"],
                    "step": 0.1,
                    "description": cls.DEFAULTS["recent_years_ratio"]["description"],
                    "required": True
                },
                {
                    "key": "english_ratio",
                    "label": cls.DEFAULTS["english_ratio"]["name"],
                    "type": "slider",
                    "default": cls.DEFAULTS["english_ratio"]["default"],
                    "min": cls.DEFAULTS["english_ratio"]["min"],
                    "max": cls.DEFAULTS["english_ratio"]["max"],
                    "step": 0.1,
                    "description": cls.DEFAULTS["english_ratio"]["description"],
                    "required": True
                },
                {
                    "key": "search_years",
                    "label": cls.DEFAULTS["search_years"]["name"],
                    "type": "number",
                    "default": cls.DEFAULTS["search_years"]["default"],
                    "min": cls.DEFAULTS["search_years"]["min"],
                    "max": cls.DEFAULTS["search_years"]["max"],
                    "description": cls.DEFAULTS["search_years"]["description"],
                    "required": False,
                    "advanced": True
                },
                {
                    "key": "max_search_queries",
                    "label": cls.DEFAULTS["max_search_queries"]["name"],
                    "type": "number",
                    "default": cls.DEFAULTS["max_search_queries"]["default"],
                    "min": cls.DEFAULTS["max_search_queries"]["min"],
                    "max": cls.DEFAULTS["max_search_queries"]["max"],
                    "description": cls.DEFAULTS["max_search_queries"]["description"],
                    "required": False,
                    "advanced": True
                },
            ]
        }

    @classmethod
    def validate(cls, data: dict):
        """验证用户配置"""
        errors = []

        for key, config in cls.DEFAULTS.items():
            if key in data:
                value = data[key]
                min_val = config["min"]
                max_val = config["max"]

                if value < min_val or value > max_val:
                    errors.append(f"{key} should be between {min_val} and {max_val}")

        return errors


# 启动时验证配置
config_errors = Config.validate()
if config_errors:
    print("[Config] Warning: Configuration errors found:")
    for error in config_errors:
        print(f"  - {error}")

# 导出研究方向配置
from .research_directions import (
    RESEARCH_DIRECTIONS,
    get_all_directions,
    get_direction_by_id,
    get_direction_abbreviations,
    get_direction_keywords,
    match_direction_by_text,
    expand_abbreviation_by_direction,
)

__all__ = [
    'Config',
    'UserConfig',
    'RESEARCH_DIRECTIONS',
    'get_all_directions',
    'get_direction_by_id',
    'get_direction_abbreviations',
    'get_direction_keywords',
    'match_direction_by_text',
    'expand_abbreviation_by_direction',
]
