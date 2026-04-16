# 一期 ER 图

```mermaid
erDiagram
    USERS ||--o{ BROKER_ACCOUNTS : owns
    USERS ||--o{ AUDIT_LOGS : creates
    BROKER_ACCOUNTS ||--o{ ACCOUNT_BALANCES : snapshots
    BROKER_ACCOUNTS ||--o{ POSITIONS : holds
    BROKER_ACCOUNTS ||--o{ ORDERS : places
    ORDERS ||--o{ EXECUTIONS : fills
    RISK_RULES ||--o{ RISK_EVENTS : triggers
    ORDERS ||--o{ RISK_EVENTS : blocked_or_flagged
    USERS ||--o{ RISK_RULES : manages

    USERS {
        uuid id PK
        string email UK
        string full_name
        string password_hash
        string role
        string status
        timestamptz created_at
        timestamptz updated_at
    }

    BROKER_ACCOUNTS {
        uuid id PK
        uuid user_id FK
        string broker_name
        string broker_account_no UK
        string external_account_id UK
        string environment
        string status
        timestamptz created_at
        timestamptz updated_at
    }

    ACCOUNT_BALANCES {
        uuid id PK
        uuid broker_account_id FK
        numeric equity
        numeric cash
        numeric buying_power
        numeric day_pnl
        timestamptz snapshot_at
    }

    POSITIONS {
        uuid id PK
        uuid broker_account_id FK
        string symbol
        numeric quantity
        numeric avg_price
        numeric market_price
        numeric market_value
        numeric unrealized_pnl
        timestamptz snapshot_at
    }

    ORDERS {
        uuid id PK
        uuid broker_account_id FK
        string client_order_id UK
        string broker_order_id UK
        string symbol
        string side
        string order_type
        numeric quantity
        numeric limit_price
        string status
        string time_in_force
        string idempotency_key UK
        timestamptz submitted_at
        timestamptz updated_at
    }

    EXECUTIONS {
        uuid id PK
        uuid order_id FK
        string broker_execution_id UK
        numeric filled_quantity
        numeric filled_price
        numeric fee_amount
        timestamptz executed_at
    }

    RISK_RULES {
        uuid id PK
        uuid created_by FK
        string scope
        string rule_type
        jsonb config
        boolean enabled
        integer version
        timestamptz created_at
        timestamptz updated_at
    }

    RISK_EVENTS {
        uuid id PK
        uuid risk_rule_id FK
        uuid order_id FK
        string severity
        string event_type
        jsonb payload
        timestamptz occurred_at
    }

    AUDIT_LOGS {
        uuid id PK
        uuid user_id FK
        string resource_type
        string resource_id
        string action
        jsonb before_state
        jsonb after_state
        timestamptz created_at
    }
```

## 约束与索引

- `users.email` 唯一。
- `broker_accounts.external_account_id` 唯一。
- `orders.client_order_id` 与 `orders.idempotency_key` 唯一。
- `positions` 建议唯一键：`(broker_account_id, symbol, snapshot_at)`。
- 高频查询索引：
  - `orders(broker_account_id, status, submitted_at desc)`
  - `executions(order_id, executed_at desc)`
  - `risk_events(occurred_at desc, severity)`
  - `audit_logs(resource_type, resource_id, created_at desc)`
