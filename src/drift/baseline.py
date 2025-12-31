import os
import json
from datetime import datetime, UTC
from collections import defaultdict
from statistics import mean, median

from src.common.config_loader import load_config
from src.common.logger import get_logger

logger = get_logger("DRIFT_BASELINE")

METRICS_BASE_PATH = "metrics/drift"
BASELINE_BASE_PATH = "metrics/drift/baseline"


# ---------------- Utilities ---------------- #

def _ensure_dir(path: str):
    os.makedirs(path, exist_ok=True)


def _load_profiling(snapshot_date: str) -> list[dict]:
    path = (
        f"{METRICS_BASE_PATH}/snapshot_date={snapshot_date}/"
        "profiling_metrics.json"
    )

    if not os.path.exists(path):
        raise FileNotFoundError(f"Profiling metrics missing for {snapshot_date}")

    records = []
    with open(path, "r") as f:
        for line in f:
            records.append(json.loads(line))

    return records


def _list_previous_snapshots(current_snapshot: str, window: int) -> list[str]:
    snapshots = []

    if not os.path.exists(METRICS_BASE_PATH):
        return snapshots

    for d in os.listdir(METRICS_BASE_PATH):
        if d.startswith("snapshot_date="):
            snap = d.replace("snapshot_date=", "")
            if snap < current_snapshot:
                snapshots.append(snap)

    snapshots.sort(reverse=True)
    return snapshots[:window]


# ---------------- Baseline Builders ---------------- #

def _build_numeric_baseline(records: list[dict]) -> dict:
    buckets = defaultdict(list)

    for r in records:
        for metric, value in r["metrics"].items():
            buckets[metric].append(value)

    return {
        "mean": mean(buckets["mean"]),
        "median": median(buckets["median"]),
        "std": mean(buckets["std"]),
        "min": min(buckets["min"]),
        "max": max(buckets["max"]),
        "p25": mean(buckets["p25"]),
        "p50": mean(buckets["p50"]),
        "p75": mean(buckets["p75"]),
    }


def _build_categorical_baseline(records: list[dict]) -> dict:
    cardinalities = []
    value_freq = defaultdict(list)

    for r in records:
        cardinalities.append(r["metrics"]["cardinality"])
        for val, cnt in r["metrics"]["top_5_values"].items():
            value_freq[val].append(cnt)

    return {
        "avg_cardinality": mean(cardinalities),
        "top_values": {
            val: mean(cnts) for val, cnts in value_freq.items()
        },
        "seen_values": list(value_freq.keys()),
    }


# ---------------- Main Entry ---------------- #

def build_baseline(snapshot_date: str):
    config = load_config()
    drift_cfg = config["base"]["drift_detection"]
    window = drift_cfg["baseline_window"]

    logger.info(
        f"START | Baseline build for snapshot {snapshot_date} "
        f"(window={window})"
    )

    previous_snapshots = _list_previous_snapshots(snapshot_date, window)

    if not previous_snapshots:
        logger.info("No historical snapshots available — bootstrap mode")
        return

    history = defaultdict(list)

    for snap in previous_snapshots:
        try:
            records = _load_profiling(snap)
            for r in records:
                key = (r["column"], r["type"])
                history[key].append(r)
        except Exception as e:
            logger.warning(f"Skipping snapshot {snap}: {e}")

    baseline_records = []
    timestamp = datetime.now(UTC).isoformat()

    for (column, col_type), records in history.items():
        if col_type == "numeric":
            baseline = _build_numeric_baseline(records)
        else:
            baseline = _build_categorical_baseline(records)

        baseline_records.append({
            "snapshot_date": snapshot_date,
            "layer": "silver",
            "column": column,
            "type": col_type,
            "baseline": baseline,
            "history_snapshots": len(records),
            "timestamp": timestamp,
        })

        logger.info(f"Baseline built for column: {column}")

    output_dir = f"{BASELINE_BASE_PATH}/snapshot_date={snapshot_date}"
    _ensure_dir(output_dir)

    output_path = f"{output_dir}/baseline_metrics.json"

    with open(output_path, "a") as f:
        for r in baseline_records:
            f.write(json.dumps(r) + "\n")

    logger.info(
        f"END | Baseline build completed "
        f"(columns={len(baseline_records)})"
    )


def main():
    snapshot_date = datetime.now().strftime("%Y-%m-%d")
    build_baseline(snapshot_date)


if __name__ == "__main__":
    main()
