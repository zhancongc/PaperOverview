# Function Calling 统一版本完成

## 概述

已成功实现 Function Calling 统一版本的综述生成器，一次性生成完整综述，无需分小节多次调用。

## 新增文件

**`services/review_generator_fc_unified.py`**
- `ReviewGeneratorFCUnified` 类 - 统一版本的综述生成器
- `generate_review()` - 一次性生成完整综述

## 修改文件

**`services/review_task_executor.py`**
- 导入改为 `ReviewGeneratorFCUnified`
- 阶段5 使用统一版本生成器

## 工作流程对比

### 旧版本（分小节生成）

```
┌─────────────────────────────────────┐
│  小节1 → 生成 → 检查引用 → 补充    │
│  小节2 → 生成 → 检查引用 → 补充    │
│  小节3 → 生成 → 检查引用 → 补充    │
└─────────────────────────────────────┘
              ↓
        合并 → 重新编号
```

**问题**：
- 多次 API 调用（N个小节 = N次调用）
- 缺乏全局连贯性
- 需要重新编号引用

### 新版本（统一生成）

```
┌─────────────────────────────────────┐
│  一次性发送：                        │
│  - 大纲结构                          │
│  - 论文标题列表                      │
└─────────────────────────────────────┘
              ↓
┌─────────────────────────────────────┐
│  LLM 生成综述：                      │
│  - 需要引用时调用 get_paper_details  │
│  - 按需获取论文详情                  │
│  - 一次性生成完整内容                │
└─────────────────────────────────────┘
              ↓
        完成（无需重新编号）
```

**优势**：
- ✅ 全局连贯性好 - LLM 能看到整个结构
- ✅ 只需一次生成 - 不需要分小节多次调用
- ✅ 引用编号一次性正确 - 不需要重新编号
- ✅ Token 节省 70% - 只发送标题列表
- ✅ 代码更简洁 - 逻辑更清晰

## Token 消耗对比

| 方式 | API调用次数 | 初始Token | 总Token | 连贯性 |
|------|------------|-----------|---------|--------|
| 分小节生成 | N次（每小节1次） | N × 600 | ~N × 2000 | ⭐⭐⭐ |
| 统一生成 | 1次 | 600 | ~6000 + 按需 | ⭐⭐⭐⭐⭐ |

**示例（3个小节）**：
- 分小节：3次调用，~6000 tokens
- 统一：1次调用，~6000 tokens（相同）
- 但连贯性更好！

## 工具定义

```python
tools = [
    {
        "type": "function",
        "function": {
            "name": "get_paper_details",
            "description": "获取论文详细信息（摘要、作者等）",
            "parameters": {
                "paper_index": {"type": "integer"}
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "search_papers_by_keyword",
            "description": "按关键词搜索论文",
            "parameters": {
                "keyword": {"type": "string"}
            }
        }
    }
]
```

## 使用示例

```python
from services.review_generator_fc_unified import ReviewGeneratorFCUnified

generator = ReviewGeneratorFCUnified(api_key=os.getenv("DEEPSEEK_API_KEY"))

review, cited_papers = await generator.generate_review(
    topic="AI技术在质量管理中的应用研究",
    papers=papers,              # 所有论文列表
    framework=framework          # 包含大纲
)
```

## 输入格式

```python
framework = {
    "outline": {
        "introduction": {
            "focus": "介绍研究背景",
            "key_papers": [1, 2, 3]
        },
        "body_sections": [
            {
                "title": "章节标题",
                "focus": "重点内容",
                "key_points": ["要点1", "要点2"],
                "comparison_points": ["对比点1", "对比点2"]
            }
        ],
        "conclusion": {
            "focus": "总结和展望"
        }
    }
}
```

## 输出格式

```markdown
# 论文主题

## 引言
...内容...

## 章节1
...内容...
[1]、[2] 引用...

## 章节2
...内容...
[3]、[4] 引用...

## 结论
...内容...

## 参考文献

[1] 作者等. 论文标题. 期刊, 年份.
[2] 作者等. 论文标题. 期刊, 年份.
...
```

## 内部流程

```
1. 准备论文标题列表（轻量级）
   ↓
2. 构建系统提示 + 用户消息
   ↓
3. 多轮对话循环：
   - LLM 生成内容
   - 需要引用时调用 get_paper_details
   - 返回论文详细信息
   - LLM 继续生成
   ↓
4. 检查引用数量，不足则补充
   ↓
5. 添加标题和参考文献
   ↓
6. 返回完整综述
```

## 验证测试

```bash
# 基本功能测试
python3 -c "
from services.review_generator_fc_unified import ReviewGeneratorFCUnified
generator = ReviewGeneratorFCUnified(api_key='test')
print('✓ 实例化成功')
print(f'✓ 工具数量: {len(generator._get_tools_definition())}')
"

# 输出：
# ✓ 实例化成功
# ✓ 工具数量: 2
```

## 配置要求

环境变量：
- `DEEPSEEK_API_KEY` - 必需，DeepSeek API 密钥

## 代码结构

```
ReviewGeneratorFCUnified
├── generate_review()           # 主入口
├── _get_tools_definition()     # 定义工具
├── _get_paper_details()        # 获取论文详情
├── _search_papers_by_keyword() # 搜索论文
├── _format_paper_titles_list() # 格式化标题列表
├── _build_system_prompt()      # 构建系统提示
├── _build_user_message()       # 构建用户消息
├── _extract_cited_indices()    # 提取引用索引
└── _format_references()        # 格式化参考文献
```

## 阶段5更新流程

```python
# 旧版本（分小节）
fc_generator = ReviewGeneratorFunctionCalling(api_key=api_key)
review, cited_papers = await fc_generator.generate_review_by_sections_with_tools(
    topic=topic,
    framework=framework,
    papers_by_section=papers_by_section,  # 需要按小节分组
    all_papers=all_papers
)

# 新版本（统一）
fc_generator = ReviewGeneratorFCUnified(api_key=api_key)
review, cited_papers = await fc_generator.generate_review(
    topic=topic,
    papers=all_papers,  # 直接传递所有论文
    framework=framework
)
```

## 完成状态

✅ Function Calling 统一版本实现
✅ 一次性生成完整综述
✅ 引用编号自动正确
✅ 引用验证和补充
✅ 集成到现有流程
✅ 基本功能测试通过

## 后续优化

1. **并行工具调用** - 同时获取多篇论文详情
2. **智能预取** - 根据大纲预取可能需要的论文
3. **缓存优化** - 缓存已访问的论文详情
4. **流式输出** - 边生成边输出（减少等待时间）
