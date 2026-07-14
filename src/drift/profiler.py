import os
import json
import pandas as pd
from datetime import datetime, UTC
from typing import Dict, Any

from src.common.config_loader import load_config
from src.common.logger import get_logger

logger = get_logger("DRIFT_PROFILER")

SILVER_BASE_PATH = "data/silver"
METRICS_BASE_PATH = "metrics/drift"


# ---------------- Utilities ---------------- #

def _ensure_dir(path: str):
    os.makedirs(path, exist_ok=True)


def _write_metrics(snapshot_date: str, records: list[dict]):
    """
    Append-only write of drift profiling metrics
    """
    output_dir = f"{METRICS_BASE_PATH}/snapshot_date={snapshot_date}"
    _ensure_dir(output_dir)

    output_path = f"{output_dir}/profiling_metrics.json"

    with open(output_path, "a") as f:
        for record in records:
            f.write(json.dumps(record) + "\n")


# ---------------- Profilers ---------------- #

def _profile_numeric(df: pd.DataFrame, column: str) -> Dict[str, Any]:
    series = df[column].dropna()

    return {
        "count": int(series.count()),
        "mean": float(series.mean()),
        "median": float(series.median()),
        "std": float(series.std(ddof=0)) if series.count() > 1 else 0.0,
        "min": float(series.min()),
        "max": float(series.max()),
        "p25": float(series.quantile(0.25)),
        "p50": float(series.quantile(0.50)),
        "p75": float(series.quantile(0.75)),
    }


def _profile_categorical(df: pd.DataFrame, column: str) -> Dict[str, Any]:
    series = df[column].dropna()

    value_counts = series.value_counts()

    top_5 = (
        value_counts.head(5)
        .to_dict()
    )

    return {
        "count": int(series.count()),
        "cardinality": int(series.nunique()),
        "top_5_values": top_5,
    }


# ---------------- Main Entry ---------------- #

def run_profiling(snapshot_date: str):
    config = load_config()

    drift_cfg = config["base"]["drift_detection"]

    silver_path = (
        f"{SILVER_BASE_PATH}/snapshot_date={snapshot_date}/"
        "nba_player_stats_silver.parquet"
    )

    logger.info(f"START | Drift profiling for snapshot {snapshot_date}")

    if not os.path.exists(silver_path):
        raise FileNotFoundError(
            f"Silver data not found for snapshot {snapshot_date}"
        )

    df = pd.read_parquet(silver_path)

    profiling_records: list[dict] = []

    timestamp = datetime.now(UTC).isoformat()

    # -------- Numeric Profiling -------- #

    for col in drift_cfg["numeric_columns"]:
        if col not in df.columns:
            logger.warning(f"Numeric column missing in Silver: {col}")
            continue

        stats = _profile_numeric(df, col)

        profiling_records.append({
            "snapshot_date": snapshot_date,
            "layer": "silver",
            "column": col,
            "type": "numeric",
            "metrics": stats,
            "timestamp": timestamp,
        })

        logger.info(f"Profiled numeric column: {col}")

    # -------- Categorical Profiling -------- #

    for col in drift_cfg["categorical_columns"]:
        if col not in df.columns:
            logger.warning(f"Categorical column missing in Silver: {col}")
            continue

        stats = _profile_categorical(df, col)

        profiling_records.append({
            "snapshot_date": snapshot_date,
            "layer": "silver",
            "column": col,
            "type": "categorical",
            "metrics": stats,
            "timestamp": timestamp,
        })

        logger.info(f"Profiled categorical column: {col}")

    # -------- Persist -------- #

    _write_metrics(snapshot_date, profiling_records)

    logger.info(
        f"END | Drift profiling completed "
        f"(records_written={len(profiling_records)})"
    )


def main():
    snapshot_date = datetime.now().strftime("%Y-%m-%d")
    run_profiling(snapshot_date)


if __name__ == "__main__":
    main()
