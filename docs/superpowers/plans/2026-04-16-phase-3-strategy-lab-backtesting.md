# Phase 3 Strategy Lab Backtesting Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Deliver a working Strategy Lab where users can manage strategies and versions, submit asynchronous backtests, and inspect normalized results and downloadable reports.

**Architecture:** Add a dedicated `strategies` backend module for strategy/version metadata, a `backtests` backend module for job orchestration and results, and an RQ-backed worker task that writes normalized job logs and reports. On the frontend, replace the placeholder Strategy page with a research workspace that only consumes stable DTOs and polls backtest job state.

**Tech Stack:** React 19 + React Query + TypeScript + Recharts, FastAPI + SQLAlchemy + Alembic + RQ + pytest, SQLite-backed tests with sample backtest data.

---

### Task 1: Backend strategy and backtest API foundation

**Files:**
- Modify: `server/app/core/models.py`
- Modify: `server/app/api/router.py`
- Create: `server/app/modules/strategies/__init__.py`
- Create: `server/app/modules/strategies/router.py`
- Create: `server/app/modules/strategies/schemas.py`
- Create: `server/app/modules/strategies/repository.py`
- Create: `server/app/modules/strategies/service.py`
- Create: `server/app/modules/backtests/__init__.py`
- Create: `server/app/modules/backtests/router.py`
- Create: `server/app/modules/backtests/schemas.py`
- Create: `server/app/modules/backtests/repository.py`
- Create: `server/app/modules/backtests/service.py`
- Create: `server/app/tests/test_strategy_backtests_api.py`
- Create: `server/migrations/versions/20260416_0003_phase3_strategy_backtests.py`

- [ ] **Step 1: Write failing API tests for strategy/version/job CRUD**

```python
def test_strategy_and_backtest_api_end_to_end() -> None:
    response = client.post("/api/v1/strategies", json={"name": "Momentum Pulse"})
    assert response.status_code == 200
    strategy_id = response.json()["data"]["id"]

    version_response = client.post(
        f"/api/v1/strategies/{strategy_id}/versions",
        json={"version_note": "Initial draft", "code": "def run(): pass", "parameters": {"lookback": 20}},
    )
    assert version_response.status_code == 200

    job_response = client.post(
        "/api/v1/backtests",
        json={
            "strategy_version_id": version_response.json()["data"]["id"],
            "symbols": ["AAPL"],
            "time_range": {"start": "2024-01-01", "end": "2024-03-31"},
            "baseline": "SPY",
        },
    )
    assert job_response.status_code == 200
    assert job_response.json()["data"]["status"] == "QUEUED"
```

- [ ] **Step 2: Run targeted backend tests and verify the new tests fail for missing routes/models**

Run: `& 'D:\Project\test\quantflow-pro\server\.venv\Scripts\pytest.exe' app/tests/test_strategy_backtests_api.py -q`
Expected: FAIL with missing modules, tables, or route registration errors.

- [ ] **Step 3: Implement normalized models, schemas, repository methods, and API routes**

```python
class StrategyModel(Base):
    __tablename__ = "strategies"
    id: Mapped[str] = mapped_column(GUID(), primary_key=True, default=lambda: str(uuid.uuid4()))
    owner_user_id: Mapped[str] = mapped_column(GUID(), ForeignKey("users.id"), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="ACTIVE", server_default="ACTIVE")
    default_parameters: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict, server_default="{}")
    latest_version_id: Mapped[str | None] = mapped_column(GUID(), nullable=True)
```

- [ ] **Step 4: Add migration for strategy, version, job, result, and log tables**

```python
op.create_table(
    "backtest_jobs",
    sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
    sa.Column("strategy_version_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("strategy_versions.id"), nullable=False),
    sa.Column("submitted_by", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=False),
    sa.Column("status", sa.String(length=32), nullable=False),
    sa.Column("queue_job_id", sa.String(length=64), nullable=True),
    sa.Column("parameters_snapshot", sa.JSON(), nullable=False),
    sa.Column("dataset_key", sa.String(length=128), nullable=False),
)
```

- [ ] **Step 5: Run backend tests to verify API foundation passes**

Run: `& 'D:\Project\test\quantflow-pro\server\.venv\Scripts\pytest.exe' app/tests/test_strategy_backtests_api.py -q`
Expected: PASS

### Task 2: Worker execution, reports, retry/cancel semantics, and result persistence

**Files:**
- Modify: `server/app/workers/queue.py`
- Modify: `server/app/workers/worker.py`
- Modify: `server/app/modules/backtests/service.py`
- Create: `server/app/modules/backtests/executor.py`
- Create: `server/app/modules/backtests/reporting.py`
- Create: `server/app/modules/backtests/sample_data.py`
- Create: `server/app/tests/test_backtest_worker.py`

- [ ] **Step 1: Write failing worker tests covering execute/cancel/retry/report generation**

