# 归档文件说明

本目录包含旧版本的综述生成器和测试文件，已被新的两阶段生成器替代。

## 保留的核心文件（在 backend/ 目录）

### 综述生成器
- `services/smart_review_generator_final.py` - **最新两阶段生成器**（推荐使用）
  - 集成了 Function Calling 按需获取论文详情
  - 内置 5 条引用规范
  - 支持表格生成
  - 优化的 prompt

### 引用验证器
- `services/citation_validator_v2.py` - **改进版引用验证器**
  - 支持 arXiv ID 提取
  - 作者"佚名"过滤
  - Unicode 编码修复
  - IEEE 格式优化

### 文档导出
- `services/docx_generator.py` - **支持表格的 Word 导出**
  - Markdown 表格解析
  - 自动表头加粗
  - Table Grid 样式

### 运行脚本
- `run_final_generator.py` - 运行最终版生成器

## 归档的旧文件

### 旧版生成器
- `review_generator.py` - 最早版本
- `review_generator_v2_enhanced.py` - 增强版 v2
- `review_generator_function_calling.py` - Function Calling 版本
- `review_generator_fc_unified.py` - 统一 Function Calling 版本
- `smart_review_generator.py` - 智能生成器 v1
- `smart_review_generator_v2.py` - 智能生成器 v2

### 旧版引用验证
- `citation_validator.py` - 第一版引用验证器

### 旧版运行脚本
- `run_smart_review.py` - 运行 v1
- `run_smart_review_v2.py` - 运行 v2
- `example_smart_review.py` - 使用示例
- `generate_review_from_json.py` - 从 JSON 生成

### 测试和临时文件
- 各种 `test_*.py` - 测试脚本
- 各种 `debug_*.py` - 调试脚本
- 各种 `fix_*.py` - 修复脚本
- 各种 `*.md` 和 `*.json` - 生成的测试结果

## 使用建议

新用户请直接使用：
1. `run_final_generator.py` 生成综述
2. `services/smart_review_generator_final.py` 查看生成器实现
3. `services/citation_validator_v2.py` 查看引用验证
4. `services/docx_generator.py` 查看 Word 导出
