# NBA Player Statistics ETL Pipeline (V3)

## Overview

This project implements a **production-style end-to-end Data Engineering pipeline** for NBA player statistics. It is designed to reflect real-world industry workflows by prioritizing layered data quality, schema enforcement, data drift monitoring, and robust orchestration.

The pipeline ingests synthetic data and delivers **analytics-ready Gold data** into PostgreSQL with guarantees around **correctness, idempotency, observability, and data quality**.

> **V3 Focus:** Orchestration (Airflow), Data Quality & Drift Monitoring, and Incremental Upserts.

---

## High-Level Architecture

The pipeline follows a **Medallion Architecture** (Raw → Bronze → Silver → Gold) to ensure data lineage and quality at every stage.

### Data Layers & Workflow

| Layer | Format | Purpose | Key Operations |
| --- | --- | --- | --- |
| **Raw** | CSV | Ingestion Source | Synthetic snapshots partitioned by `snapshot_date`. |
| **Bronze** | Parquet | Source of Truth | Raw data preserved as-is; adds `ingested_at` metadata. |
| **Silver** | Parquet | Validated & Clean | Deduplication, null handling, and type enforcement. |
| **Schema Gate** | JSONL | Quality Control | Validates against `schema_v2.yaml`; emits metrics. |
| **Gold** | PostgreSQL | Analytics Ready | Idempotent Upserts into `analytics.nba_player_stats`. |

---

## Pipeline Components Explained

### 1. Raw & Bronze Layers (Ingestion)

*   **Raw (CSV):** 1:1 capture of external source data partitioned by `snapshot_date`.
*   **Bronze (Parquet):** Immutable source of truth for the internal pipeline. Optimized for downstream reads.

### 2. Silver Layer (Validation & Cleaning)

Enforces structural correctness:
*   Drops rows with nulls in critical fields (e.g., Player Name, Team).
*   Deduplicates records within the snapshot.
*   Outputs as Parquet format.

### 3. Schema & Data Quality (Custom DQ)

A strict gate ensuring Silver data matches the defined contract and business rules.
*   **Schema Check:** Validates column presence, data types, and non-null constraints.
*   **Data Quality (`src.quality`):** Performs statistical validation and rule-based checks on the processed data.
*   **Fail-Fast:** Prevents corrupted data from ever reaching the Gold database.

### 4. Data Drift Monitoring (`src.drift`)

Continuous monitoring of data distributions to detect anomalies in incoming batches.
*   **Profiler & Baseline:** Generates profiles for datasets and establishes a baseline.
*   **Detector:** Compares new snapshots against the baseline to detect statistical drift.

### 5. Gold Layer (PostgreSQL)

The final destination for BI and analytics.
*   **Idempotent Upserts:** Uses `ON CONFLICT DO UPDATE SET` to enforce idempotency without truncating the table, enabling safe backfills and updates.
*   **Metadata:** Records are tagged with `schema_version`, `snapshot_time_date`, and `ingested_at`.

### 6. Alerting (`src.alerts`)

A centralized alert manager integrated throughout the pipeline to notify on failures, empty datasets, or critical data drift.

---

## Tech Stack

*   **Orchestration:** Apache Airflow
*   **Language:** Python, SQL
*   **Storage:** Local filesystem (S3-ready layout)
*   **File Formats:** CSV, Parquet (via PyArrow)
*   **Database:** PostgreSQL (SQLAlchemy / Psycopg2)
*   **Libraries:** Pandas, PyArrow

---

## Engineering Principles Demonstrated

*   **Idempotent Processing:** Jobs can be re-run safely via upserts and directory overwrites.
*   **Schema-First Design:** Data contracts are defined before loading.
*   **Separation of Concerns:** Configuration and secrets are decoupled from logic.
*   **Automated Quality & Drift Detection:** Prevents silent data corruption.

---

## Execution Guide

The pipeline is fully orchestrated using **Apache Airflow**.

1.  Start your Airflow environment.
2.  Enable the `nba_player_etl_v3` DAG.
3.  The DAG will run daily, executing the following task flow:
    `generate_data` → `bronze_ingest` → `silver_transform` → `schema_check` → `data_quality` → `drift_profiler` → `drift_baseline` → `drift_detector` → `gold_load`

---

## V4 Roadmap (Wishlist)

*   Transition from local filesystem to AWS S3.
*   Implement real-time streaming ingestion (e.g., Kafka).
*   Migrate Gold layer to a cloud data warehouse (e.g., Snowflake or BigQuery).
*   Integrate dbt for advanced Gold layer transformations.

**Author:** ARM
*Focus: Production-style Data Engineering systems*
