This is a solid architectural foundation for a Data Engineering project. I have cleaned up the formatting, improved the visual hierarchy using Markdown best practices, and ensured the technical descriptions are concise and professional.

# NBA Player Statistics ETL Pipeline (V1)

## Overview

This project implements a **production-style end-to-end Data Engineering pipeline** for NBA player statistics. It is designed to reflect real-world industry workflows by prioritizing layered data quality and schema enforcement over "toy" scripts.

The pipeline ingests synthetic data and delivers **analytics-ready Gold data** into PostgreSQL with guarantees around **correctness, idempotency, and observability**.

> **V1 Focus:** Correctness > Reliability > Clarity.
> *Advanced optimizations (upserts, alerts, indexing) are intentionally deferred to V2.*

---

## High-Level Architecture

The pipeline follows a **Medallion Architecture** (Raw → Bronze → Silver → Gold) to ensure data lineage and quality at every stage.

### Data Layers & Workflow

| Layer | Format | Purpose | Key Operations |
| --- | --- | --- | --- |
| **Raw** | CSV | Ingestion Source | Synthetic snapshots partitioned by `snapshot_date`. |
| **Bronze** | Parquet | Source of Truth | Raw data preserved as-is; adds `ingested_at` metadata. |
| **Silver** | Parquet/CSV | Validated & Clean | Deduplication, null handling, and type enforcement. |
| **Schema Gate** | JSONL | Quality Control | Validates against `schema_v1.yaml`; emits metrics. |
| **Gold** | PostgreSQL | Analytics Ready | Idempotent load into `analytics.nba_player_stats`. |

---

## Data Layers Explained

### 1. Raw Layer (CSV)

Represents external source data.

* **Storage:** `data/raw/snapshot_date=YYYY-MM-DD/`
* **Validation:** None. This is a 1:1 capture of the source.

### 2. Bronze Layer (Parquet)

The "immutable" source of truth for the internal pipeline.

* **Design Principle:** Bronze preserves truth, not cleanliness.
* **Optimization:** Converted to Parquet for efficient downstream reads.

### 3. Silver Layer (Validation & Cleaning)

Enforces structural correctness:

* Drops rows with nulls in critical fields (e.g., Player Name, Team).
* Deduplicates records within the snapshot.
* Outputs both **Parquet** (authoritative) and **CSV** (for debugging/portability).

### 4. Schema Enforcement (v1)

A strict gate ensuring Silver data matches the defined contract.

* **Checks:** Column presence, data types, and non-null constraints.
* **Observability:** Emits append-only metrics to `metrics/schema/schema_metrics.jsonl`.
* **Fail-Fast:** Prevents corrupted data from ever reaching the Gold database.

### 5. Gold Layer (PostgreSQL)

The final destination for BI and analytics.

* **Idempotency:** Uses a **TRUNCATE + INSERT** pattern to ensure runs can be retried without duplicating data.
* **Metadata:** Records are tagged with `schema_version` and `snapshot_time_date`.

---

## Tech Stack

* **Language:** Python, SQL
* **Storage:** Local filesystem (S3-ready layout)
* **File Formats:** CSV, Parquet (via PyArrow)
* **Database:** PostgreSQL (SQLAlchemy / Psycopg2)
* **Libraries:** Pandas, PyArrow

---

## Engineering Principles Demonstrated

* **Idempotent Processing:** Jobs can be re-run safely.
* **Schema-First Design:** Data contracts are defined before loading.
* **Separation of Concerns:** Configuration and secrets are decoupled from logic.
* **Partition-Awareness:** Data is organized by date to support future backfills.

---

## Execution Guide (V1)

Run the pipeline in sequence:

1. **Generate Data:** `python3 -m src.generator.generate_csv`
2. **Ingest to Bronze:** `python3 -m src.ingestion.ingest_raw`
3. **Validate (Silver):** `python3 -m src.validation.validate_clean`
4. **Schema Check:** `python3 -m src.schema.schema_check`
5. **Load to Gold:** `python3 -m src.loader.load_postgres`

---

## V2 Roadmap

* Transition from Truncate-Load to **Incremental Upserts (MERGE)**.
* Implementation of **Great Expectations** for advanced data quality thresholds.
* Full **Airflow DAG** orchestration.
* Database indexing and query optimization for the Gold layer.

**Author:** ARM

*Focus: Production-style Data Engineering systems*

