import os
import pandas as pd
from datetime import datetime
import json

from src.common.config_loader import load_config
from src.common.logger import get_logger

logger = get_logger("SCHEMA_CHECK")

SILVER_BASE_PATH = "data/silver"
METRICS_BASE_PATH = "metrics/schema"

TYPE_MAPPING = {
    "integer": "int64",
    "string": "object",
    "date": "datetime64[ns]"
}


def _write_metrics(snapshot_date: str, metrics: dict):
    output_dir = f"{METRICS_BASE_PATH}/snapshot_date={snapshot_date}"
    os.makedirs(output_dir, exist_ok=True)

    output_path = f"{output_dir}/schema_metrics.json"
    with open(output_path, "a") as f:
        f.write(json.dumps(metrics) + "\n")


def enforce_schema(snapshot_date: str):
    config = load_config()
    schema = config["schema"]

    silver_csv_path = (
        f"{SILVER_BASE_PATH}/snapshot_date={snapshot_date}/"
        "nba_player_stats_silver.csv"
    )

    logger.info(f"START | Schema enforcement for snapshot {snapshot_date}")

    metrics = {
        "snapshot_date": snapshot_date,
        "schema_version": schema["version"],
        "checks_passed": 0,
        "checks_failed": 0,
        "status": "UNKNOWN",
        "timestamp": datetime.utcnow().isoformat()
    }

    try:
        if not os.path.exists(silver_csv_path):
            logger.error(f"Silver file not found: {silver_csv_path}")
            raise FileNotFoundError("Missing silver data")

        df = pd.read_csv(silver_csv_path)

        # 1️⃣ Column presence check
        expected_columns = [col["name"] for col in schema["columns"]]
        actual_columns = df.columns.tolist()

        missing_cols = set(expected_columns) - set(actual_columns)
        if missing_cols:
            logger.error(f"Missing required columns: {missing_cols}")
            raise ValueError("Schema enforcement failed: missing columns")

        metrics["checks_passed"] += 1

        extra_cols = set(actual_columns) - set(expected_columns)
        if extra_cols:
            logger.warning(f"Extra columns detected (allowed in v1): {extra_cols}")

        # 2️⃣ Data type enforcement (CSV-aware)
        for col in schema["columns"]:
            col_name = col["name"]
            expected_type = col["type"]

            actual_dtype = str(df[col_name].dtype)

            try:
                if actual_dtype != "object":
                    # Parquet-like strict check (future-proof)
                    expected_pandas_type = TYPE_MAPPING[expected_type]
                    if actual_dtype != expected_pandas_type:
                        raise TypeError
                else:
                    # CSV → validate via cast
                    if expected_type == "integer":
                        df[col_name].astype(int)
                    elif expected_type == "date":
                        pd.to_datetime(df[col_name], errors="raise")
            except Exception:
                logger.error(
                    f"Column '{col_name}' cannot be cast to {expected_type}"
                )
                raise TypeError("Schema enforcement failed: type validation error")

        metrics["checks_passed"] += 1

        # 3️⃣ Nullability constraints
        non_nullable_cols = [
            col["name"]
            for col in schema["columns"]
            if not col.get("nullable", True)
        ]

        null_violations = df[non_nullable_cols].isnull().any()
        violated_cols = null_violations[null_violations].index.tolist()

        if violated_cols:
            logger.error(
                f"Non-nullable columns contain nulls: {violated_cols}"
            )
            raise ValueError("Schema enforcement failed: null constraint violation")

        metrics["checks_passed"] += 1

        # ✅ SUCCESS
        metrics["status"] = "PASSED"
        _write_metrics(snapshot_date, metrics)

        logger.info("END | Schema enforcement passed successfully")

    except Exception:
        # ❌ FAILURE
        metrics["checks_failed"] += 1
        metrics["status"] = "FAILED"
        _write_metrics(snapshot_date, metrics)
        raise


def main():
    snapshot_date = datetime.today().strftime("%Y-%m-%d")
    enforce_schema(snapshot_date)


if __name__ == "__main__":
    main()
