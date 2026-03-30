# 后端服务

## 安装依赖

```bash
pip install -r requirements.txt
```

## 配置环境变量

复制 `.env.example` 为 `.env`，填入 DeepSeek API Key：

```bash
cp .env.example .env
```

## 运行服务

```bash
python main.py
```

服务将在 `http://localhost:8000` 启动

## API 文档

启动后访问 `http://localhost:8000/docs` 查看 API 文档
