import os
import pandas as pd
from datetime import datetime
from typing import List

from src.common.config_loader import load_config
from src.common.logger import get_logger

logger = get_logger("RAW_INGESTION")

RAW_BASE_PATH = "data/raw"
BRONZE_BASE_PATH = "data/bronze"

def discover_snapshots() -> List[str]:
    """
    Discover available snapshot_date partitions from raw storage.
    """
    if not os.path.exists(RAW_BASE_PATH):
        return []

    partitions = []
    for name in os.listdir(RAW_BASE_PATH):
        if name.startswith("snapshot_date="):
            partitions.append(name.split("=")[1])

    return sorted(partitions)



def ingest_snapshot(snapshot_date: str):
    config = load_config()

    input_path = f"{RAW_BASE_PATH}/snapshot_date={snapshot_date}/nba_player_stats.csv"

    logger.info(f"START | Raw ingestion for snapshot {snapshot_date}")

    if not os.path.exists(input_path):
        logger.error(f"Raw file not found: {input_path}")
        raise FileNotFoundError(f"Missing raw snapshot: {snapshot_date}")

    df = pd.read_csv(input_path)
    input_row_count = len(df)

    logger.info(f"Rows read from raw CSV: {input_row_count}")

    # Add ingestion metadata
    df["ingested_at"] = datetime.utcnow()

    output_dir = f"{BRONZE_BASE_PATH}/snapshot_date={snapshot_date}"
    os.makedirs(output_dir, exist_ok=True)

    output_path = f"{output_dir}/nba_player_stats_bronze.csv"
    df.to_csv(output_path, index=False)

    logger.info(f"END | Bronze ingestion completed")
    logger.info(f"Rows written to bronze: {len(df)}")
    logger.info(f"Bronze file path: {output_path}")


def main(snapshot_date: str = None):
    config = load_config()

    if snapshot_date:
        ingest_snapshot(snapshot_date)
    else:
        # Default behavior: ingest latest snapshot
        snapshots = discover_snapshots()
        if not snapshots:
            logger.error("No snapshot partitions found in raw layer")
            raise RuntimeError("No snapshots available for ingestion")

        latest_snapshot = snapshots[-1]
        logger.info(f"No snapshot_date provided. Using latest: {latest_snapshot}")
        ingest_snapshot(latest_snapshot)

if __name__ == "__main__":
    main()
