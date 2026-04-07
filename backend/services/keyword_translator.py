"""
关键词翻译服务
使用 LLM 进行中英文关键词翻译

DEPRECATED: 此模块为 v5.x 旧版本遗留代码，当前 v6.0 流程已不再使用。
保留仅用于历史参考，新代码请使用 PaperSearchAgent + SmartReviewGeneratorFinal。
"""
import warnings
warnings.warn(
    "keyword_translator 模块已废弃，v6.0 流程不再使用",
    DeprecationWarning,
    stacklevel=2
)
import httpx
import asyncio
from typing import List, Dict, Optional
import os
from dotenv import load_dotenv

load_dotenv()


class KeywordTranslator:
    """关键词翻译服务"""

    def __init__(self):
        self.api_key = os.getenv("DEEPSEEK_API_KEY")
        self.base_url = "https://api.deepseek.com/v1"
        self.client = None

    async def _get_client(self):
        """获取 HTTP 客户端"""
        if self.client is None:
            self.client = httpx.AsyncClient(timeout=30.0)
        return self.client

    async def close(self):
        """关闭客户端"""
        if self.client:
            await self.client.aclose()
            self.client = None

    async def translate_keywords(
        self,
        keywords: List[str],
        source_lang: str = "auto",
        target_lang: str = "en"
    ) -> Dict[str, str]:
        """
        批量翻译关键词

        Args:
            keywords: 关键词列表
            source_lang: 源语言 (auto/zh/en)
            target_lang: 目标语言 (zh/en)

        Returns:
            翻译映射 {原词: 译词}
        """
        if not keywords:
            return {}

        if not self.api_key:
            print("[翻译服务] DEEPSEEK_API_KEY 未配置，跳过翻译")
            return {}

        client = await self._get_client()

        # 构建翻译提示词
        if target_lang == "en":
            prompt = f"""请将以下学术关键词翻译成英文（计算机科学领域）：

关键词列表：
{chr(10).join(f"{i+1}. {kw}" for i, kw in enumerate(keywords))}

要求：
1. 只返回翻译结果，格式为：原词 -> 译词
2. 每行一个关键词
3. 保持学术术语的准确性
4. 如果是专有名词（如人名、算法名），保持原文

示例：
机器学习 -> machine learning
深度学习 -> deep learning
Rust -> Rust
"""
        else:  # target_lang == "zh"
            prompt = f"""请将以下学术关键词翻译成中文（计算机科学领域）：

关键词列表：
{chr(10).join(f"{i+1}. {kw}" for i, kw in enumerate(keywords))}

要求：
1. 只返回翻译结果，格式为：原词 -> 译词
2. 每行一个关键词
3. 保持学术术语的准确性
4. 使用中文学术界常用译法

示例：
machine learning -> 机器学习
deep learning -> 深度学习
code translation -> 代码翻译
"""

        try:
            response = await client.post(
                f"{self.base_url}/chat/completions",
                json={
                    "model": "deepseek-chat",
                    "messages": [
                        {"role": "system", "content": "你是一个专业的学术翻译专家，精通计算机科学领域的术语翻译。"},
                        {"role": "user", "content": prompt}
                    ],
                    "temperature": 0.3,
                    "max_tokens": 1000
                },
                headers={"Authorization": f"Bearer {self.api_key}"}
            )
            response.raise_for_status()
            data = response.json()

            # 解析翻译结果
            content = data["choices"][0]["message"]["content"]
            translations = {}

            for line in content.strip().split('\n'):
                line = line.strip()
                if '->' in line:
                    parts = line.split('->')
                    if len(parts) == 2:
                        original = parts[0].strip()
                        translated = parts[1].strip()
                        # 移除可能的序号前缀
                        original = original.split('.', 1)[-1].strip() if '.' in original else original
                        translations[original] = translated

            print(f"[翻译服务] 成功翻译 {len(translations)} 个关键词")
            return translations

        except Exception as e:
            print(f"[翻译服务] 翻译失败: {e}")
            return {}

    async def translate_keyword(
        self,
        keyword: str,
        source_lang: str = "auto",
        target_lang: str = "en"
    ) -> Optional[str]:
        """
        翻译单个关键词

        Args:
            keyword: 关键词
            source_lang: 源语言
            target_lang: 目标语言

        Returns:
            翻译后的关键词，失败返回 None
        """
        result = await self.translate_keywords([keyword], source_lang, target_lang)
        return result.get(keyword)


# 全局实例
translator = KeywordTranslator()


async def translate_search_queries(
    queries: List[Dict],
    translate: bool = True
) -> List[Dict]:
    """
    为搜索查询添加翻译版本

    Args:
        queries: 查询列表，每项包含 query, lang, source 等字段
        translate: 是否启用翻译

    Returns:
        包含原文和翻译的查询列表
    """
    if not translate:
        return queries

    # 分离中英文查询
    zh_keywords = []
    en_keywords = []

    for item in queries:
        query = item.get('query', '')
        lang = item.get('lang', 'auto')

        if lang == 'zh' or (lang == 'auto' and _contains_chinese(query)):
            zh_keywords.append(query)
        elif lang == 'en' or (lang == 'auto' and not _contains_chinese(query)):
            en_keywords.append(query)

    # 批量翻译
    result_queries = list(queries)  # 复制原文查询

    # 中文关键词翻译成英文
    if zh_keywords:
        print(f"[翻译服务] 翻译 {len(zh_keywords)} 个中文关键词为英文...")
        translations = await translator.translate_keywords(zh_keywords, "zh", "en")

        for original, translated in translations.items():
            if translated and translated != original:
                # 为每个英文数据源添加翻译后的查询
                english_sources = ['openalex', 'crossref', 'datacite']
                for source in english_sources:
                    result_queries.append({
                        'query': translated,
                        'lang': 'en',
                        'source': source,
                        'original_query': original,
                        'is_translation': True
                    })

    # 英文关键词翻译成中文
    if en_keywords:
        print(f"[翻译服务] 翻译 {len(en_keywords)} 个英文关键词为中文...")
        translations = await translator.translate_keywords(en_keywords, "en", "zh")

        for original, translated in translations.items():
            if translated and translated != original:
                # 为每个中文数据源添加翻译后的查询
                chinese_sources = ['aminer', 'semantic_scholar', 'chinese_doi']
                for source in chinese_sources:
                    result_queries.append({
                        'query': translated,
                        'lang': 'zh',
                        'source': source,
                        'original_query': original,
                        'is_translation': True
                    })

    print(f"[翻译服务] 翻译后总查询数: {len(result_queries)} (原文 {len(queries)} + 翻译 {len(result_queries) - len(queries)})")

    return result_queries


def _contains_chinese(text: str) -> bool:
    """检测文本是否包含中文"""
    return bool(text and any('\u4e00' <= char <= '\u9fff' for char in text))
