import os
import pandas as pd
from datetime import datetime
from sqlalchemy import create_engine, text
from dotenv import load_dotenv
import yaml

load_dotenv()

from src.common.config_loader import load_config
from src.common.logger import get_logger
from src.alerts.alert_manager import emit_alert


logger = get_logger("GOLD_LOADER")

SILVER_BASE_PATH = "data/silver"
SCHEMA_REGISTRY_PATH = "schema_registry"


def ensure_gold_tables(conn):
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
            schema_version TEXT NOT NULL,
            PRIMARY KEY (player_id, season, snapshot_time_date)
        );

        CREATE TABLE IF NOT EXISTS analytics.processed_snapshots (
            snapshot_date DATE PRIMARY KEY,
            processed_at TIMESTAMP NOT NULL
        );
    """))


def _latest_schema_version() -> str:
    if not os.path.exists(SCHEMA_REGISTRY_PATH):
        raise RuntimeError("Schema registry directory not found")

    versions = [
        f for f in os.listdir(SCHEMA_REGISTRY_PATH)
        if f.startswith("schema_v") and f.endswith(".yaml")
    ]
    if not versions:
        raise RuntimeError("No schema versions found in registry")

    versions.sort(key=lambda v: int(v.replace("schema_v", "").replace(".yaml", "")))
    latest = versions[-1]

    with open(os.path.join(SCHEMA_REGISTRY_PATH, latest)) as f:
        schema = yaml.safe_load(f)

    return schema["version"]


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


def snapshot_already_processed(conn, snapshot_date: str) -> bool:
    result = conn.execute(
        text("""
            SELECT 1
            FROM analytics.processed_snapshots
            WHERE snapshot_date = :snapshot_date
        """),
        {"snapshot_date": snapshot_date}
    ).fetchone()

    return result is not None


def mark_snapshot_processed(conn, snapshot_date: str):
    conn.execute(
        text("""
            INSERT INTO analytics.processed_snapshots (snapshot_date, processed_at)
            VALUES (:snapshot_date, :processed_at)
        """),
        {
            "snapshot_date": snapshot_date,
            "processed_at": datetime.utcnow()
        }
    )


def load_to_postgres(snapshot_date: str):
    silver_path = (
        f"{SILVER_BASE_PATH}/snapshot_date={snapshot_date}/"
        "nba_player_stats_silver.parquet"
    )

    logger.info(f"START | Incremental Gold load for snapshot {snapshot_date}")

    try:
        if not os.path.exists(silver_path):
            raise FileNotFoundError(
                f"Silver data not found for snapshot {snapshot_date}"
            )

        df = pd.read_parquet(silver_path)
        rows_read = len(df)

        logger.info(f"Rows read from silver: {rows_read}")

        if rows_read == 0:
            emit_alert(
                severity="WARN",
                source="GOLD_LOADER",
                snapshot_date=snapshot_date,
                message="Silver dataset is empty — no rows loaded"
            )
            return

        schema_version = _latest_schema_version()
        df["schema_version"] = schema_version

        engine = get_engine()

        with engine.begin() as conn:
            logger.info("Ensuring Gold tables exist")
            ensure_gold_tables(conn)

            if snapshot_already_processed(conn, snapshot_date):
                emit_alert(
                    severity="INFO",
                    source="GOLD_LOADER",
                    snapshot_date=snapshot_date,
                    message="Snapshot already processed — skipping Gold load"
                )
                return

            upsert_sql = """
                INSERT INTO analytics.nba_player_stats (
                    player_id, player_name, team, season,
                    points, assists, rebounds,
                    snapshot_time_date, ingested_at, schema_version
                )
                VALUES (
                    :player_id, :player_name, :team, :season,
                    :points, :assists, :rebounds,
                    :snapshot_time_date, :ingested_at, :schema_version
                )
                ON CONFLICT (player_id, season, snapshot_time_date)
                DO UPDATE SET
                    player_name = EXCLUDED.player_name,
                    team = EXCLUDED.team,
                    points = EXCLUDED.points,
                    assists = EXCLUDED.assists,
                    rebounds = EXCLUDED.rebounds,
                    ingested_at = EXCLUDED.ingested_at,
                    schema_version = EXCLUDED.schema_version
            """

            conn.execute(text(upsert_sql), df.to_dict(orient="records"))
            mark_snapshot_processed(conn, snapshot_date)

        emit_alert(
            severity="INFO",
            source="GOLD_LOADER",
            snapshot_date=snapshot_date,
            message="Gold load completed successfully",
            details={
                "rows_loaded": rows_read,
                "schema_version": schema_version
            }
        )

        logger.info(f"END | Incremental Gold load completed for {snapshot_date}")

    except Exception as e:
        emit_alert(
            severity="CRITICAL",
            source="GOLD_LOADER",
            snapshot_date=snapshot_date,
            message="Gold load failed",
            details={"error": str(e)}
        )

        logger.exception(
            f"Gold load failed for snapshot {snapshot_date}"
        )
        raise


def main():
    snapshot_date = datetime.today().strftime("%Y-%m-%d")
    load_to_postgres(snapshot_date)


if __name__ == "__main__":
    main()
