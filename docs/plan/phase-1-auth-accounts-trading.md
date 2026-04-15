# Phase 1：认证、账户与基础交易闭环

## 阶段目标

- 以 Phase 0 已完成的前后端骨架为基础，替换当前 auth、accounts、orders、market_data 相关 demo/mock 返回值。
- 打通一期最小业务闭环：`登录 -> 查看账户 -> 查看订单 -> 下单 -> 撤单 -> 订单状态回推`。
- 让 `Trade` 页面从“原型演示”升级为“可联调、可验收、可追踪”的真实交易工作台。

## 进入条件与完成定义

### 进入条件

- `server/` FastAPI、PostgreSQL、Redis、Alembic、RQ 基础骨架可本地启动。
- `src/` 已完成路由化改造，`auth`、`trading`、`accounts` 相关页面和 API 封装已具备接入点。
- 一期边界保持不变：美股、单账户、单 Broker（`Alpaca`）、模块化单体。

### 完成定义

- 用户可通过真实认证流程登录、刷新令牌、登出并获取当前用户信息。
- 系统可读取真实或 paper trading 账户的账户总览、持仓、订单、成交。
- 用户可提交订单、撤销订单，并在前端看到与后端一致的订单状态。
- 最小行情订阅可工作，`Trade` 页能显示选中标的报价并接收订单状态推送。
- 所有关键写操作带幂等键，关键交易动作写入审计日志。

### 输出给下一阶段

- 稳定的用户会话模型、账户查询模型、订单生命周期模型。
- 可被 Dashboard 和 Risk 复用的账户、持仓、订单、成交接口。
- 订单状态变更事件、行情事件、基础审计事件，为 Phase 2 风控联动和 Dashboard 去 mock 提供输入。

## 范围与非目标

### 本阶段必做闭环

- 认证：登录、刷新、登出、当前用户信息、基础 RBAC 上下文。
- 账户：Broker 账户读取、账户总览、持仓、订单列表、成交列表。
- 交易：下单、撤单、订单状态同步、幂等键校验、Broker 订单号映射。
- 行情：最小 quote 订阅、行情缓存、前端 WebSocket 订阅与断线重连。
- 前端：`LoginPage`、`TradePage`、交易表单、订单列表从 mock 切换为真实 API。

### 可延后项

- MFA、多设备会话管理、细粒度权限策略。
- Level 2 深度、逐笔成交流、批量撤单、改单。
- 多账户切换、多 Broker 抽象扩展、复杂订单类型。
- 高级交易组件体验优化，如快捷键、预估滑点、乐观更新。

### 不在本阶段处理

- Dashboard 指标真实化。
- 风控规则配置和下单前风控阻断。
- 策略版本管理、回测任务、运行实例。
- 报表、运营后台、生产级发布能力。

## 工作流拆解

### 前端

- 将 `src/features/auth/api/login.ts` 从 demo 登录切换为真实接口调用，同时补充刷新令牌、登出、`/auth/me` 获取与失败态处理。
- 在用户状态存储中固化 `accessToken`、`refreshToken`、用户角色与会话恢复逻辑，保证刷新页面后能恢复登录态。
- 为受保护路由增加基础守卫，未登录用户统一跳转登录页；已登录用户可访问交易页和账户相关页面。
- 将 `src/features/trading/api/getTradingWorkspace.ts` 中对 `mockTradingWorkspace` 的依赖缩减到仅保留占位行情深度，账户、订单、下单必须走真实 API。
- 改造 `OrderEntryForm`：补充必填校验、数量/价格边界校验、提交中态、成功/失败提示、重复点击保护。
- 订单列表与成交列表统一使用查询层管理，支持主动刷新与收到订单事件后的局部更新。
- 新增 WebSocket 客户端基础能力，订阅 `market.quote.<symbol>` 和 `orders.status.<account_id>`，处理心跳、断线重连、过期鉴权。

### 后端

- 完成 `auth` 模块的最小真实实现：用户表查询、密码校验、JWT access token、refresh token、登出失效机制。
- 明确角色上下文至少包含 `ADMIN`、`TRADER`、`RESEARCHER`，并在接口层完成最小权限校验。
- 完成 `accounts` 模块：读取已绑定的 `broker_accounts`，同步并返回账户总览、持仓、成交、订单列表所需数据。
- 完成 `orders` 模块：接收下单请求、写入内部订单、调用 `BrokerAdapter` 提交、落地内部订单号与外部订单号映射、处理撤单。
- 建立订单状态机的最小集合：`PENDING_SUBMIT`、`SUBMITTED`、`OPEN`、`PARTIALLY_FILLED`、`FILLED`、`CANCEL_REQUESTED`、`CANCELED`、`REJECTED`、`FAILED`。
- 为下单和撤单实现幂等保护：同一 `idempotency_key` 不得重复创建内部订单。
- 完成 `market_data` 模块的最小 quote 能力：查询单标的报价、订阅报价、将事件广播到 WebSocket 频道。
- 订单状态更新采用“Broker 回报优先、轮询补偿兜底”的最小实现，避免因推送丢失导致前端状态长期不一致。

### 数据与集成

- 优先落地数据表：`users`、`broker_accounts`、`account_balances`、`positions`、`orders`、`executions`。
- `users` 至少包含登录所需字段、角色、状态、审计字段；密码哈希不得明文存储。
- `broker_accounts` 保存用户与 Alpaca 账户绑定关系、环境类型、凭证引用、同步状态。
- `orders` 保存内部订单 ID、外部订单 ID、账户 ID、标的、方向、数量、价格、状态、幂等键、失败原因。
- `executions` 保存成交回报、成交时间、成交数量、成交价格、手续费、关联订单 ID。
- Redis 用于会话缓存、WebSocket 订阅广播、行情最新报价缓存、短期订单状态缓存。
- `BrokerAdapter` 在本阶段至少提供：查询账户、查询持仓、查询订单、提交订单、撤单、获取报价、订阅或轮询订单状态。

