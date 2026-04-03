"""
学术术语数据库访问层
用于管理和查询学术术语
"""
from typing import List, Dict, Optional
from sqlalchemy.orm import Session
from sqlalchemy import or_, and_
from models import AcademicTerm


class AcademicTermDAO:
    """学术术语数据访问对象"""

    def __init__(self, session: Session):
        self.session = session

    def create_term(
        self,
        chinese_term: str,
        english_terms: List[str],
        category: str,
        subcategory: str = None,
        aliases: List[str] = None,
        description: str = None,
        usage_examples: List[str] = None,
        priority: int = 0
    ) -> AcademicTerm:
        """
        创建新术语

        Args:
            chinese_term: 中文术语
            english_terms: 英文术语列表
            category: 分类
            subcategory: 子分类
            aliases: 别名列表
            description: 描述
            usage_examples: 使用示例
            priority: 优先级

        Returns:
            创建的术语对象
        """
        # 检查是否已存在
        existing = self.session.query(AcademicTerm).filter_by(chinese_term=chinese_term).first()
        if existing:
            raise ValueError(f"术语 '{chinese_term}' 已存在")

        term = AcademicTerm(
            chinese_term=chinese_term,
            english_terms=english_terms,
            category=category,
            subcategory=subcategory,
            aliases=aliases or [],
            description=description,
            usage_examples=usage_examples or [],
            priority=priority
        )
        self.session.add(term)
        self.session.commit()
        self.session.refresh(term)
        print(f"[AcademicTermDAO] 创建术语: {chinese_term}")
        return term

    def get_term_by_chinese(self, chinese_term: str) -> Optional[AcademicTerm]:
        """根据中文术语获取术语"""
        return self.session.query(AcademicTerm).filter_by(chinese_term=chinese_term).first()

    def get_term_by_id(self, term_id: int) -> Optional[AcademicTerm]:
        """根据ID获取术语"""
        return self.session.query(AcademicTerm).filter_by(id=term_id).first()

    def search_terms(
        self,
        keyword: str = None,
        category: str = None,
        limit: int = 100
    ) -> List[AcademicTerm]:
        """
        搜索术语

        Args:
            keyword: 关键词（匹配中文术语、英文术语或别名）
            category: 分类筛选
            limit: 返回数量限制

        Returns:
            术语列表
        """
        query = self.session.query(AcademicTerm).filter(AcademicTerm.is_active == True)

        if keyword:
            # 搜索中文术语
            chinese_match = AcademicTerm.chinese_term.like(f"%{keyword}%")
            # 搜索英文术语（JSON字段搜索）
            # SQLite JSON 搜索需要使用 json_extract
            try:
                english_match = AcademicTerm.english_terms.like(f"%{keyword}%")
                alias_match = AcademicTerm.aliases.like(f"%{keyword}%")
                query = query.filter(or_(chinese_match, english_match, alias_match))
            except:
                # 如果 JSON 搜索不支持，只搜索中文术语
                query = query.filter(chinese_match)

        if category:
            query = query.filter(AcademicTerm.category == category)

        return query.order_by(AcademicTerm.priority.desc()).limit(limit).all()

    def get_terms_by_category(self, category: str) -> List[AcademicTerm]:
        """获取指定分类的所有术语"""
        return self.session.query(AcademicTerm).filter(
            and_(
                AcademicTerm.category == category,
                AcademicTerm.is_active == True
            )
        ).order_by(AcademicTerm.priority.desc()).all()

    def get_all_categories(self) -> List[str]:
        """获取所有分类"""
        results = self.session.query(AcademicTerm.category).filter(
            AcademicTerm.is_active == True
        ).distinct().all()
        return [r[0] for r in results]

    def update_term(
        self,
        term_id: int,
        english_terms: List[str] = None,
        aliases: List[str] = None,
        description: str = None,
        is_active: bool = None
    ) -> Optional[AcademicTerm]:
        """更新术语"""
        term = self.get_term_by_id(term_id)
        if not term:
            return None

        if english_terms is not None:
            term.english_terms = english_terms
        if aliases is not None:
            term.aliases = aliases
        if description is not None:
            term.description = description
        if is_active is not None:
            term.is_active = is_active

        self.session.commit()
        self.session.refresh(term)
        return term

    def delete_term(self, term_id: int) -> bool:
        """删除术语（软删除，设置is_active=False）"""
        term = self.get_term_by_id(term_id)
        if not term:
            return False

        term.is_active = False
        self.session.commit()
        return True

    def get_statistics(self) -> Dict:
        """获取术语库统计信息"""
        total = self.session.query(AcademicTerm).filter(AcademicTerm.is_active == True).count()

        # 按分类统计（使用 COUNT）
        from sqlalchemy import func
        category_stats = self.session.query(
            AcademicTerm.category,
            func.count(AcademicTerm.id)
        ).filter(AcademicTerm.is_active == True).group_by(
            AcademicTerm.category
        ).all()

        return {
            "total": total,
            "categories": {cat: count for cat, count in category_stats}
        }

    def batch_import_terms(self, terms_data: List[Dict]) -> Dict:
        """
        批量导入术语

        Args:
            terms_data: 术语数据列表

        Returns:
            导入结果统计
        """
        success_count = 0
        skip_count = 0
        error_count = 0

        for data in terms_data:
            try:
                # 检查是否已存在
                existing = self.get_term_by_chinese(data['chinese_term'])
                if existing:
                    skip_count += 1
                    continue

                self.create_term(
                    chinese_term=data['chinese_term'],
                    english_terms=data.get('english_terms', []),
                    category=data['category'],
                    subcategory=data.get('subcategory'),
                    aliases=data.get('aliases', []),
                    description=data.get('description'),
                    usage_examples=data.get('usage_examples', []),
                    priority=data.get('priority', 0)
                )
                success_count += 1
            except Exception as e:
                print(f"[AcademicTermDAO] 导入术语失败: {data.get('chinese_term')} - {e}")
                error_count += 1

        return {
            "success": success_count,
            "skipped": skip_count,
            "errors": error_count,
            "total": len(terms_data)
        }
