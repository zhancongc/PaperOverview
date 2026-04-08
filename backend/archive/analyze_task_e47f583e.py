"""
分析任务 e47f583e 的详细信息
"""
from database import db
from models import ReviewTask, PaperSearchStage, PaperFilterStage, ReviewGenerationStage
from sqlalchemy import desc

db.connect()
session = db.SessionLocal()

# 查找任务
task = session.query(ReviewTask).filter(ReviewTask.id == 'e47f583e').first()
if task:
    print('=== 任务信息 ===')
    print(f'任务ID: {task.id}')
    print(f'主题: {task.topic}')
    print(f'状态: {task.status}')
    print(f'当前阶段: {task.current_stage}')
    print(f'参数: {task.params}')
    print()

# 查找所有搜索阶段
all_searches = session.query(PaperSearchStage).filter(PaperSearchStage.task_id == 'e47f583e').order_by(desc(PaperSearchStage.id)).all()
print(f'=== 搜索阶段记录 ({len(all_searches)} 条) ===')
for i, s in enumerate(all_searches, 1):
    print(f'记录{i}:')
    print(f'  状态: {s.status}')
    print(f'  搜索到的文献数: {s.papers_count}')
    print(f'  搜索查询数量: {s.search_queries_count}')
    print(f'  耗时: {s.duration_ms}ms')
    if s.started_at:
        print(f'  开始时间: {s.started_at}')
    if s.completed_at:
        print(f'  完成时间: {s.completed_at}')
    if s.error_message:
        print(f'  错误信息: {s.error_message}')
    if s.outline:
        print(f'  大纲信息（包含搜索查询）:')
        print(f'  {s.outline}')
    print()

# 查找所有筛选阶段
all_filters = session.query(PaperFilterStage).filter(PaperFilterStage.task_id == 'e47f583e').order_by(desc(PaperFilterStage.id)).all()
print(f'=== 质量筛选阶段记录 ({len(all_filters)} 条) ===')
for i, f in enumerate(all_filters, 1):
    print(f'记录{i}:')
    print(f'  输入文献数: {f.input_papers_count}')
    print(f'  质量过滤移除数: {f.quality_filtered_count}')
    print(f'  主题不相关移除数: {f.topic_irrelevant_count}')
    print(f'  输出文献数: {f.output_papers_count}')
    print(f'  耗时: {f.duration_ms}ms')
    print(f'  错误信息: {f.error_message}')
    if f.quality_filtered_details:
        print(f'  质量过滤详情（前5个）:')
        for j, detail in enumerate(f.quality_filtered_details[:5], 1):
            print(f'    {j}. {detail}')
    if f.topic_irrelevant_details:
        print(f'  主题不相关详情（前5个）:')
        for j, detail in enumerate(f.topic_irrelevant_details[:5], 1):
            print(f'    {j}. {detail}')
    if f.started_at:
        print(f'  开始时间: {f.started_at}')
    if f.completed_at:
        print(f'  完成时间: {f.completed_at}')
    print()

# 查找综述生成阶段
review_gen = session.query(ReviewGenerationStage).filter(ReviewGenerationStage.task_id == 'e47f583e').order_by(desc(ReviewGenerationStage.id)).first()
if review_gen:
    print('=== 综述生成阶段 ===')
    print(f'  输入文献数: {review_gen.papers_count}')
    print(f'  引用文献数: {review_gen.citation_count}')
    print(f'  被引用文献数: {review_gen.cited_papers_count}')
    print(f'  综述长度: {review_gen.review_length}')
    print(f'  耗时: {review_gen.duration_ms}ms')
    print(f'  状态: {review_gen.status}')
    if review_gen.error_message:
        print(f'  错误信息: {review_gen.error_message}')
    print()

session.close()