```python
def test_execute_backtest_job_writes_result_and_report(tmp_path) -> None:
    job_id = seed_backtest_job(status="QUEUED")
    result = execute_backtest_job(job_id=job_id, database_url=db_url)

    assert result["status"] == "SUCCEEDED"
    saved = repository.get_result(job_id)
    assert saved.metrics.total_return == 0.126
    assert saved.report_path.endswith(".json")
```

- [ ] **Step 2: Run worker tests and verify they fail before implementation**

Run: `& 'D:\Project\test\quantflow-pro\server\.venv\Scripts\pytest.exe' app/tests/test_backtest_worker.py -q`
Expected: FAIL because executor/reporting code does not exist yet.

- [ ] **Step 3: Implement sample-data-backed backtest execution and idempotent result writing**

```python
def execute_backtest_job(*, job_id: str, database_url: str | None = None) -> dict[str, object]:
    session_factory = build_session_factory(database_url)
    repository = BacktestRepository(session_factory)
    job = repository.require_job(job_id)
    repository.mark_job_running(job_id)
    sample = load_sample_backtest(job.dataset_key)
    result = build_backtest_result(job=job, sample=sample)
    repository.save_result_if_absent(job_id=job_id, result=result)
    repository.mark_job_succeeded(job_id, report_path=result["report_path"])
    return {"job_id": job_id, "status": "SUCCEEDED"}
```

- [ ] **Step 4: Wire RQ enqueue/cancel/retry helpers and structured log writes**

```python
queue = get_queue("backtests")
rq_job = queue.enqueue("app.modules.backtests.executor.execute_backtest_job", job_id=job.id)
repository.attach_queue_job(job.id, rq_job.get_id())
repository.append_log(job.id, level="INFO", code="JOB_ENQUEUED", message="Backtest queued.")
```

- [ ] **Step 5: Run worker tests to verify execution flow now passes**

Run: `& 'D:\Project\test\quantflow-pro\server\.venv\Scripts\pytest.exe' app/tests/test_backtest_worker.py -q`
Expected: PASS

### Task 3: Strategy Lab frontend workspace and polling result views

**Files:**
- Modify: `src/shared/types/domain.ts`
- Create: `src/features/strategy/api/strategyLabApi.ts`
- Create: `src/features/strategy/hooks/strategyLabQueryKeys.ts`
- Create: `src/features/strategy/hooks/useStrategyLab.ts`
- Modify: `src/features/strategy/pages/StrategyPage.tsx`
- Create: `src/features/strategy/components/StrategyListPanel.tsx`
- Create: `src/features/strategy/components/StrategyVersionPanel.tsx`
- Create: `src/features/strategy/components/BacktestJobsPanel.tsx`
- Create: `src/features/strategy/components/BacktestResultPanel.tsx`

- [ ] **Step 1: Write failing frontend type-level integration by referencing missing Strategy Lab DTOs**

```ts
const workspace = await getStrategyLabWorkspace();
expect(workspace.strategies[0].versions[0].versionTag).toBe("v1");
expect(workspace.selectedJob?.result?.metrics.totalReturn).toBeGreaterThan(0);
```

- [ ] **Step 2: Run frontend type-check and verify it fails until the new DTOs and page are implemented**

Run: `npm run check`
Expected: FAIL with missing strategy lab types/functions/components.

- [ ] **Step 3: Implement API client and polling hook over stable backend DTOs**

```ts
export function useBacktestJob(jobId: string | null) {
  return useQuery({
    queryKey: [...strategyLabQueryKeys.jobs, jobId],
    queryFn: () => getBacktestJob(jobId!),
    enabled: Boolean(jobId),
    refetchInterval: (query) => {
      const status = query.state.data?.status;
      return status === "QUEUED" || status === "RUNNING" ? 3000 : false;
    },
  });
}
```

- [ ] **Step 4: Replace the placeholder Strategy page with a usable workspace**

```tsx
<div className="grid gap-6 xl:grid-cols-[320px_360px_minmax(0,1fr)]">
  <StrategyListPanel ... />
  <StrategyVersionPanel ... />
  <BacktestResultPanel ... />
</div>
```

- [ ] **Step 5: Run frontend type-check and build to verify the workspace compiles**

Run: `npm run check`
Expected: PASS

### Task 4: Final integration verification

**Files:**
- Verify only

- [ ] **Step 1: Run the focused backend strategy/backtest test suite**

Run: `& 'D:\Project\test\quantflow-pro\server\.venv\Scripts\pytest.exe' app/tests/test_strategy_backtests_api.py app/tests/test_backtest_worker.py -q`
Expected: PASS

- [ ] **Step 2: Run the full backend test suite**

Run: `& 'D:\Project\test\quantflow-pro\server\.venv\Scripts\pytest.exe'`
Expected: PASS

- [ ] **Step 3: Run frontend type-check**

Run: `npm run check`
Expected: PASS

- [ ] **Step 4: Run frontend production build**

Run: `npm run build`
Expected: PASS
