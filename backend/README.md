# PersonaFlow Backend

个性化内容推荐系统后端服务

## 快速开始

### 1. 安装依赖

```bash
pip install -r requirements.txt
```

### 2. 配置环境变量

复制 `.env.example` 为 `.env` 并配置必要的环境变量：

```bash
cp .env.example .env
```

### 3. 初始化数据库

```bash
python dev_tools.py init-db
```

### 4. 启动服务

```bash
python run_api.py
```

API 文档将在 http://localhost:8000/docs 提供

## 开发工具

```bash
# 查看数据库统计
python dev_tools.py stats

# 添加RSS源
python dev_tools.py add-source "https://example.com/rss" "示例RSS源"

# 重置数据库
python dev_tools.py reset-db
```

## API 端点

- `GET /api/feed` - 获取推荐文章
- `POST /api/feed/action` - 用户操作反馈
- `GET /api/sources` - 获取订阅源
- `POST /api/sources` - 添加订阅源
- `GET /api/settings/prompt` - 获取AI提示词
- `POST /api/settings/prompt` - 更新AI提示词

## 项目结构 