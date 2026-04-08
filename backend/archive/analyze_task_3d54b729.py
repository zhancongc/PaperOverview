"""
分析任务 3d54b729 的数据
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from database import db
from models import (
    PaperSearchStage,
    PaperFilterStage,
    PaperSearchSource,
    ReviewTask
)
from sqlalchemy import func


def analyze_task(task_id: str = "3d54b729"):
    """分析任务数据"""
    print(f"\n{'='*80}")
    print(f"分析任务: {task_id}")
    print(f"{'='*80}\n")

    session = next(db.get_session())
    try:
        # 1. 任务基本信息
        task = session.query(ReviewTask).filter_by(id=task_id).first()
        if task:
            print(f"【任务信息】")
            print(f"  主题: {task.topic}")
            print(f"  状态: {task.status}")
            print(f"  当前阶段: {task.current_stage}")
            print(f"  创建时间: {task.created_at}")
            print()

        # 2. 搜索阶段
        search_stage = session.query(PaperSearchStage).filter_by(task_id=task_id).first()
        if search_stage:
            print(f"【搜索阶段】")
            print(f"  搜索查询数: {search_stage.search_queries_count}")
            print(f"  搜索到文献数: {search_stage.papers_count}")
            print(f"  文献摘要统计: {search_stage.papers_summary}")
            print(f"  状态: {search_stage.status}")
            if search_stage.error_message:
                print(f"  错误: {search_stage.error_message}")
            print()

        # 3. 筛选阶段
        filter_stage = session.query(PaperFilterStage).filter_by(task_id=task_id).first()
        if filter_stage:
            print(f"【筛选阶段】")
            print(f"  输入文献数: {filter_stage.input_papers_count}")
            print(f"  质量过滤移除数: {filter_stage.quality_filtered_count}")
            print(f"  主题不相关移除数: {filter_stage.topic_irrelevant_count}")
            print(f"  输出文献数: {filter_stage.output_papers_count}")
            print(f"  状态: {filter_stage.status}")
            if filter_stage.error_message:
                print(f"  错误: {filter_stage.error_message}")
            print()

            # 详细的质量过滤移除详情
            if filter_stage.quality_filtered_details:
                print(f"【质量过滤移除详情】(前50篇)")
                for i, detail in enumerate(filter_stage.quality_filtered_details[:50], 1):
                    print(f"  [{i}] {detail.get('title', '')[:60]}")
                    print(f"      得分: {detail.get('score', 0):.1f}, 年份: {detail.get('year')}, 被引: {detail.get('cited', 0)}, 来源: {detail.get('venue', '')[:30]}")
                print()

            # 详细的主题不相关移除详情
            if filter_stage.topic_irrelevant_details:
                print(f"【主题不相关移除详情】(前50篇)")
                for i, detail in enumerate(filter_stage.topic_irrelevant_details[:50], 1):
                    print(f"  [{i}] {detail.get('title', '')[:60]}")
                    print(f"      年份: {detail.get('year')}, 被引: {detail.get('cited', 0)}, 来源: {detail.get('venue', '')[:30]}")
                print()

            # 筛选后统计
            if filter_stage.output_papers_summary:
                print(f"【筛选后统计】")
                print(f"  {filter_stage.output_papers_summary}")
                print()

        # 4. 搜索关键词统计
        print(f"【搜索关键词统计】")
        stats = session.query(
            PaperSearchSource.search_keyword,
            func.count(PaperSearchSource.paper_id).label('count')
        ).filter(
            PaperSearchSource.task_id == task_id
        ).group_by(
            PaperSearchSource.search_keyword
        ).order_by(
            func.count(PaperSearchSource.paper_id).desc()
        ).all()

        print(f"  共 {len(stats)} 个关键词:")
        for keyword, count in stats:
            print(f"    - {keyword}: {count} 篇")
        print()

        # 5. 计算总移除数量
        if filter_stage:
            total_removed = (filter_stage.quality_filtered_count or 0) + (filter_stage.topic_irrelevant_count or 0)
            print(f"【数据流失分析】")
            print(f"  搜索到: {filter_stage.input_papers_count} 篇")
            print(f"  质量过滤移除: {filter_stage.quality_filtered_count or 0} 篇")
            print(f"  主题不相关移除: {filter_stage.topic_irrelevant_count or 0} 篇")
            print(f"  总移除: {total_removed} 篇")
            print(f"  保留: {filter_stage.output_papers_count} 篇")
            if filter_stage.input_papers_count > 0:
                retention_rate = (filter_stage.output_papers_count / filter_stage.input_papers_count * 100)
                print(f"  保留率: {retention_rate:.1f}%")
            print()

        print(f"{'='*80}")

    finally:
        session.close()


if __name__ == "__main__":
    analyze_task()
