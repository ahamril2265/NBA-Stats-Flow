import os
import json
from datetime import datetime, UTC

from src.common.config_loader import load_config
from src.common.logger import get_logger
from src.alerts.alert_manager import emit_alert

logger = get_logger("DRIFT_DETECTOR")

METRICS_BASE_PATH = "metrics/drift"
BASELINE_BASE_PATH = "metrics/drift/baseline"


# ---------------- Utilities ---------------- #

def _load_jsonl(path: str) -> list[dict]:
    records = []
    with open(path, "r") as f:
        for line in f:
            records.append(json.loads(line))
    return records


def _write_metrics(snapshot_date: str, records: list[dict]):
    out_dir = f"{METRICS_BASE_PATH}/snapshot_date={snapshot_date}"
    os.makedirs(out_dir, exist_ok=True)

    out_path = f"{out_dir}/drift_metrics.json"
    with open(out_path, "a") as f:
        for r in records:
            f.write(json.dumps(r) + "\n")


def _pct_drift(current: float, baseline: float) -> float:
    if baseline == 0:
        return 0.0
    return abs(current - baseline) / baseline * 100.0


# ---------------- Detection Logic ---------------- #

def _classify_numeric(drift_pct: float, thresholds: dict) -> str:
    if drift_pct >= thresholds["warn_pct"]:
        return "CRITICAL"
    if drift_pct >= thresholds["info_pct"]:
        return "WARN"
    return "INFO"


def _classify_categorical(drift_pct: float, thresholds: dict) -> str:
    if drift_pct >= thresholds["cardinality_critical_pct"]:
        return "CRITICAL"
    if drift_pct >= thresholds["cardinality_warn_pct"]:
        return "WARN"
    return "INFO"


# ---------------- Main Entry ---------------- #

def run_drift_detection(snapshot_date: str):
    config = load_config()
    drift_cfg = config["base"]["drift_detection"]

    profiling_path = (
        f"{METRICS_BASE_PATH}/snapshot_date={snapshot_date}/"
        "profiling_metrics.json"
    )

    baseline_path = (
        f"{BASELINE_BASE_PATH}/snapshot_date={snapshot_date}/"
        "baseline_metrics.json"
    )

    logger.info(f"START | Drift detection for snapshot {snapshot_date}")

    if not os.path.exists(profiling_path):
        raise FileNotFoundError("Profiling metrics missing")

    if not os.path.exists(baseline_path):
        logger.info("Baseline not available — bootstrap mode")
        return

    profiling = _load_jsonl(profiling_path)
    baselines = _load_jsonl(baseline_path)

    baseline_index = {
        (b["column"], b["type"]): b for b in baselines
    }

    drift_records = []
    critical_detected = False
    timestamp = datetime.now(UTC).isoformat()

    for record in profiling:
        key = (record["column"], record["type"])

        if key not in baseline_index:
            continue

        baseline = baseline_index[key]["baseline"]

        # -------- Numeric Drift -------- #
        if record["type"] == "numeric":
            for metric, current_val in record["metrics"].items():
                baseline_val = baseline.get(metric)
                if baseline_val is None:
                    continue

                drift_pct = _pct_drift(current_val, baseline_val)
                severity = _classify_numeric(
                    drift_pct, drift_cfg["thresholds"]["numeric"]
                )

                drift_records.append({
                    "snapshot_date": snapshot_date,
                    "layer": "silver",
                    "column": record["column"],
                    "metric": metric,
                    "baseline": baseline_val,
                    "current": current_val,
                    "drift_pct": round(drift_pct, 2),
                    "severity": severity,
                    "timestamp": timestamp,
                })

                if severity in ("WARN", "CRITICAL"):
                    emit_alert(
                        severity=severity,
                        source="DRIFT_DETECTOR",
                        snapshot_date=snapshot_date,
                        message=f"Numeric drift detected: {record['column']}:{metric}",
                        details={
                            "baseline": baseline_val,
                            "current": current_val,
                            "drift_pct": drift_pct,
                        },
                    )

                if severity == "CRITICAL":
                    critical_detected = True

        # -------- Categorical Drift -------- #
        else:
            curr_card = record["metrics"]["cardinality"]
            base_card = baseline["avg_cardinality"]

            drift_pct = _pct_drift(curr_card, base_card)
            severity = _classify_categorical(
                drift_pct, drift_cfg["thresholds"]["categorical"]
            )

            drift_records.append({
                "snapshot_date": snapshot_date,
                "layer": "silver",
                "column": record["column"],
                "metric": "cardinality",
                "baseline": base_card,
                "current": curr_card,
                "drift_pct": round(drift_pct, 2),
                "severity": severity,
                "timestamp": timestamp,
            })

            if severity in ("WARN", "CRITICAL"):
                emit_alert(
                    severity=severity,
                    source="DRIFT_DETECTOR",
                    snapshot_date=snapshot_date,
                    message=f"Categorical drift detected: {record['column']}",
                    details={
                        "baseline": base_card,
                        "current": curr_card,
                        "drift_pct": drift_pct,
                    },
                )

            if severity == "CRITICAL":
                critical_detected = True

    _write_metrics(snapshot_date, drift_records)

    if critical_detected:
        raise RuntimeError("CRITICAL drift detected — pipeline aborted")

    logger.info(
        f"END | Drift detection completed "
        f"(records={len(drift_records)})"
    )


def main():
    snapshot_date = datetime.now().strftime("%Y-%m-%d")
    run_drift_detection(snapshot_date)


if __name__ == "__main__":
    main()
