# QuantFlow Pro

QuantFlow Pro 正在从前端原型演进为同仓全栈量化交易平台。本阶段已完成 Phase 0 的基础骨架：

- 前端：`React + TypeScript + Vite + React Router + TanStack Query`
- 后端：`FastAPI + PostgreSQL + Redis + SQLAlchemy + Alembic + RQ`
- 同仓结构：前端保留在仓库根，后端位于 `server/`
- 文档产物：领域边界、ER 图、API/WebSocket 契约、环境规范

## 目录

```text
docs/
  architecture/
server/
  app/
  migrations/
src/
  app/
  entities/
  features/
  shared/
  widgets/
```

## 本地启动

### 前端

1. 安装依赖：`npm install`
2. 复制环境变量：`Copy-Item .env.example .env`
3. 启动：`npm run dev`

### 后端

要求：

- 已安装 `Python 3.12+`
- 本地已启动 PostgreSQL 和 Redis

1. 进入目录：`cd server`
2. 使用 Python 3.12 创建虚拟环境：`py -3.12 -m venv .venv`
3. 激活虚拟环境：`.\.venv\Scripts\Activate.ps1`
4. 升级打包工具：`python -m pip install --upgrade pip setuptools wheel`
5. 安装依赖：`python -m pip install -e .`
6. 复制环境变量：`Copy-Item .env.example .env`
7. 迁移数据库：`alembic upgrade head`
8. 启动服务：`uvicorn app.main:app --reload`

### 基础设施

启动 PostgreSQL、Redis、前端和后端：

```powershell
docker compose up --build
```

默认联调账号：

- `alex@quantflow.local / quantflow-demo`
- `trader@quantflow.local / quantflow-demo`

本地 `local/test` 环境启动时会自动补最小 seed 数据；如已配置 `QF_ALPACA_*`，接口会优先尝试对接 Alpaca paper，否则回退到标准化模拟响应。

## 验证

- 前端类型检查：`npm run check`
- 前端构建：`npm run build`
- 后端测试：`cd server; pytest`
- 健康检查：[http://localhost:8000/health/liveness](http://localhost:8000/health/liveness)

## Phase 0 文档

- [方案决策](docs/architecture/phase-0-decisions.md)
- [模块边界](docs/architecture/module-boundaries.md)
- [ER 图](docs/architecture/er-diagram.md)
- [API 与事件契约](docs/architecture/api-contracts.md)
