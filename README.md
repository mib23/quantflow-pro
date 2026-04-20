# QuantFlow Pro

[English README](./README.en.md)

QuantFlow Pro 是一个面向量化交易场景的同仓全栈项目，用来展示我在产品理解、前后端协同、工程化落地和可扩展架构上的综合能力。

它不是单纯的页面原型，而是围绕真实交易工作流搭起来的一套可继续演进的系统骨架：登录鉴权、账户总览、交易下单、风控事件、策略研究、异步回测、运行部署、实时推送、数据库迁移、测试和容器化联调都已经进入同一个仓库。

## 项目定位

- 面向 GitHub 展示和接单沟通的全栈样板项目
- 聚焦量化交易平台常见核心链路，而不是只做静态界面
- 强调“能继续扩展”的工程结构，而不是一次性 Demo

## 这个项目已经能体现什么

### 1. 完整的业务拆分能力

前端已经按业务域拆成 `auth`、`dashboard`、`trading`、`strategy`、`risk` 等模块；后端也按认证、账户、订单、回测、运行时、风控、行情等模块独立组织。这样的结构更适合后续继续加功能、接第三方、补测试，而不是越写越乱。

### 2. 真正的前后端一体化设计

这不是“前端一套假数据 + 后端一个空壳”。仓库里已经有：

- React + TypeScript + Vite 的前端应用
- FastAPI + PostgreSQL + Redis 的后端服务
- Alembic 数据库迁移
- WebSocket 实时通道
- RQ 异步任务与后台作业
- Docker Compose 联调环境

### 3. 贴近真实交易系统的核心能力

当前版本重点覆盖了几条很适合展示技术实力的链路：

- 登录与会话恢复
- 账户、持仓、净值、PnL 总览
- 下单、撤单、订单状态与成交记录
- 风控规则、风控摘要、命中事件流
- 策略列表、版本管理、异步回测、结果查看与报告下载
- 策略运行实例创建、启动、停止、重启
- 实盘部署审批、运行日志、告警、关联订单和风险事件

### 4. 工程化而不是“只跑得起来”

项目里已经补上了不少实际开发里很重要、但很多演示项目会省略的部分：

- 明确的模块边界和架构文档
- API 与事件契约文档
- 数据模型与迁移版本
- 后端测试用例
- 本地种子数据与演示账号
- 可选的 Alpaca 接入路径

## 适合展示给客户的技术亮点

### 前端

- `React 19 + TypeScript + Vite`
- `React Router` 管理业务页面路由
- `TanStack Query` 处理服务端状态和缓存
- `Zustand` 管理会话状态
- `React Hook Form + Zod` 处理表单与校验
- `Recharts` 展示净值曲线和结果图表
- 按领域拆分的目录结构，便于多人协作和继续扩展

### 后端

- `FastAPI` 提供 REST API 和实时接口
- `SQLAlchemy + Alembic` 管理数据访问与数据库演进
- `PostgreSQL` 负责核心业务数据
- `Redis` 负责缓存、实时通道和队列支撑
- `RQ` 处理回测等异步任务
- `BrokerAdapter` 抽象为后续接入更多券商预留空间

### 架构思路

- 同仓全栈，前后端联调成本低
- 模块化单体，先保证开发效率，再为后续拆分预留边界
- 页面层、数据层、领域层职责清晰
- REST 负责配置和查询，WebSocket 负责实时更新
- 回测、运行时、交易链路分开设计，避免后续互相污染

## 当前主要页面与能力

### Dashboard

- 展示账户净值、现金、购买力、当日损益
- 展示净值曲线、持仓明细、最近风险告警
- 支持后端聚合数据与实时刷新

### Trade

- 展示行情快照、账户摘要、持仓、活跃订单、成交记录
- 支持真实下单和撤单请求
- 接入风险事件流，适合展示交易工作台设计能力

### Strategy

- 支持策略创建、版本管理、版本克隆
- 支持异步回测任务提交、取消、重试
- 支持结果查看和报告下载
- 支持运行实例部署、启停、重启和运行态观察
- 包含实盘审批流，体现更接近生产系统的设计思路

### Risk

- 展示风控摘要、规则列表、规则详情与版本历史
- 支持规则启停
- 展示最近命中事件和硬限制信息

## 仓库结构

```text
docs/
  architecture/   # 架构、ER 图、API 契约
  plan/           # 分阶段实施计划
server/
  app/
    api/
    core/
    integrations/
    modules/
    tests/
  migrations/
src/
  app/
  entities/
  features/
  shared/
  widgets/
```

## 快速启动

### 方式一：一键启动整套环境

```powershell
docker compose up --build
```

启动后默认可访问：

- 前端：`http://localhost:5173`
- 后端：`http://localhost:8000`
- API 文档：`http://localhost:8000/docs`
- 健康检查：`http://localhost:8000/health/liveness`

### 方式二：分别本地启动

前端：

```powershell
npm install
Copy-Item .env.example .env
npm run dev
```

后端：

```powershell
cd server
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip setuptools wheel
python -m pip install -e .
Copy-Item .env.example .env
alembic upgrade head
uvicorn app.main:app --reload
```

## 本地演示说明

- 本地 `local/test` 环境启动时会自动补齐最小演示数据
- 如已配置 `QF_ALPACA_*` 环境变量，系统会优先尝试接入 Alpaca paper
- 未配置时会回退到标准化演示响应，便于本地展示和联调

默认演示账号：

- `alex@quantflow.local / quantflow-demo`
- `trader@quantflow.local / quantflow-demo`

## 自检命令

前端：

```powershell
npm run check
npm run build
```

后端：

```powershell
cd server
pytest
```

## 文档

- [架构决策](./docs/architecture/phase-0-decisions.md)
- [模块边界](./docs/architecture/module-boundaries.md)
- [ER 图](./docs/architecture/er-diagram.md)
- [API 与事件契约](./docs/architecture/api-contracts.md)
- [全栈实施计划](./docs/plan/quantflow-fullstack-implementation-plan.md)

## 适合承接什么类型的项目

如果你在找可以承接中后台系统、交易系统、策略平台、数据看板、运营后台、实时工作台、管理系统的人，这个仓库就是我处理这类项目的一个公开样本。它重点展示的是：

- 复杂业务的信息架构能力
- 前后端联动与接口抽象能力
- 从原型到可扩展系统骨架的推进能力
- 对测试、迁移、部署和长期维护的基本要求

## English Version

For an English introduction, see [README.en.md](./README.en.md).
