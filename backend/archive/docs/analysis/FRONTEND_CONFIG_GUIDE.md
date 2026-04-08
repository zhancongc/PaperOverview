# 前端配置使用指南

## 概述

用户配置通过前端表单收集，作为请求参数传递给 `/api/smart-generate` 接口。无需用户登录，无需保存到数据库。

## 用户配置项

### 基本配置（必填）

| 参数 | 类型 | 默认值 | 范围 | 说明 |
|------|------|--------|------|------|
| `target_count` | number | 50 | 10-100 | 目标文献数量 |
| `recent_years_ratio` | float | 0.5 | 0.1-1.0 | 近5年文献占比 |
| `english_ratio` | float | 0.3 | 0.1-1.0 | 英文文献占比 |

### 高级配置（可选）

| 参数 | 类型 | 默认值 | 范围 | 说明 |
|------|------|--------|------|------|
| `search_years` | number | 10 | 5-30 | 搜索最近N年的文献 |
| `max_search_queries` | number | 8 | 1-20 | 最多使用多少个搜索查询 |

## API 使用

### 获取配置 Schema

```http
GET /api/config/schema
```

响应示例：
```json
{
  "success": true,
  "data": {
    "fields": [
      {
        "key": "target_count",
        "label": "目标文献数量",
        "type": "number",
        "default": 50,
        "min": 10,
        "max": 100,
        "description": "综述中引用的文献总数",
        "required": true
      },
      {
        "key": "recent_years_ratio",
        "label": "近5年文献占比",
        "type": "slider",
        "default": 0.5,
        "min": 0.1,
        "max": 1.0,
        "step": 0.1,
        "description": "最近5年发表的文献占比",
        "required": true
      },
      {
        "key": "english_ratio",
        "label": "英文文献占比",
        "type": "slider",
        "default": 0.3,
        "min": 0.1,
        "max": 1.0,
        "step": 0.1,
        "description": "英文文献的占比",
        "required": true
      },
      {
        "key": "search_years",
        "label": "搜索年份范围",
        "type": "number",
        "default": 10,
        "min": 5,
        "max": 30,
        "description": "搜索最近N年的文献",
        "required": false,
        "advanced": true
      },
      {
        "key": "max_search_queries",
        "label": "最多搜索查询数",
        "type": "number",
        "default": 8,
        "min": 1,
        "max": 20,
        "description": "最多使用多少个搜索查询",
        "required": false,
        "advanced": true
      }
    ]
  }
}
```

### 生成综述请求

```http
POST /api/smart-generate
Content-Type: application/json

{
  "topic": "基于QFD的铝合金轮毂质量管理研究",
  "target_count": 50,
  "recent_years_ratio": 0.5,
  "english_ratio": 0.3,
  "search_years": 10,
  "max_search_queries": 8
}
```

**不传可选参数时使用默认值：**
```json
{
  "topic": "基于QFD的铝合金轮毂质量管理研究"
  // target_count = 50 (默认)
  // recent_years_ratio = 0.5 (默认)
  // english_ratio = 0.3 (默认)
  // search_years = 10 (默认)
  // max_search_queries = 8 (默认)
}
```

## 前端实现示例

### React 示例

```jsx
import { useState, useEffect } from 'react';

function ReviewGenerator() {
  const [schema, setSchema] = useState(null);
  const [formData, setFormData] = useState({
    topic: '',
    target_count: 50,
    recent_years_ratio: 0.5,
    english_ratio: 0.3,
    search_years: 10,
    max_search_queries: 8
  });

  // 获取配置 Schema
  useEffect(() => {
    fetch('/api/config/schema')
      .then(res => res.json())
      .then(data => setSchema(data.data.fields));
  }, []);

  // 渲染表单字段
  const renderField = (field) => {
    const value = formData[field.key] || field.default;

    if (field.type === 'number') {
      return (
        <input
          type="number"
          min={field.min}
          max={field.max}
          value={value}
          onChange={(e) => setFormData({
            ...formData,
            [field.key]: parseInt(e.target.value)
          })}
        />
      );
    }

    if (field.type === 'slider') {
      return (
        <input
          type="range"
          min={field.min}
          max={field.max}
          step={field.step || 0.1}
          value={value}
          onChange={(e) => setFormData({
            ...formData,
            [field.key]: parseFloat(e.target.value)
          })}
        />
      );
    }

    return null;
  };

  // 提交请求
  const handleSubmit = async () => {
    const response = await fetch('/api/smart-generate', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(formData)
    });

    const result = await response.json();
    console.log(result);
  };

  return (
    <div>
      <h1>文献综述生成器</h1>

      {/* 题目输入 */}
      <div>
        <label>论文题目：</label>
        <input
          type="text"
          value={formData.topic}
          onChange={(e) => setFormData({ ...formData, topic: e.target.value })}
        />
      </div>

      {/* 动态渲染配置字段 */}
      {schema && schema.map(field => (
        <div key={field.key}>
          <label>{field.label}：</label>
          {renderField(field)}
          <span>{value}</span>
          <small>{field.description}</small>
        </div>
      ))}

      <button onClick={handleSubmit}>生成综述</button>
    </div>
  );
}

export default ReviewGenerator;
```

### Vue 示例

```vue
<template>
  <div>
    <h1>文献综述生成器</h1>

    <!-- 题目输入 -->
    <div>
      <label>论文题目：</label>
      <input v-model="formData.topic" type="text" />
    </div>

    <!-- 动态渲染配置字段 -->
    <div v-for="field in schema" :key="field.key">
      <label>{{ field.label }}：</label>

      <input
        v-if="field.type === 'number'"
        type="number"
        :min="field.min"
        :max="field.max"
        v-model.number="formData[field.key]"
      />

      <input
        v-else-if="field.type === 'slider'"
        type="range"
        :min="field.min"
        :max="field.max"
        :step="field.step || 0.1"
        v-model.number="formData[field.key]"
      />

      <span>{{ formData[field.key] }}</span>
      <small>{{ field.description }}</small>
    </div>

    <button @click="handleSubmit">生成综述</button>
  </div>
</template>

<script>
export default {
  data() {
    return {
      schema: null,
      formData: {
        topic: '',
        target_count: 50,
        recent_years_ratio: 0.5,
        english_ratio: 0.3,
        search_years: 10,
        max_search_queries: 8
      }
    };
  },

  async mounted() {
    // 获取配置 Schema
    const response = await fetch('/api/config/schema');
    const data = await response.json();
    this.schema = data.data.fields;
  },

  methods: {
    async handleSubmit() {
      const response = await fetch('/api/smart-generate', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(this.formData)
      });

      const result = await response.json();
      console.log(result);
    }
  }
};
</script>
```

## 配置项说明

### 目标文献数量 (target_count)
- 综述中引用的文献总数
- 建议：本科论文 30-50 篇，硕士论文 50-80 篇，博士论文 80-100 篇

### 近5年文献占比 (recent_years_ratio)
- 最近5年发表的文献占比
- 建议：0.4-0.6，保证文献的新颖性

### 英文文献占比 (english_ratio)
- 英文文献的占比
- 建议：0.3-0.5，根据研究领域调整

### 搜索年份范围 (search_years)
- 搜索最近N年的文献
- 建议：10-15 年，计算机等快速发展的领域可缩短到 5-8 年

### 最多搜索查询数 (max_search_queries)
- 最多使用多少个搜索查询
- 建议：8-12 个，增加查询数可提高覆盖率但会降低速度
