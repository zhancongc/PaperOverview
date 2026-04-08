# 研究方向选择功能实现总结

## 实现内容

### 1. 研究方向配置文件
**文件**: `config/research_directions.py`

定义了三个研究方向：
- **计算机科学** (computer): AI、软件工程、网络安全等
- **材料科学** (materials): 金属材料、陶瓷材料、纳米材料等
- **管理学** (management): 运营管理、市场营销、人力资源等

每个方向包含：
- ID、中英文名称、描述
- 关键词列表（用于匹配和搜索）
- 缩写词表（用于扩展缩写）
- 子方向列表（更细分的领域）

### 2. API 接口
**文件**: `main.py`

#### GET /api/research-directions
获取所有研究方向列表

响应示例：
```json
{
  "success": true,
  "data": [
    {
      "id": "computer",
      "name": "计算机科学",
      "name_en": "Computer Science",
      "description": "计算机科学与技术领域，包括人工智能、软件工程、网络安全等",
      "keywords": ["人工智能", "机器学习", ...],
      "abbreviations": {"AI": "Artificial Intelligence", ...},
      "sub_directions": {"ai": "人工智能", ...}
    },
    ...
  ]
}
```

#### POST /api/smart-generate
创建综述任务（支持研究方向选择）

请求示例：
```json
{
  "topic": "ML算法优化研究",
  "research_direction_id": "computer",  // 新增参数
  "target_count": 50,
  "recent_years_ratio": 0.5,
  "english_ratio": 0.3
}
```

### 3. 核心功能

#### 缩写词智能扩展
根据研究方向ID扩展缩写词：

| 缩写 | 计算机科学 | 材料科学 | 管理学 |
|------|-----------|---------|--------|
| ML | Machine Learning | Materials Laboratory | Management Level |
| XRD | X-Ray Diffraction | X-Ray Diffraction | - |
| KPI | Key Performance Indicator | - | Key Performance Indicator |
| CAS | Computer Algebra System | - | - |

#### 文本匹配研究方向
根据论文题目自动匹配研究方向：
- "机器学习算法优化" → computer
- "纳米材料合成" → materials
- "供应链管理优化" → management

### 4. 测试验证
**文件**: `test_research_directions_config.py`

测试结果：
- ✅ 获取研究方向列表
- ✅ 根据ID获取研究方向详情
- ✅ 根据文本匹配研究方向
- ✅ 根据研究方向扩展缩写词
- ✅ API 接口正常工作

## 使用方式

### 后端使用

```python
from config.research_directions import (
    get_all_directions,
    get_direction_by_id,
    match_direction_by_text,
    expand_abbreviation_by_direction,
)

# 获取所有方向
directions = get_all_directions()

# 根据ID获取方向
computer = get_direction_by_id("computer")

# 根据文本匹配方向
direction_id = match_direction_by_text("机器学习算法")

# 扩展缩写词
expanded = expand_abbreviation_by_direction("ML", "computer")
# 结果: "Machine Learning"
```

### 前端使用

参考 `docs/frontend_research_direction_example.md` 中的完整示例。

基本流程：
1. 调用 GET /api/research-directions 获取研究方向列表
2. 用户选择研究方向（或选择"自动推断"）
3. 提交任务时将 research_direction_id 传递给后端
4. 后端根据研究方向ID进行关键词扩展和文献搜索

## 优势

### 1. 提高搜索相关性
- 避免缩写词歧义（CAS 在计算机科学中是 Computer Algebra System）
- 使用领域特定的术语和关键词
- 过滤不相关领域的文献

### 2. 用户友好
- 预设研究方向列表，无需手动输入
- 清晰的描述和分类
- 支持"自动推断"保持灵活性

### 3. 易于扩展
- 添加新研究方向只需修改配置文件
- 每个方向独立配置关键词和缩写表
- 支持子方向细分

## 文件清单

### 新增文件
- `config/research_directions.py` - 研究方向配置
- `config/__init__.py` - 配置包初始化
- `test_research_directions_config.py` - 测试文件
- `docs/frontend_research_direction_example.md` - 前端示例

### 修改文件
- `main.py` - 添加研究方向API接口
- `services/contextual_keyword_translator.py` - 支持研究方向ID参数
- `services/review_task_executor.py` - 传递研究方向ID

## 下一步建议

1. **添加更多研究方向**
   - 医学、生物学、物理学、化学等
   - 根据用户需求动态添加

2. **支持子方向选择**
   - 计算机科学下选择"人工智能"、"软件工程"等
   - 提供更精确的搜索范围

3. **用户自定义研究方向**
   - 允许高级用户输入自定义方向
   - 结合LLM自动识别领域关键词

4. **智能推荐**
   - 根据论文题目自动推荐研究方向
   - 显示推荐置信度
