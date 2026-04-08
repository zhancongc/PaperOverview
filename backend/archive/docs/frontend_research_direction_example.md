# 前端研究方向选择功能实现示例

## API 接口

### 1. 获取研究方向列表

```typescript
// GET /api/research-directions
interface ResearchDirection {
  id: string;
  name: string;
  name_en: string;
  description: string;
  keywords: string[];
  abbreviations: Record<string, string>;
  sub_directions: Record<string, string>;
}

interface GetDirectionsResponse {
  success: boolean;
  data: ResearchDirection[];
}

async function getResearchDirections(): Promise<GetDirectionsResponse> {
  const response = await fetch('/api/research-directions');
  return response.json();
}
```

### 2. 创建综述任务（指定研究方向）

```typescript
// POST /api/smart-generate
interface GenerateRequest {
  topic: string;
  research_direction_id?: string;  // 可选: "computer" | "materials" | "management"
  target_count?: number;
  recent_years_ratio?: number;
  english_ratio?: number;
}

async function createReviewTask(request: GenerateRequest) {
  const response = await fetch('/api/smart-generate', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(request)
  });
  return response.json();
}
```

## React 组件示例

```tsx
import React, { useState, useEffect } from 'react';

interface ResearchDirection {
  id: string;
  name: string;
  name_en: string;
  description: string;
}

export function ReviewGeneratorForm() {
  const [directions, setDirections] = useState<ResearchDirection[]>([]);
  const [selectedDirection, setSelectedDirection] = useState<string>('');
  const [topic, setTopic] = useState<string>('');

  // 加载研究方向列表
  useEffect(() => {
    fetch('/api/research-directions')
      .then(res => res.json())
      .then(data => {
        if (data.success) {
          setDirections(data.data);
        }
      });
  }, []);

  const handleSubmit = async () => {
    const request = {
      topic: topic,
      research_direction_id: selectedDirection,  // 可选
      target_count: 50,
      recent_years_ratio: 0.5,
      english_ratio: 0.3
    };

    const response = await fetch('/api/smart-generate', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(request)
    });

    const result = await response.json();
    console.log('任务创建成功:', result.data.task_id);
  };

  return (
    <div className="review-generator-form">
      <h2>文献综述生成器</h2>

      {/* 论文题目输入 */}
      <div className="form-group">
        <label>论文题目 *</label>
        <input
          type="text"
          value={topic}
          onChange={(e) => setTopic(e.target.value)}
          placeholder="请输入论文题目"
        />
      </div>

      {/* 研究方向选择 */}
      <div className="form-group">
        <label>研究方向（可选）</label>
        <select
          value={selectedDirection}
          onChange={(e) => setSelectedDirection(e.target.value)}
        >
          <option value="">自动推断</option>
          {directions.map(direction => (
            <option key={direction.id} value={direction.id}>
              {direction.name} ({direction.name_en})
            </option>
          ))}
        </select>

        {/* 显示选中方向的描述 */}
        {selectedDirection && (
          <div className="direction-description">
            {directions.find(d => d.id === selectedDirection)?.description}
          </div>
        )}
      </div>

      {/* 提交按钮 */}
      <button onClick={handleSubmit} disabled={!topic}>
        生成综述
      </button>
    </div>
  );
}
```

## Vue 3 组件示例

```vue
<template>
  <div class="review-generator-form">
    <h2>文献综述生成器</h2>

    <!-- 论文题目输入 -->
    <div class="form-group">
      <label>论文题目 *</label>
      <input
        v-model="topic"
        type="text"
        placeholder="请输入论文题目"
      />
    </div>

    <!-- 研究方向选择 -->
    <div class="form-group">
      <label>研究方向（可选）</label>
      <select v-model="selectedDirection">
        <option value="">自动推断</option>
        <option
          v-for="direction in directions"
          :key="direction.id"
          :value="direction.id"
        >
          {{ direction.name }} ({{ direction.name_en }})
        </option>
      </select>

      <!-- 显示选中方向的描述 -->
      <div v-if="selectedDirection" class="direction-description">
        {{ selectedDirectionInfo?.description }}
      </div>
    </div>

    <!-- 提交按钮 -->
    <button @click="handleSubmit" :disabled="!topic">
      生成综述
    </button>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue';

interface ResearchDirection {
  id: string;
  name: string;
  name_en: string;
  description: string;
}

const topic = ref('');
const selectedDirection = ref('');
const directions = ref<ResearchDirection[]>([]);

const selectedDirectionInfo = computed(() =>
  directions.value.find(d => d.id === selectedDirection.value)
);

onMounted(async () => {
  const response = await fetch('/api/research-directions');
  const data = await response.json();
  if (data.success) {
    directions.value = data.data;
  }
});

const handleSubmit = async () => {
  const request = {
    topic: topic.value,
    research_direction_id: selectedDirection.value,
    target_count: 50,
    recent_years_ratio: 0.5,
    english_ratio: 0.3
  };

  const response = await fetch('/api/smart-generate', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(request)
  });

  const result = await response.json();
  console.log('任务创建成功:', result.data.task_id);
};
</script>
```