### 测试与运维

- 建立最小联调种子数据：管理员、交易员用户各一组，至少一组 Alpaca paper account 绑定。
- 为认证、账户、订单接口增加集成测试，确保数据库写入、Broker 适配层 mock、错误码符合契约。
- 建立本地联调脚本或说明，保证前端、后端、PostgreSQL、Redis、Broker 沙箱配置可重复启动。
- 明确日志字段：`request_id`、`user_id`、`broker_account_id`、`client_order_id`、`broker_order_id`，便于排查下单链路。

## 关键接口、模型与事件

### REST API

- `POST /api/v1/auth/login`
- `POST /api/v1/auth/refresh`
- `POST /api/v1/auth/logout`
- `GET /api/v1/auth/me`
- `GET /api/v1/accounts/broker-accounts`
- `GET /api/v1/accounts/overview`
- `GET /api/v1/accounts/positions`
- `GET /api/v1/orders`
- `POST /api/v1/orders`
- `POST /api/v1/orders/{client_order_id}/cancel`
- `GET /api/v1/orders/executions`
- `GET /api/v1/market-data/quote/{symbol}`

### WebSocket 事件

- `market.quote.<symbol>`：推送最新 bid、ask、last、timestamp。
- `orders.status.<account_id>`：推送订单状态变化、已成交数量、剩余数量、更新时间。
- `system.notifications.<user_id>`：本阶段只预留错误提示和系统广播，不承载运营通知。

### 核心数据模型

- `UserSession`：访问令牌、刷新令牌、过期时间、当前用户角色。
- `BrokerAccount`：账户标识、Broker 类型、环境、同步状态。
- `Order`：内部订单 ID、外部订单 ID、幂等键、状态、错误原因、审计字段。
- `Execution`：成交 ID、订单 ID、成交价格、数量、手续费、成交时间。
- `BrokerQuote`：symbol、bid、ask、last、timestamp、来源。

## 里程碑与依赖

### 里程碑 1：认证与会话

- 完成用户表、密码校验、JWT、刷新令牌、前端登录态恢复。
- 产出：真实登录闭环、路由守卫、`/auth/me` 可用。

### 里程碑 2：账户查询链路

- 完成 Broker 账户读取、账户总览、持仓、订单、成交查询。
- 产出：Dashboard 与 Trade 可复用的账户数据接口。

### 里程碑 3：交易写链路

- 完成下单、撤单、订单落库、幂等键、订单状态机和错误码。
- 产出：真实交易闭环、订单审计事件。

### 里程碑 4：实时状态同步

- 完成最小行情推送、订单状态推送、前端 WebSocket 接入与重连。
- 产出：Phase 2 风控告警与 Dashboard 实时卡片可复用的事件总线输入。

### 关键依赖

- 依赖 Phase 0 的目录骨架、环境配置、API 契约基线、数据库迁移框架。
- 依赖 Alpaca paper trading 账户与行情能力可在 test/local 环境访问。
- 风控预检查只保留接口预留，本阶段不阻塞下单链路。

## 验收与测试场景

### 测试矩阵

| 类型 | 必测内容 |
| --- | --- |
| 单元测试 | 密码校验、JWT 编解码、订单状态机迁移、幂等键判重、DTO 映射 |
| 集成测试 | 登录、刷新、账户总览查询、下单、撤单、订单列表、成交列表、Broker 适配层错误映射 |
| 联调 / E2E | 登录进入交易页、加载账户、提交订单、接收状态更新、撤单成功 |
| 人工验收 | 刷新页面后会话保持、网络抖动后 WebSocket 重连、失败下单提示准确 |

### 核心验收场景

1. 交易员输入正确账号密码登录后，前端获取 `/auth/me` 并进入交易页。
2. 页面加载账户总览、持仓、订单列表，且数据来自后端真实接口而非 `shared/mocks`。
3. 用户提交一笔限价单，系统写入内部订单、调用 Broker、返回 `PENDING_SUBMIT` 或 `SUBMITTED` 状态。
4. Broker 回报到达后，后端更新订单状态并经 WebSocket 推送给前端，页面状态同步变化。
5. 用户发起撤单，系统执行撤单并最终显示 `CANCELED` 或明确失败原因。

## 风险与回退方案

- Broker 沙箱不稳定或返回字段波动：通过 `BrokerAdapter` 做字段映射和容错，必要时增加轮询补偿。
- WebSocket 链路不稳定：保留主动刷新和短轮询兜底，避免前端只能依赖推送。
- 订单状态不一致：以内部订单表为系统事实源，Broker 状态作为外部同步输入，不允许前端直接信任第三方原始结构。
- 鉴权设计过轻导致后续返工：本阶段仅做最小 RBAC，但接口层必须保留可扩展的角色校验位置。
- 如真实 Broker 联调阻塞，可在 test 环境保留标准化 broker mock 适配器；但前端和应用服务层不得再直接读取 `shared/mocks` 作为业务事实。

## 交付清单

- 认证与会话真实实现文档和代码。
- 账户、持仓、订单、成交最小真实接口。
- `Trade` 页面真实数据接入与 WebSocket 订阅。
- 订单状态机、幂等机制、基础审计日志。
- Phase 1 联调说明、种子数据、测试用例。
