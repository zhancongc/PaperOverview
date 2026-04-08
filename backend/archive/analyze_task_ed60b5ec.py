"""
分析任务 ed60b5ec 的数据
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


def analyze_task(task_id: str = "ed60b5ec"):
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

            # 打印文献样本
            if search_stage.papers_sample:
                print(f"【搜索到的文献样本】（前20篇）:")
                print(f"{'序号':<6}{'标题':<60}{'年份':<8}{'被引':<8}")
                print("-" * 100)
                for i, paper in enumerate(search_stage.papers_sample[:20], 1):
                    title = paper.get('title', '')[:57] + '...' if len(paper.get('title', '')) > 57 else paper.get('title', '')
                    year = paper.get('year', 'N/A')
                    cited = paper.get('cited_by_count', 0)
                    print(f"{i:<6}{title:<60}{year:<8}{cited:<8}")
                if len(search_stage.papers_sample) > 20:
                    print(f"... 共 {len(search_stage.papers_sample)} 篇样本")
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
                print(f"【质量过滤移除详情】（前50篇）:")
                print(f"{'序号':<6}{'得分':<8}{'标题':<50}{'年份':<8}{'被引':<8}")
                print("-" * 100)
                for i, detail in enumerate(filter_stage.quality_filtered_details[:50], 1):
                    title = detail.get('title', '')[:47] + '...' if len(detail.get('title', '')) > 47 else detail.get('title', '')
                    print(f"{i:<6}{detail.get('score', 0):<8.1f}{title:<50}{detail.get('year', 'N/A'):<8}{detail.get('cited', 0):<8}")
                if len(filter_stage.quality_filtered_details) > 50:
                    print(f"... 共 {len(filter_stage.quality_filtered_details)} 篇被移除")
                print()

            # 详细的主题不相关移除详情
            if filter_stage.topic_irrelevant_details:
                print(f"【主题不相关移除详情】（前50篇）:")
                print(f"{'序号':<6}{'标题':<50}{'年份':<8}{'被引':<8}{'来源':<20}{'所属小节'}")
                print("-" * 120)
                for i, detail in enumerate(filter_stage.topic_irrelevant_details[:50], 1):
                    title = detail.get('title', '')[:47] + '...' if len(detail.get('title', '')) > 47 else detail.get('title', '')
                    sections = detail.get('sections', [])
                    sections_str = ", ".join(sections)[:25]
                    print(f"{i:<6}{title:<50}{detail.get('year', 'N/A'):<8}{detail.get('cited', 0):<8}{(detail.get('venue', '')[:18]):<20}{sections_str}")
                if len(filter_stage.topic_irrelevant_details) > 50:
                    print(f"... 共 {len(filter_stage.topic_irrelevant_details)} 篇被移除")
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