## 研究方向卡片展示

```tsx
// 更直观的卡片式选择界面
export function ResearchDirectionSelector() {
  const [directions, setDirections] = useState<ResearchDirection[]>([]);
  const [selectedDirection, setSelectedDirection] = useState<string | null>(null);

  useEffect(() => {
    fetch('/api/research-directions')
      .then(res => res.json())
      .then(data => {
        if (data.success) {
          setDirections(data.data);
        }
      });
  }, []);

  return (
    <div className="direction-selector">
      <h3>选择研究方向（可选）</h3>

      <div className="direction-cards">
        {/* 自动推断选项 */}
        <div
          className={`direction-card ${selectedDirection === null ? 'selected' : ''}`}
          onClick={() => setSelectedDirection(null)}
        >
          <div className="card-icon">🤖</div>
          <div className="card-title">自动推断</div>
          <div className="card-desc">
            系统将根据论文题目自动判断研究方向
          </div>
        </div>

        {/* 计算机科学 */}
        <div
          className={`direction-card ${selectedDirection === 'computer' ? 'selected' : ''}`}
          onClick={() => setSelectedDirection('computer')}
        >
          <div className="card-icon">💻</div>
          <div className="card-title">计算机科学</div>
          <div className="card-desc">
            人工智能、软件工程、网络安全等
          </div>
        </div>

        {/* 材料科学 */}
        <div
          className={`direction-card ${selectedDirection === 'materials' ? 'selected' : ''}`}
          onClick={() => setSelectedDirection('materials')}
        >
          <div className="card-icon">🔬</div>
          <div className="card-title">材料科学</div>
          <div className="card-desc">
            金属材料、陶瓷材料、高分子材料等
          </div>
        </div>

        {/* 管理学 */}
        <div
          className={`direction-card ${selectedDirection === 'management' ? 'selected' : ''}`}
          onClick={() => setSelectedDirection('management')}
        >
          <div className="card-icon">📊</div>
          <div className="card-title">管理学</div>
          <div className="card-desc">
            运营管理、市场营销、人力资源等
          </div>
        </div>
      </div>
    </div>
  );
}
```

## CSS 样式示例

```css
.direction-cards {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
  gap: 16px;
  margin-top: 16px;
}

.direction-card {
  border: 2px solid #e0e0e0;
  border-radius: 8px;
  padding: 16px;
  text-align: center;
  cursor: pointer;
  transition: all 0.2s;
}

.direction-card:hover {
  border-color: #1976d2;
  background-color: #f5f5f5;
}

.direction-card.selected {
  border-color: #1976d2;
  background-color: #e3f2fd;
}

.card-icon {
  font-size: 32px;
  margin-bottom: 8px;
}

.card-title {
  font-weight: bold;
  margin-bottom: 8px;
}

.card-desc {
  font-size: 14px;
  color: #666;
}
```

## 使用效果

### 1. 提高搜索相关性
当用户选择"计算机科学"研究方向时：
- "CAS" 会被扩展为 "Computer Algebra System"（而非 "Critical Assessment Series"）
- "ML" 会被扩展为 "Machine Learning"（而非 "Materials Laboratory"）

### 2. 减少不相关文献
指定研究方向后，系统会：
- 优先搜索该领域的数据库
- 使用该领域的术语进行翻译
- 过滤掉明显不属于该领域的文献

### 3. 用户友好
- 预设的研究方向列表，用户无需输入
- 清晰的描述和图标，便于理解
- 支持"自动推断"选项，保持灵活性
