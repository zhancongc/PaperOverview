"""
智能论文搜索服务
结合本地数据库和外部API，提高搜索效率
"""
from typing import List, Dict, Optional
from datetime import datetime


class SmartPaperSearchService:
    """智能论文搜索服务"""

    def __init__(self, scholarflux, db_session_factory):
        """
        Args:
            scholarflux: ScholarFlux 实例
            db_session_factory: 数据库会话工厂函数
        """
        self.scholarflux = scholarflux
        self.get_db_session = db_session_factory

    async def search(
        self,
        query: str,
        years_ago: int = 5,
        limit: int = 100,
        min_citations: int = 0,
        use_all_sources: bool = True,
        lang: str = None,
        keywords: List[str] = None,
        search_mode: str = None,
        use_cache: bool = True
    ) -> List[Dict]:
        """
        智能搜索：先查数据库，再查外部API

        Args:
            query: 搜索关键词
            years_ago: 近N年
            limit: 返回数量
            min_citations: 最小被引量
            use_all_sources: 是否使用所有数据源
            lang: 语言标识
            keywords: 关键词列表
            search_mode: 搜索模式
            use_cache: 是否使用数据库缓存

        Returns:
            论文列表
        """
        db_papers = []
        external_papers = []
        seen_ids = set()

        # 1. 先查询数据库
        if use_cache:
            try:
                with self._get_db_session() as session:
                    from services.paper_metadata_dao import PaperMetadataDAO
                    dao = PaperMetadataDAO(session)

                    # 计算年份范围
                    current_year = datetime.now().year
                    min_year = current_year - years_ago

                    # 从数据库搜索
                    db_results = dao.search_papers(
                        keyword=query,
                        min_year=min_year,
                        max_year=current_year,
                        limit=limit * 2  # 多取一些，后续筛选
                    )

                    # 过滤被引量
                    for paper in db_results:
                        cited = paper.cited_by_count or 0
                        if cited >= min_citations:
                            paper_dict = paper.to_paper_dict()
                            paper_dict['_from_db'] = True  # 标记来自数据库
                            db_papers.append(paper_dict)
                            seen_ids.add(paper.id)

            except Exception as e:
                print(f"[SmartSearch] 数据库查询失败: {e}")

        # 2. 如果数据库结果不足，查询外部API
        needed = limit - len(db_papers)
        if needed > 0:
            try:
                external_papers = await self.scholarflux.search(
                    query=query,
                    years_ago=years_ago,
                    limit=needed * 2,  # 多取一些，后续去重
                    min_citations=min_citations,
                    use_all_sources=use_all_sources,
                    lang=lang,
                    keywords=keywords,
                    search_mode=search_mode
                )

                # 过滤掉已在数据库中的论文
                filtered_external = []
                for paper in external_papers:
                    paper_id = paper.get("id")
                    if paper_id and paper_id not in seen_ids:
                        paper['_from_db'] = False  # 标记来自外部API
                        filtered_external.append(paper)
                        seen_ids.add(paper_id)

                external_papers = filtered_external

            except Exception as e:
                print(f"[SmartSearch] 外部API查询失败: {e}")

        # 3. 合并结果
        all_papers = db_papers + external_papers

        # 4. 按相关性排序
        all_papers = self._sort_by_relevance(all_papers)

        # 只在找到论文时输出日志
        if all_papers:
            db_count = len(db_papers)
            ext_count = len(external_papers)
            total_count = len(all_papers[:limit])
            sources = []
            if db_count > 0:
                sources.append(f"数据库{db_count}篇")
            if ext_count > 0:
                sources.append(f"API{ext_count}篇")
            print(f"[搜索] '{query}': 找到 {total_count} 篇 ({', '.join(sources)})")

        return all_papers[:limit]

    async def search_papers(
        self,
        query: str,
        years_ago: int = 5,
        limit: int = 100,
        min_citations: int = 0,
        use_all_sources: bool = True,
        lang: str = None,
        keywords: List[str] = None,
        search_mode: str = None,
        use_cache: bool = True
    ) -> List[Dict]:
        """
        搜索论文（兼容旧接口）

        该方法与 search() 方法完全相同，提供向后兼容性
        """
        return await self.search(
            query=query,
            years_ago=years_ago,
            limit=limit,
            min_citations=min_citations,
            use_all_sources=use_all_sources,
            lang=lang,
            keywords=keywords,
            search_mode=search_mode,
            use_cache=use_cache
        )

    def _sort_by_relevance(self, papers: List[Dict]) -> List[Dict]:
        """按相关性排序（综合考虑被引量和年份）"""
        current_year = datetime.now().year

        def score(paper):
            cited = paper.get("cited_by_count", 0)
            year = paper.get("year")
            year_score = 0

            if year:
                years_ago = current_year - year
                if years_ago <= 5:
                    year_score = 10
                elif years_ago <= 10:
                    year_score = 5

            return cited * 2 + year_score

        return sorted(papers, key=score, reverse=True)

    def _get_db_session(self):
        """获取数据库会话"""
        try:
            session = next(self.get_db_session())
            return session
        except StopIteration:
            return None

    async def get_paper_by_id(self, paper_id: str) -> Optional[Dict]:
        """根据ID获取论文（先查数据库，再查外部API）"""
        # 1. 先查数据库
        try:
            with self._get_db_session() as session:
                from services.paper_metadata_dao import PaperMetadataDAO
                dao = PaperMetadataDAO(session)
                paper = dao.get_paper_by_id(paper_id)
                if paper:
                    print(f"[SmartSearch] 从数据库获取论文: {paper_id}")
                    return paper.to_paper_dict()
        except Exception as e:
            print(f"[SmartSearch] 数据库查询失败: {e}")

        # 2. 数据库没有，尝试外部API
        print(f"[SmartSearch] 数据库未找到，尝试外部API: {paper_id}")
        # TODO: 可以调用外部API获取单篇论文详情

        return None

    def get_statistics(self) -> Dict:
        """获取论文库统计信息"""
        try:
            with self._get_db_session() as session:
                from services.paper_metadata_dao import PaperMetadataDAO
                dao = PaperMetadataDAO(session)
                return dao.get_statistics()
        except Exception as e:
            print(f"[SmartSearch] 获取统计信息失败: {e}")
            return {}
