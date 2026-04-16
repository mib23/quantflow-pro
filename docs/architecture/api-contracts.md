# 一期 API 与事件契约

## 通用约定

- Base URL：`/api/v1`
- 鉴权：`Authorization: Bearer <access_token>`
- 时间字段：统一 ISO 8601 UTC 字符串
- 金额字段：后端返回字符串或数字时都按十进制金额语义处理，一期前端统一格式化为美元
- 分页格式：

```json
{
  "items": [],
  "page": 1,
  "page_size": 20,
  "total": 0
}
```

- 响应外壳：

```json
{
  "data": {},
  "meta": {
    "request_id": "req_123"
  },
  "error": null
}
```

## REST API 清单

### 认证

- `POST /auth/login`
- `POST /auth/refresh`
- `POST /auth/logout`
- `GET /auth/me`

### 账户

- `GET /accounts/overview`
- `GET /accounts/positions`
- `GET /accounts/broker-accounts`

### 市场数据

- `GET /market-data/quote/{symbol}`
- `GET /market-data/watchlist`

### 订单与成交

- `GET /orders`
- `POST /orders`
- `POST /orders/{client_order_id}/cancel`
- `GET /orders/executions`

### 风控

- `GET /risk/summary`
- `GET /risk/rules`
- `GET /risk/events`
- `POST /risk/checks/pre-trade`

## 下单契约

### 请求体

```json
{
  "broker_account_id": "acc_paper_001",
  "symbol": "AAPL",
  "side": "BUY",
  "order_type": "LIMIT",
  "quantity": 100,
  "limit_price": 189.25,
  "time_in_force": "day",
  "idempotency_key": "place-order-20260414-001"
}
```

### 响应体

```json
{
  "data": {
    "client_order_id": "ord_20260414_001",
    "broker_order_id": null,
    "status": "PENDING_SUBMIT",
    "risk_check": {
      "passed": true,
      "events": []
    }
  },
  "meta": {
    "request_id": "req_123"
  },
  "error": null
}
```

## WebSocket 事件清单

WebSocket 根路径：`/ws`

### 频道

- `market.quote.<symbol>`
- `orders.status.<account_id>`
- `risk.events.<account_id>`
- `system.notifications.<user_id>`

### 事件载荷

#### 行情推送

```json
{
  "channel": "market.quote.AAPL",
  "event": "quote.updated",
  "payload": {
    "symbol": "AAPL",
    "bid": 189.2,
    "ask": 189.25,
    "last": 189.23,
    "timestamp": "2026-04-14T07:32:00Z"
  }
}
```

#### 订单状态变更

```json
{
  "channel": "orders.status.acc_paper_001",
  "event": "order.status_changed",
  "payload": {
    "client_order_id": "ord_20260414_001",
    "status": "PARTIALLY_FILLED",
    "filled_quantity": 50,
    "remaining_quantity": 50,
    "updated_at": "2026-04-14T07:32:02Z"
  }
}
```

#### 风险事件

```json
{
  "channel": "risk.events.acc_paper_001",
  "event": "risk.rule_triggered",
  "payload": {
    "rule_id": "rr_001",
    "severity": "HIGH",
    "message": "Order notional exceeds account threshold.",
    "occurred_at": "2026-04-14T07:32:03Z"
  }
}
```

## 错误码

| 错误码 | 含义 |
| --- | --- |
| `AUTH_INVALID_CREDENTIALS` | 用户名或密码错误 |
| `AUTH_TOKEN_EXPIRED` | 登录态过期 |
| `ORDER_RISK_REJECTED` | 风控拒单 |
| `ORDER_DUPLICATE_IDEMPOTENCY_KEY` | 幂等键重复 |
| `BROKER_UPSTREAM_ERROR` | Broker 返回不可恢复错误 |
| `INTERNAL_UNEXPECTED_ERROR` | 服务内部异常 |
