import os
import pandas as pd
from datetime import datetime
from sqlalchemy import create_engine, text
from dotenv import load_dotenv
import os

load_dotenv()

from src.common.config_loader import load_config
from src.common.logger import get_logger

logger = get_logger("GOLD_LOADER")

SILVER_BASE_PATH = "data/silver"

def ensure_gold_table(conn):
    conn.execute(text("""
        CREATE SCHEMA IF NOT EXISTS analytics;

        CREATE TABLE IF NOT EXISTS analytics.nba_player_stats (
            player_id INT NOT NULL,
            player_name TEXT NOT NULL,
            team TEXT NOT NULL,
            season TEXT NOT NULL,
            points INT NOT NULL,
            assists INT NOT NULL,
            rebounds INT NOT NULL,
            snapshot_time_date DATE NOT NULL,
            ingested_at TIMESTAMP NOT NULL,
            schema_version TEXT NOT NULL
        );
    """))

def get_engine():
    user = os.getenv("POSTGRES_USER")
    password = os.getenv("POSTGRES_PASSWORD")
    host = os.getenv("POSTGRES_HOST")
    port = os.getenv("POSTGRES_PORT")
    database = os.getenv("POSTGRES_DB")

    missing = [k for k, v in {
        "POSTGRES_USER": user,
        "POSTGRES_PASSWORD": password,
        "POSTGRES_HOST": host,
        "POSTGRES_PORT": port,
        "POSTGRES_DB": database,
    }.items() if v is None]

    if missing:
        raise EnvironmentError(f"Missing DB environment variables: {missing}")

    return create_engine(
        f"postgresql://{user}:{password}@{host}:{port}/{database}"
    )



def load_to_postgres(snapshot_date: str):
    config = load_config()
    schema_cfg = config["schema"]
    db_cfg = config["base"]["database"]

    silver_path = (
        f"{SILVER_BASE_PATH}/snapshot_date={snapshot_date}/"
        "nba_player_stats_silver.parquet"
    )

    logger.info(f"START | Gold load for snapshot {snapshot_date}")

    if not os.path.exists(silver_path):
        logger.error(f"Silver file not found: {silver_path}")
        raise FileNotFoundError("Missing silver data")

    df = pd.read_parquet(silver_path)
    rows_to_load = len(df)

    logger.info(f"Rows read from silver: {rows_to_load}")

    # Add schema version for lineage
    df["schema_version"] = schema_cfg["version"]

    engine = get_engine()

    with engine.begin() as conn:
        logger.info("Ensuring Gold table exists")
        ensure_gold_table(conn)

        logger.info("Truncating target table for idempotent load")
        conn.execute(text("TRUNCATE TABLE analytics.nba_player_stats"))


        df.to_sql(
            name="nba_player_stats",
            schema="analytics",
            con=conn,
            if_exists="append",
            index=False,
            method="multi",
            chunksize=10_000
        )

        result = conn.execute(
            text("SELECT COUNT(*) FROM analytics.nba_player_stats")
        )
        rows_loaded = result.scalar()

    logger.info("END | Gold load completed")
    logger.info(f"Rows loaded into Gold: {rows_loaded}")

    if rows_loaded != rows_to_load:
        logger.error(
            f"Row count mismatch: silver={rows_to_load}, gold={rows_loaded}"
        )
        raise ValueError("Gold load row count mismatch")


def main():
    snapshot_date = datetime.today().strftime("%Y-%m-%d")
    load_to_postgres(snapshot_date)


if __name__ == "__main__":
    main()
