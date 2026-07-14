from airflow import DAG
from airflow.providers.standard.operators.bash import BashOperator
import pendulum

# -------------------------------------------------------------------
# Project configuration
# -------------------------------------------------------------------
PROJECT_ROOT = "/home/ahamed/Projects/DE/nba-player-etl"

def bash(cmd: str) -> str:
    """
    Ensures Airflow tasks:
    - run from project root
    - see src/ via PYTHONPATH
    - use the correct virtualenv
    """
    return f"""
    cd {PROJECT_ROOT} &&
    export PYTHONPATH={PROJECT_ROOT} &&
    source venv/bin/activate &&
    {cmd}
    """

DEFAULT_ARGS = {
    "owner": "data-platform",
    "retries": 2,
    "retry_delay": pendulum.duration(minutes=5),
}

# -------------------------------------------------------------------
# DAG definition
# -------------------------------------------------------------------
with DAG(
    dag_id="nba_player_etl_v3",
    default_args=DEFAULT_ARGS,
    schedule="@daily",
    start_date=pendulum.datetime(2025, 12, 29, tz="UTC"),
    catchup=True,
    tags=["nba", "etl", "v3"],
) as dag:

    # ---------------- Tasks ---------------- #

    generate_data = BashOperator(
    task_id="generate_data",
    bash_command=bash("python3 -m src.generator.generate_csv"),
    )

    bronze_ingest = BashOperator(
        task_id="bronze_ingest",
        bash_command=bash("python3 -m src.ingestion.ingest_raw_parquet"),
    )

    silver_transform = BashOperator(
        task_id="silver_transform",
        bash_command=bash("python3 -m src.validation.validate_clean_parquet"),
    )

    schema_check = BashOperator(
        task_id="schema_check",
        bash_command=bash("python3 -m src.schema.schema_check_parquet"),
    )

    data_quality = BashOperator(
        task_id="data_quality",
        bash_command=bash("python3 -m src.quality.data_quality_check_parquet"),
    )

    drift_profiler = BashOperator(
        task_id="drift_profiler",
        bash_command=bash("python3 -m src.drift.profiler"),
    )

    drift_baseline = BashOperator(
        task_id="drift_baseline",
        bash_command=bash("python3 -m src.drift.baseline"),
    )

    drift_detector = BashOperator(
        task_id="drift_detector",
        bash_command=bash("python3 -m src.drift.detector"),
    )

    gold_load = BashOperator(
        task_id="gold_load",
        bash_command=bash("python3 -m src.loader.load_postgres"),
    )


    # ---------------- Dependencies ---------------- #

    generate_data >> bronze_ingest >> silver_transform
    silver_transform >> schema_check >> data_quality
    data_quality >> drift_profiler >> drift_baseline >> drift_detector >> gold_load

