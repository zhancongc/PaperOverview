"""
论文元数据数据库访问层
用于存储和检索所有搜索到的论文元数据
"""
from typing import List, Dict, Optional
from datetime import datetime
from sqlalchemy.orm import Session
from sqlalchemy import or_, and_
from models import PaperMetadata


class PaperMetadataDAO:
    """论文元数据数据访问对象"""

    def __init__(self, session: Session):
        self.session = session

    def save_paper(self, paper: Dict, source: str = "unknown") -> PaperMetadata:
        """
        保存单篇论文元数据

        Args:
            paper: 论文数据字典
            source: 数据源（aminer/openalex/semantic_scholar）

        Returns:
            保存的PaperMetadata对象
        """
        paper_id = paper.get("id")
        if not paper_id:
            raise ValueError("论文必须包含id字段")

        # 检查是否已存在
        existing = self.session.query(PaperMetadata).filter_by(id=paper_id).first()
        if existing:
            # 更新现有记录
            existing.title = paper.get("title", existing.title)
            existing.authors = paper.get("authors", existing.authors)
            existing.year = paper.get("year", existing.year)
            existing.abstract = paper.get("abstract", existing.abstract)
            existing.cited_by_count = paper.get("cited_by_count", existing.cited_by_count)
            existing.is_english = paper.get("is_english", existing.is_english)
            existing.type = paper.get("type", existing.type)
            existing.doi = paper.get("doi", existing.doi)
            existing.concepts = paper.get("concepts", existing.concepts)
            existing.venue_name = paper.get("venue_name", existing.venue_name)
            existing.issue = paper.get("issue", existing.issue)

            # 合并来源信息
            existing_sources = existing.source if isinstance(existing.source, list) else [existing.source]
            new_sources = source if isinstance(source, list) else [source]
            merged_sources = list(set(existing_sources + new_sources))
            existing.source = merged_sources

            existing.url = paper.get("url", existing.url)
            existing.updated_at = datetime.now()
            self.session.commit()
            print(f"[PaperMetadataDAO] 更新论文: {paper_id} - 来源: {merged_sources}")
            return existing
        else:
            # 创建新记录
            paper_metadata = PaperMetadata(
                id=paper_id,
                title=paper.get("title", ""),
                authors=paper.get("authors", []),
                year=paper.get("year"),
                abstract=paper.get("abstract", ""),
                cited_by_count=paper.get("cited_by_count", 0),
                is_english=paper.get("is_english", True),
                type=paper.get("type", ""),
                doi = paper.get("doi", ""),
                concepts = paper.get("concepts", []),
                venue_name = paper.get("venue_name"),
                issue = paper.get("issue"),
                source=source if isinstance(source, list) else [source],
                url = paper.get("url")
            )
            self.session.add(paper_metadata)
            self.session.commit()
            print(f"[PaperMetadataDAO] 新增论文: {paper_id} - 来源: {source}")
            return paper_metadata

    def save_papers(self, papers: List[Dict], source: str = "unknown") -> int:
        """
        批量保存论文元数据

        Args:
            papers: 论文数据列表
            source: 数据源

        Returns:
            新增的论文数量
        """
        new_count = 0
        for paper in papers:
            try:
                paper_id = paper.get("id")
                if not paper_id:
                    continue

                existing = self.session.query(PaperMetadata).filter_by(id=paper_id).first()
                if existing:
                    # 更新现有记录
                    existing.title = paper.get("title", existing.title)
                    existing.authors = paper.get("authors", existing.authors)
                    existing.year = paper.get("year", existing.year)
                    existing.abstract = paper.get("abstract", existing.abstract)
                    existing.cited_by_count = paper.get("cited_by_count", existing.cited_by_count)
                    existing.is_english = paper.get("is_english", existing.is_english)
                    existing.type = paper.get("type", existing.type)
                    existing.doi = paper.get("doi", existing.doi)
                    existing.concepts = paper.get("concepts", existing.concepts)
                    existing.venue_name = paper.get("venue_name", existing.venue_name)
                    existing.issue = paper.get("issue", existing.issue)
                    # 合并来源信息
                    existing_sources = existing.source if isinstance(existing.source, list) else [existing.source]
                    new_sources = source if isinstance(source, list) else [source]
                    merged_sources = list(set(existing_sources + new_sources))
                    existing.source = merged_sources
                    existing.url = paper.get("url", existing.url)
                    existing.updated_at = datetime.now()
                else:
                    # 创建新记录
                    paper_metadata = PaperMetadata(
                        id=paper_id,
                        title=paper.get("title", ""),
                        authors=paper.get("authors", []),
                        year=paper.get("year"),
                        abstract=paper.get("abstract", ""),
                        cited_by_count=paper.get("cited_by_count", 0),
                        is_english=paper.get("is_english", True),
                        type=paper.get("type", ""),
                        doi=paper.get("doi", ""),
                        concepts=paper.get("concepts", []),
                        venue_name=paper.get("venue_name"),
                        issue=paper.get("issue"),
                        source=source if isinstance(source, list) else [source],
                        url=paper.get("url")
                    )
                    self.session.add(paper_metadata)
                    new_count += 1
            except Exception:
                continue

        self.session.commit()
        return new_count

    def get_paper_by_id(self, paper_id: str) -> Optional[PaperMetadata]:
        """根据ID获取论文"""
        return self.session.query(PaperMetadata).filter_by(id=paper_id).first()

    def get_papers_by_ids(self, paper_ids: List[str]) -> List[PaperMetadata]:
        """根据ID列表批量获取论文"""
        if not paper_ids:
            return []
        return self.session.query(PaperMetadata).filter(
            PaperMetadata.id.in_(paper_ids)
        ).all()

    def search_papers(
        self,
        keyword: str = None,
        year: int = None,
        min_year: int = None,
        max_year: int = None,
        is_english: bool = None,
        source: str = None,
        limit: int = 100
    ) -> List[PaperMetadata]:
        """
        搜索论文（支持模糊搜索和多关键词）

        Args:
            keyword: 标题关键词（支持多个词，空格分隔）
            year: 指定年份
            min_year: 最小年份
            max_year: 最大年份
            is_english: 是否英文文献
            source: 数据源
            limit: 返回数量限制

        Returns:
            论文列表
        """
        from sqlalchemy import or_

        query = self.session.query(PaperMetadata)

        if keyword:
            # 处理多关键词搜索
            # 如果keyword包含空格，拆分成多个词进行OR搜索
            keywords = keyword.split()
            if len(keywords) > 1:
                # 多关键词：使用OR连接多个LIKE条件
                conditions = [PaperMetadata.title.like(f"%{kw}%") for kw in keywords]
                query = query.filter(or_(*conditions))
            else:
                # 单关键词：直接LIKE搜索
                query = query.filter(PaperMetadata.title.like(f"%{keyword}%"))

        if year:
            query = query.filter(PaperMetadata.year == year)
        else:
            if min_year:
                query = query.filter(PaperMetadata.year >= min_year)
            if max_year:
                query = query.filter(PaperMetadata.year <= max_year)

        if is_english is not None:
            query = query.filter(PaperMetadata.is_english == is_english)

        if source:
            query = query.filter(PaperMetadata.source == source)

        return query.order_by(PaperMetadata.cited_by_count.desc()).limit(limit).all()

    def get_statistics(self) -> Dict:
        """获取论文库统计信息"""
        total = self.session.query(PaperMetadata).count()

        english_count = self.session.query(PaperMetadata).filter(
            PaperMetadata.is_english == True
        ).count()

        current_year = datetime.now().year
        recent_count = self.session.query(PaperMetadata).filter(
            PaperMetadata.year >= current_year - 5
        ).count()

        # 按数据源统计
        source_stats = self.session.query(
            PaperMetadata.source,
            PaperMetadata.id
        ).group_by(PaperMetadata.source).all()

        # 按年份统计
        year_stats = self.session.query(
            PaperMetadata.year,
            PaperMetadata.id
        ).group_by(PaperMetadata.year).order_by(PaperMetadata.year.desc()).limit(10).all()

        return {
            "total": total,
            "english_count": english_count,
            "english_ratio": english_count / total if total > 0 else 0,
            "recent_count": recent_count,
            "recent_ratio": recent_count / total if total > 0 else 0,
            "sources": {source: count for source, count in source_stats},
            "years": {year: count for year, count in year_stats}
        }

    def delete_paper(self, paper_id: str) -> bool:
        """删除论文"""
        paper = self.session.query(PaperMetadata).filter_by(id=paper_id).first()
        if paper:
            self.session.delete(paper)
            self.session.commit()
            return True
        return False

    def get_recent_papers(self, limit: int = 50) -> List[PaperMetadata]:
        """获取最近入库的论文"""
        return self.session.query(PaperMetadata).order_by(
            PaperMetadata.created_at.desc()
        ).limit(limit).all()

    def get_top_cited_papers(self, limit: int = 50) -> List[PaperMetadata]:
        """获取被引次数最多的论文"""
        return self.session.query(PaperMetadata).order_by(
            PaperMetadata.cited_by_count.desc()
        ).limit(limit).all()
