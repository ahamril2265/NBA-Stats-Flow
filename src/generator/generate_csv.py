import os
import pandas as pd
import random
from datetime import datetime
from src.common.config_loader import load_config
from src.common.logger import get_logger

logger = get_logger("DATA_GENERATOR")


TEAMS = [
    "LAL", "GSW", "BOS", "MIA", "CHI",
    "PHX", "DEN", "DAL", "NYK", "MIL",
    "ATL", "BKN", "CHA", "CLE", "DET",
    "HOU", "IND", "LAC", "MEM", "MIN",
    "NOP", "OKC", "ORL", "PHI", "POR",
    "SAC", "TOR", "UTA", "WAS"
]

SEASONS = ["2021-22", "2022-23", "2023-24", "2024-25", "2025-26"]


def generate_player_stats(num_records: int, snapshot_date: str) -> pd.DataFrame:
    data = []

    for i in range(num_records):
        player_id = random.randint(1, 5000)

        data.append({
            "player_id": player_id,
            "player_name": f"Player_{player_id}",
            "team": random.choice(TEAMS),
            "season": random.choice(SEASONS),
            "points": random.randint(0, 60),
            "assists": random.randint(0, 20),
            "rebounds": random.randint(0, 25),
            "snapshot_time_date": snapshot_date
        })

    return pd.DataFrame(data)


def main():
    config = load_config()
    snapshot_date = datetime.today().strftime("%Y-%m-%d")
    min_rows = config["base"]["data"]["min_rows_expected"]

    logger.info(f"START | Generating data for snapshot {snapshot_date}")

    df = generate_player_stats(
        num_records=min_rows,
        snapshot_date=snapshot_date
    )

    output_dir = f"data/raw/snapshot_date={snapshot_date}"
    os.makedirs(output_dir, exist_ok=True)

    output_path = f"{output_dir}/nba_player_stats.csv"
    df.to_csv(output_path, index=False)

    logger.info(f"END | Generated {len(df)} records")
    logger.info(f"File written to {output_path}")


if __name__ == "__main__":
    main()
