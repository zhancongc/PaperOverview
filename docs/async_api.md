# 异步API使用文档

## 概述

从 v4.0 开始，综述生成接口采用异步任务模式，避免长时间等待导致超时。

**v5.1 更新**：新增"查找文献"和"智能分析"接口，支持阶段记录追踪。

## API 接口

### 1. 生成综述（完整流程）

**接口**: `POST /api/smart-generate`

**请求参数**:
```json
{
  "topic": "基于FMEA法的Agent开发项目风险管理研究",
  "target_count": 50,
  "recent_years_ratio": 0.5,
  "english_ratio": 0.3,
  "search_years": 10,
  "max_search_queries": 8
}
```

**响应**:
```json
{
  "success": true,
  "message": "任务已提交，请使用任务ID查询进度",
  "data": {
    "task_id": "751bdaa7",
    "topic": "基于FMEA法的Agent开发项目风险管理研究",
    "status": "pending",
    "poll_url": "/api/tasks/751bdaa7"
  }
}
```

### 2. 查找文献（仅搜索，不生成综述）

**接口**: `POST /api/search-papers`

**请求参数**: 同上

**响应（同步返回）**:
```json
{
  "success": true,
  "data": {
    "topic": "基于FMEA法的Agent开发项目风险管理研究",
    "outline": {
      "introduction": {...},
      "sections": [...],
      "conclusion": {...}
    },
    "papers": [
      {
        "id": "https://openalex.org/W123",
        "title": "...",
        "authors": [...],
        "year": 2023,
        "abstract": "...",
        "cited_by_count": 45
      }
    ],
    "statistics": {
      "total_count": 60,
      "recent_years_count": 35,
      "recent_years_ratio": 0.58,
      "english_count": 40,
      "english_ratio": 0.67
    }
  }
}
```

### 3. 智能分析（仅分析，不搜索文献）

**接口**: `POST /api/smart-analyze`

**请求参数**:
```json
{
  "topic": "基于FMEA法的Agent开发项目风险管理研究"
}
```

**响应（同步返回）**:
```json
{
  "success": true,
  "data": {
    "classification": {
      "primary_domain": "深度学习",
      "secondary_domain": "图像识别",
      "research_type": "应用研究",
      "confidence": 0.85
    },
    "outline": {
      "introduction": {
        "focus": "...",
        "key_papers": [...]
      },
      "sections": [
        {
          "title": "深度学习在图像识别中的应用",
          "focus": "...",
          "key_points": [...],
          "comparison_points": [...],
          "search_keywords": ["深度学习", "图像识别", "CNN"]
        }
      ],
      "conclusion": {
        "focus": "待根据文献内容生成"
      }
    },
    "search_keywords": [
      {
        "section": "深度学习在图像识别中的应用",
        "keywords": ["深度学习", "图像识别", "CNN", "计算机视觉"]
      }
    ]
  }
}
```

### 4. 查询任务状态

**接口**: `GET /api/tasks/{task_id}`

**响应（处理中）**:
```json
{
  "success": true,
  "data": {
    "task_id": "751bdaa7",
    "topic": "基于FMEA法的Agent开发项目风险管理研究",
    "status": "processing",
    "progress": {
      "step": "searching",
      "message": "正在搜索文献 (3/8)...",
      "stage": "3/6"
    },
    "created_at": "2026-04-03T10:30:00",
    "started_at": "2026-04-03T10:30:01",
    "completed_at": null,
    "error": null,
    "has_result": false
  }
}
```

**响应（已完成）**:
```json
{
  "success": true,
  "data": {
    "task_id": "751bdaa7",
    "status": "completed",
    "progress": {},
    "result": {
      "id": 123,
      "topic": "...",
      "review": "综述内容...",
      "papers": [...],
      "statistics": {...},
      "cited_papers_count": 52
    }
  }
}
```

**响应（失败）**:
```json
{
  "success": true,
  "data": {
    "task_id": "751bdaa7",
    "status": "failed",
    "error": "未找到相关文献",
    "completed_at": "2026-04-03T10:32:00"
  }
}
```

## 任务状态

| 状态 | 说明 |
|------|------|
| `pending` | 等待执行 |
| `processing` | 执行中 |
| `completed` | 完成 |
| `failed` | 失败 |

## 进度信息

处理中的任务会返回 `progress` 对象：

```json
{
  "step": "searching",      // 当前步骤
  "message": "正在搜索文献 (3/8)...",  // 进度描述
  "stage": "3/6"            // 阶段进度
}
```

**步骤说明**（v5.1更新）:

| 步骤 | step值 | 阶段 | 说明 |
|------|--------|------|------|
| 分析题目 | `analyzing` | 1/6 | 生成大纲和搜索关键词 |
| 搜索文献 | `searching` | 3/6 | 按小节搜索文献 |
| 筛选文献 | `filtering` | 4/6 | 质量过滤 |
| 生成综述 | `generating` | 5/6 | 生成综述内容 |
| 验证引用 | `validating` | 6/6 | 验证和修复引用 |

**详细阶段说明**:

| 阶段 | 名称 | Temperature | 记录表 |
|------|------|-------------|--------|
| 1 | 生成大纲和搜索关键词 | 0.3 | `outline_generation_stages` |
| 2 | 搜索词优化 | - | - |
| 3 | 按小节搜索文献 | - | `paper_search_stages` |
| 4 | 质量过滤 | - | `paper_filter_stages` |
| 5 | 生成综述 | 0.4 | `review_generation_stages` |
| 6 | 验证和保存 | - | - |

