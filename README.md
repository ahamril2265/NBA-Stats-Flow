# NBA Player Statistics ETL Pipeline — V2

## Overview

This project is a **production-style Data Engineering pipeline** that ingests NBA player statistics, enforces schema and data quality contracts, and loads analytics-ready data into PostgreSQL with **strong operational guarantees**.

**V2 focuses on correctness, observability, and on-call readiness**, moving beyond simple ETL into a system that can be trusted in real-world environments. The pipeline is **fail-fast**, **idempotent**, **schema-aware**, and **fully observable** through logs, metrics, and alerts.

---

## Architecture (V2)

The pipeline follows a refined Medallion architecture with integrated quality and schema gates.

### Key V2 Capabilities

* **✅ End-to-End Pipeline:** Automated flow from Raw (CSV) → Bronze (Parquet) → Silver (Cleaned) → Gold (PostgreSQL).
* **✅ Schema Enforcement:** Versioned schema registry with backward-compatibility checks and breaking change detection.
* **✅ Data Quality Gates:** Threshold-based failure handling for row count drift and null percentage spikes.
* **✅ Observability:** Unified logging (Console + File) and structured alerts with severity levels (**INFO**, **WARN**, **CRITICAL**).
* **✅ Operational Safety:** Exactly-once semantics via processed snapshot tracking and idempotent Gold loads.

---

## Technology Stack

* **Language:** Python, SQL
* **Storage:** Local filesystem (CSV, Parquet)
* **Database:** PostgreSQL
* **Orchestration:** Bash (V2), Airflow-ready Python entry points
* **Observability:** Python logging, YAML-based config, and JSONL metrics

---

## Project Structure

```text
nba-player-etl/
├── src/
│   ├── generator/      # Synthetic data generation
│   ├── ingestion/      # Bronze ingestion (Parquet conversion)
│   ├── processing/     # Silver transformations (Cleaning)
│   ├── schema/         # Schema enforcement (CSV + Parquet)
│   ├── quality/        # Data quality checks
│   ├── loader/         # Gold loader (PostgreSQL)
│   ├── alerts/         # Structured alert manager
│   └── common/         # Logger, config loader
├── schema_registry/    # Versioned YAML schemas
├── metrics/            # Schema + quality metrics (JSONL)
├── logs/               # Unified pipeline logs
├── config/             # base.yaml, environment configs
├── run_pipeline.sh     # End-to-end orchestration script
└── README.md

```

---

## Execution (V2)

### 1. Grant Permissions

```bash
chmod +x run_pipeline.sh

```

### 2. Run the Full Pipeline

```bash
./run_pipeline.sh

```

> **Note:** The pipeline is designed to stop immediately on any failure to prevent downstream data corruption.

---

## Failure & Alerting Model

### Alert Severity Levels

| Severity | Meaning |
| --- | --- |
| **INFO** | Successful execution or expected skip (e.g., snapshot already processed). |
| **WARN** | Minor drift detected; pipeline continues but requires review. |
| **CRITICAL** | **Pipeline stopped.** Immediate manual intervention required. |

### Failure Scenarios

* **Breaking Schema Change:** Triggers **CRITICAL** alert and halts the process.
* **Quality Threshold Breach:** (e.g., >5% nulls) Triggers **CRITICAL** alert and halts the process.
* **Gold Load Failure:** Database connection or constraint errors trigger a rollback and **CRITICAL** alert.

---

## Metrics & Logs

* **Unified Logs:** Found in `logs/pipeline.log`.
* **Schema Metrics:** Tracked in `metrics/schema/` (Append-only JSONL).
* **Quality Metrics:** Tracked in `metrics/data_quality/` (Snapshot-partitioned).

---

## Idempotency & Incremental Loads

Each snapshot is processed **exactly once**.

1. Processed snapshots are tracked in a `metadata.processed_logs` table in PostgreSQL.
2. If the pipeline is re-run for a previously successful day, the Gold load is skipped.
3. The system emits an **INFO** alert and terminates gracefully to avoid duplicate records.

---

## Testing & Validation

To validate the alerting and fail-fast mechanism, you can force a failure:

```bash
export FORCE_SCHEMA_FAILURE=true
./run_pipeline.sh

```

**Expected Result:**

* Pipeline exits with non-zero status.
* `logs/pipeline.log` contains a **CRITICAL** alert.
* Metrics are marked as `FAILED`.

*To reset:* `unset FORCE_SCHEMA_FAILURE`

---

## V3 Roadmap (Planned)

* **Airflow Orchestration:** Transition from Bash to full DAG-based scheduling.
* **Advanced Drift Detection:** Implementation of PSI (Population Stability Index).
* **Backfill Automation:** Automated CLI for re-processing historical ranges.

---

**Author:** ARM

*Focus: Production-style Data Engineering systems.*

---
