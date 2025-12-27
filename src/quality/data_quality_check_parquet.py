import os
import json
import pandas as pd
from datetime import datetime

from src.common.config_loader import load_config
from src.common.logger import get_logger
from src.alerts.alert_manager import emit_alert


logger = get_logger("DATA_QUALITY")

SILVER_BASE_PATH = "data/silver"
METRICS_BASE_PATH = "metrics/data_quality"


def _latest_metrics_path():
    if not os.path.exists(METRICS_BASE_PATH):
        return None

    snapshots = [
        d for d in os.listdir(METRICS_BASE_PATH)
        if d.startswith("snapshot_date=")
    ]

    if not snapshots:
        return None

    snapshots.sort()
    return os.path.join(
        METRICS_BASE_PATH,
        snapshots[-1],
        "quality_metrics.json"
    )


def _write_metrics(snapshot_date: str, metrics: dict):
    out_dir = f"{METRICS_BASE_PATH}/snapshot_date={snapshot_date}"
    os.makedirs(out_dir, exist_ok=True)

    path = f"{out_dir}/quality_metrics.json"
    with open(path, "a") as f:
        f.write(json.dumps(metrics) + "\n")


def check_data_quality(snapshot_date: str):
    config = load_config()
    dq_cfg = config["base"]["data_quality"]

    silver_path = (
        f"{SILVER_BASE_PATH}/snapshot_date={snapshot_date}/"
        "nba_player_stats_silver.parquet"
    )

    logger.info(f"START | Data quality check for {snapshot_date}")

    if not os.path.exists(silver_path):
        raise FileNotFoundError("Silver data not found")

    df = pd.read_parquet(silver_path)
    row_count = len(df)

    metrics = {
        "snapshot_date": snapshot_date,
        "row_count": row_count,
        "null_percentages": {},
        "status": "PASSED",
        "timestamp": datetime.utcnow().isoformat()
    }

    # ---------- Row Count Drift ---------- #
    previous_path = _latest_metrics_path()
    if previous_path:
        with open(previous_path) as f:
            lines = f.readlines()
            prev = json.loads(lines[-1])

        prev_count = prev["row_count"]
        pct_change = abs(row_count - prev_count) / prev_count * 100

        metrics["row_count_change_pct"] = round(pct_change, 2)

        if pct_change > dq_cfg["row_count_drift_pct"]:
            logger.warning(
                f"Row count drift detected: {pct_change:.2f}%"
            )
            metrics["status"] = "WARN"
            emit_alert(
                severity="WARN",
                source="DATA_QUALITY",
                snapshot_date=snapshot_date,
                message="Row count drift detected",
                details={
                    "row_count": row_count,
                    "pct_change": metrics.get("row_count_change_pct")
                }
            )



    # ---------- Null Percentage Drift ---------- #
    for col in dq_cfg["critical_columns"]:
        null_pct = df[col].isnull().mean() * 100
        metrics["null_percentages"][col] = round(null_pct, 2)

        if null_pct > dq_cfg["null_threshold_pct"]:
            logger.error(
                f"High null percentage in {col}: {null_pct:.2f}%"
            )
            metrics["status"] = "FAILED"
            emit_alert(
                severity="CRITICAL",
                source="DATA_QUALITY",
                snapshot_date=snapshot_date,
                message="Null percentage threshold exceeded",
                details=metrics["null_percentages"]
            )


    _write_metrics(snapshot_date, metrics)

    if metrics["status"] == "FAILED":
        raise ValueError("Data quality checks failed")

    logger.info(
        f"END | Data quality check completed with status {metrics['status']}"
    )


def main():
    snapshot_date = datetime.today().strftime("%Y-%m-%d")
    check_data_quality(snapshot_date)


if __name__ == "__main__":
    main()
