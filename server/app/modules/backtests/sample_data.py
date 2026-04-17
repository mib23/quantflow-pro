from __future__ import annotations

from copy import deepcopy


_SAMPLE_BACKTESTS: dict[str, dict[str, object]] = {
    "demo-momentum": {
        "title": "Backtest Report",
        "description": "Deterministic sample output for the strategy lab worker.",
        "metrics": {
            "total_return": 0.126,
            "sharpe": 1.42,
            "max_drawdown": -0.08,
            "win_rate": 0.58,
            "trade_count": 12,
        },
        "equity_curve": [
            {"time": "2024-01-02", "equity": 100000},
            {"time": "2024-02-01", "equity": 104800},
            {"time": "2024-03-29", "equity": 112600},
        ],
        "trades": [
            {"symbol": "AAPL", "side": "BUY", "quantity": 100, "pnl": 820.0},
            {"symbol": "MSFT", "side": "BUY", "quantity": 50, "pnl": 510.0},
            {"symbol": "AAPL", "side": "SELL", "quantity": 100, "pnl": 1260.0},
        ],
    }
}


def load_sample_backtest(dataset_key: str) -> dict[str, object]:
    try:
        return deepcopy(_SAMPLE_BACKTESTS[dataset_key])
    except KeyError as exc:  # pragma: no cover - defensive guard for future datasets
        raise ValueError(f"Unknown sample backtest dataset: {dataset_key}") from exc