## 前端集成示例

### JavaScript/TypeScript

```typescript
// 1. 提交综述生成任务
async function submitReviewTask(params) {
  const response = await fetch('http://localhost:8000/api/smart-generate', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(params),
  });

  const result = await response.json();
  return result.data.task_id;
}

// 2. 查找文献（同步返回）
async function searchPapers(params) {
  const response = await fetch('http://localhost:8000/api/search-papers', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(params),
  });

  const result = await response.json();
  return result.data;
}

// 3. 智能分析（同步返回）
async function analyzeTopic(topic) {
  const response = await fetch('http://localhost:8000/api/smart-analyze', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ topic }),
  });

  const result = await response.json();
  return result.data;
}

// 4. 查询任务状态
async function pollTaskStatus(taskId) {
  const response = await fetch(`http://localhost:8000/api/tasks/${taskId}`);
  const result = await response.json();
  return result.data;
}

// 5. 完整流程（生成综述）
async function generateReview(topic) {
  // 提交任务
  const taskId = await submitReviewTask({
    topic,
    target_count: 50,
    recent_years_ratio: 0.5,
    english_ratio: 0.3,
  });

  console.log('任务已提交:', taskId);

  // 轮询直到完成
  while (true) {
    const taskInfo = await pollTaskStatus(taskId);

    if (taskInfo.status === 'completed') {
      return taskInfo.result;
    }

    if (taskInfo.status === 'failed') {
      throw new Error(taskInfo.error);
    }

    // 显示进度
    console.log(taskInfo.progress?.message || taskInfo.status);

    // 等待1秒
    await new Promise(resolve => setTimeout(resolve, 1000));
  }
}
```

### React Hook

```typescript
function useReviewGeneration() {
  const [taskId, setTaskId] = useState(null);
  const [status, setStatus] = useState('idle');
  const [progress, setProgress] = useState({});
  const [result, setResult] = useState(null);
  const [error, setError] = useState(null);

  const submitTask = async (params) => {
    const response = await fetch('/api/smart-generate', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(params),
    });

    const data = await response.json();
    setTaskId(data.data.task_id);
    setStatus('polling');
  };

  useEffect(() => {
    if (status !== 'polling' || !taskId) return;

    const interval = setInterval(async () => {
      const response = await fetch(`/api/tasks/${taskId}`);
      const data = await response.json();
      const taskInfo = data.data;

      setProgress(taskInfo.progress || {});

      if (taskInfo.status === 'completed') {
        setStatus('completed');
        setResult(taskInfo.result);
        clearInterval(interval);
      } else if (taskInfo.status === 'failed') {
        setStatus('error');
        setError(taskInfo.error);
        clearInterval(interval);
      }
    }, 1000);

    return () => clearInterval(interval);
  }, [status, taskId]);

  return { status, progress, result, error, submitTask };
}
```

### 完整交互流程

```typescript
// 组件中使用
function ReviewGenerator() {
  const { status, progress, result, error, submitTask } = useReviewGeneration();
  const [topic, setTopic] = useState('');

  const handleSubmit = async () => {
    await submitTask({
      topic,
      target_count: 50,
      recent_years_ratio: 0.5,
      english_ratio: 0.3,
    });
  };

  return (
    <div>
      <input value={topic} onChange={(e) => setTopic(e.target.value)} />
      <button onClick={handleSubmit}>生成综述</button>

      {status === 'polling' && (
        <div>
          <p>进度: {progress.stage || '处理中...'}</p>
          <p>{progress.message}</p>
        </div>
      )}

      {status === 'completed' && (
        <div>
          <h2>综述生成完成！</h2>
          <p>引用文献数: {result.cited_papers_count}</p>
        </div>
      )}

      {status === 'error' && (
        <div>
          <p>错误: {error}</p>
        </div>
      )}
    </div>
  );
}
```

## 轮询建议

1. **轮询间隔**: 建议 1-2 秒
2. **超时时间**: 建议设置 5-10 分钟超时
3. **进度显示**: 显示 `progress.message` 给用户
4. **错误处理**: 处理 `failed` 状态和异常

## 阶段记录查询（v5.1新增）

### 查询任务的所有阶段记录

**接口**: `GET /api/tasks/{task_id}/stages`

**响应**:
```json
{
  "success": true,
  "data": {
    "outline": {
      "outline": {...},
      "search_queries": [...],
      "execution_time": 1.2
    },
    "search": {
      "total_found": 150,
      "papers_by_section": {...},
      "sources": ["openalex", "aminer"]
    },
    "filter": {
      "input_count": 150,
      "output_count": 60,
      "filtered_papers": [...]
    },
    "review": {
      "review": "...",
      "papers_summary": [...],
      "cited_papers_count": 52
    }
  }
}
```

## 兼容性

旧版同步接口仍然可用：`POST /api/smart-generate-sync`

但推荐使用新的异步接口以获得更好的用户体验。

## 错误码

| 错误码 | 说明 |
|--------|------|
| `NO_PAPERS_FOUND` | 未找到相关文献 |
| `INSUFFICIENT_PAPERS` | 找到的文献数量不足 |
| `GENERATION_FAILED` | 综述生成失败 |
| `VALIDATION_FAILED` | 引用验证失败 |
| `API_RATE_LIMIT` | API 调用超限 |
