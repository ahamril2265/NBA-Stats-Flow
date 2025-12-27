import os
import pandas as pd
from datetime import datetime
import json
import yaml

from src.common.config_loader import load_config
from src.common.logger import get_logger
from src.alerts.alert_manager import emit_alert


logger = get_logger("SCHEMA_CHECK")

SILVER_BASE_PATH = "data/silver"
METRICS_BASE_PATH = "metrics/schema"
SCHEMA_REGISTRY_PATH = "schema_registry"

TYPE_MAPPING = {
    "integer": "int64",
    "string": "object",
    "date": "datetime64[ns]"
}


# ---------------- Schema Registry Utilities ---------------- #

def _load_schema(path: str) -> dict:
    with open(path, "r") as f:
        return yaml.safe_load(f)


def _latest_schema_path() -> str:
    if not os.path.exists(SCHEMA_REGISTRY_PATH):
        raise RuntimeError("Schema registry directory not found")

    versions = [
        f for f in os.listdir(SCHEMA_REGISTRY_PATH)
        if f.startswith("schema_v") and f.endswith(".yaml")
    ]
    if not versions:
        raise RuntimeError("No schema versions found in registry")

    versions.sort(key=lambda v: int(v.replace("schema_v", "").replace(".yaml", "")))
    return os.path.join(SCHEMA_REGISTRY_PATH, versions[-1])


def _next_schema_version(version: str) -> str:
    v = int(version.replace("v", ""))
    return f"v{v + 1}"


def _classify_schema_change(old: dict, new: dict):
    old_cols = {c["name"]: c for c in old["columns"]}
    new_cols = {c["name"]: c for c in new["columns"]}

    breaking = []
    compatible = []

    for name, old_col in old_cols.items():
        if name not in new_cols:
            breaking.append(f"Column removed: {name}")
        else:
            new_col = new_cols[name]
            if old_col["type"] != new_col["type"]:
                breaking.append(f"Type change: {name}")
            if old_col.get("nullable", True) and not new_col.get("nullable", True):
                breaking.append(f"Nullable → non-nullable: {name}")

    for name, new_col in new_cols.items():
        if name not in old_cols:
            if new_col.get("nullable", True):
                compatible.append(f"New nullable column: {name}")
            else:
                breaking.append(f"New non-nullable column: {name}")

    return breaking, compatible


def _persist_new_schema(schema: dict, new_version: str):
    path = os.path.join(SCHEMA_REGISTRY_PATH, f"schema_{new_version}.yaml")
    with open(path, "w") as f:
        yaml.safe_dump(schema, f)


# ---------------- Metrics ---------------- #

def _write_metrics(snapshot_date: str, metrics: dict):
    output_dir = f"{METRICS_BASE_PATH}/snapshot_date={snapshot_date}"
    os.makedirs(output_dir, exist_ok=True)

    output_path = f"{output_dir}/schema_metrics.json"
    with open(output_path, "a") as f:
        f.write(json.dumps(metrics) + "\n")


# ---------------- Main Enforcement ---------------- #

def enforce_schema(snapshot_date: str):
    config = load_config()
    incoming_schema = config["schema"]

    silver_parquet_path = (
        f"{SILVER_BASE_PATH}/snapshot_date={snapshot_date}/"
        "nba_player_stats_silver.parquet"
    )

    logger.info(f"START | Schema enforcement for snapshot {snapshot_date}")

    metrics = {
        "snapshot_date": snapshot_date,
        "schema_version": incoming_schema["version"],
        "checks_passed": 0,
        "checks_failed": 0,
        "status": "UNKNOWN",
        "timestamp": datetime.utcnow().isoformat()
    }

    try:
        # ---------- Phase 2.2: Schema Evolution Gate ---------- #

        latest_schema = _load_schema(_latest_schema_path())
        breaking, compatible = _classify_schema_change(
            latest_schema, incoming_schema
        )

        if breaking:
            logger.error("Breaking schema changes detected:")
            for issue in breaking:
                logger.error(f"- {issue}")

            emit_alert(
                severity="CRITICAL",
                source="SCHEMA_CHECK",
                snapshot_date=snapshot_date,
                message="Breaking schema change detected",
                details={"issues": breaking}
            )
            raise ValueError("Breaking schema changes detected")

        if compatible:
            new_version = _next_schema_version(latest_schema["version"])
            incoming_schema["version"] = new_version
            metrics["schema_version"] = new_version  # ✅ fix
            _persist_new_schema(incoming_schema, new_version)

            emit_alert(
                severity="INFO",
                source="SCHEMA_CHECK",
                snapshot_date=snapshot_date,
                message=f"New schema version registered: {new_version}"
            )

            logger.info(f"Registered new schema version: {new_version}")

        metrics["checks_passed"] += 1

        # ---------- Parquet Enforcement ---------- #

        if not os.path.exists(silver_parquet_path):
            raise FileNotFoundError("Missing silver Parquet data")

        df = pd.read_parquet(silver_parquet_path)

        expected_columns = [c["name"] for c in incoming_schema["columns"]]
        actual_columns = df.columns.tolist()

        missing = set(expected_columns) - set(actual_columns)
        if missing:
            raise ValueError(f"Missing required columns: {missing}")

        metrics["checks_passed"] += 1

        for col in incoming_schema["columns"]:
            col_name = col["name"]
            expected_type = TYPE_MAPPING[col["type"]]
            actual_type = str(df[col_name].dtype)

            if actual_type != expected_type:
                raise TypeError(
                    f"Type mismatch for {col_name}: {actual_type} != {expected_type}"
                )

        metrics["checks_passed"] += 1

        non_nullable = [
            c["name"] for c in incoming_schema["columns"]
            if not c.get("nullable", True)
        ]

        violated = df[non_nullable].isnull().any()
        if violated.any():
            raise ValueError(
                f"Nulls in non-nullable columns: {violated[violated].index.tolist()}"
            )

        metrics["checks_passed"] += 1

        metrics["status"] = "PASSED"
        _write_metrics(snapshot_date, metrics)

        logger.info("END | Schema enforcement passed successfully")

    except Exception as e:
        metrics["checks_failed"] += 1
        metrics["status"] = "FAILED"
        _write_metrics(snapshot_date, metrics)

        emit_alert(
            severity="CRITICAL",
            source="SCHEMA_CHECK",
            snapshot_date=snapshot_date,
            message="Schema enforcement failed (Parquet)",
            details={"error": str(e)}
        )
        raise


def main():
    snapshot_date = datetime.today().strftime("%Y-%m-%d")
    enforce_schema(snapshot_date)


if __name__ == "__main__":
    main()
