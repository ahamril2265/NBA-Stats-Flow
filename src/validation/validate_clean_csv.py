import os
import pandas as pd
from datetime import datetime
from typing import List

from src.common.config_loader import load_config
from src.common.logger import get_logger

logger = get_logger("SILVER_VALIDATION")

BRONZE_BASE_PATH = "data/bronze"
SILVER_BASE_PATH = "data/silver"


def get_critical_columns(schema_config: dict) -> List[str]:
    return [
        col["name"]
        for col in schema_config["columns"]
        if not col.get("nullable", True)
    ]


def validate_and_clean(snapshot_date: str):
    config = load_config()
    schema = config["schema"]

    bronze_path = (
        f"{BRONZE_BASE_PATH}/snapshot_date={snapshot_date}/"
        "nba_player_stats_bronze.csv"
    )

    logger.info(f"START | Silver validation for snapshot {snapshot_date}")

    if not os.path.exists(bronze_path):
        logger.error(f"Bronze file not found: {bronze_path}")
        raise FileNotFoundError("Missing bronze data")

    df = pd.read_csv(bronze_path)
    rows_in = len(df)

    logger.info(f"Rows read from bronze: {rows_in}")

    # 1️⃣ Null validation
    critical_cols = get_critical_columns(schema)
    df = df.dropna(subset=critical_cols)
    rows_after_nulls = len(df)

    logger.info(
        f"Rows after null drop: {rows_after_nulls} "
        f"(dropped {rows_in - rows_after_nulls})"
    )

    # 2️⃣ Deduplication
    df = df.drop_duplicates(
        subset=["player_id", "season", "team", "snapshot_time_date"]
    )
    rows_after_dedup = len(df)

    logger.info(
        f"Rows after deduplication: {rows_after_dedup} "
        f"(dropped {rows_after_nulls - rows_after_dedup})"
    )

    # 3️⃣ Type enforcement (basic, explicit)
    df["player_id"] = df["player_id"].astype(int)
    df["points"] = df["points"].astype(int)
    df["assists"] = df["assists"].astype(int)
    df["rebounds"] = df["rebounds"].astype(int)
    # Enforce snapshot_time_date as datetime
    df["snapshot_time_date"] = pd.to_datetime(df["snapshot_time_date"],errors="raise")


    # 4️⃣ Write Silver
    output_dir = f"{SILVER_BASE_PATH}/snapshot_date={snapshot_date}"
    os.makedirs(output_dir, exist_ok=True)

    output_path = f"{output_dir}/nba_player_stats_silver.csv"

    df.to_csv(output_path, index=False)

    logger.info("END | Silver validation completed")
    logger.info(f"Final silver row count: {len(df)}")
    logger.info(f"Silver file path: {output_path}")


def main():
    snapshot_date = datetime.today().strftime("%Y-%m-%d")
    validate_and_clean(snapshot_date)


if __name__ == "__main__":
    main()
