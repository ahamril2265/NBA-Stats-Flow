# NBA Player Data Engineering Platform

A production-inspired Data Engineering pipeline that ingests, validates, transforms, monitors, and loads NBA player statistics using modern ETL design patterns.

## Overview

This project simulates how data platforms are built in industry by implementing:

- Multi-layer Bronze → Silver → Gold architecture
- Data quality validation
- Schema contract enforcement
- Data drift detection
- PostgreSQL analytics warehouse loading
- Apache Airflow orchestration
- Observability through logs and metrics

The objective is to demonstrate reliable, scalable, and maintainable batch data processing workflows.

---

## Architecture

```text
                 ┌────────────────────┐
                 │ Data Generator     │
                 └─────────┬──────────┘
                           │
                           ▼
                 ┌────────────────────┐
                 │ Bronze Layer       │
                 │ Raw Parquet Data   │
                 └─────────┬──────────┘
                           │
                           ▼
                 ┌────────────────────┐
                 │ Silver Layer       │
                 │ Validation & Clean │
                 └─────────┬──────────┘
                           │
                           ▼
                 ┌────────────────────┐
                 │ Schema Enforcement │
                 └─────────┬──────────┘
                           │
                           ▼
                 ┌────────────────────┐
                 │ Data Quality Check │
                 └─────────┬──────────┘
                           │
                           ▼
                 ┌────────────────────┐
                 │ Drift Detection    │
                 └─────────┬──────────┘
                           │
                           ▼
                 ┌────────────────────┐
                 │ Gold Layer         │
                 │ PostgreSQL         │
                 └────────────────────┘
```

---

## Features

### Data Generation
- Synthetic NBA player statistics
- Snapshot-based ingestion
- Incremental processing

### Bronze Layer
- Raw data ingestion
- Parquet storage format
- Immutable snapshots

### Silver Layer
- Data cleaning
- Type validation
- Standardized records

### Schema Management
- YAML-based schema contracts
- Versioned schema registry
- Schema evolution support

### Data Quality
- Row count validation
- Null checks
- Threshold monitoring
- Automated failure handling

### Data Drift Detection
- Statistical profiling
- Baseline generation
- Drift monitoring
- Alert generation

### Gold Layer
- PostgreSQL analytics tables
- Idempotent loading
- Snapshot tracking

### Orchestration
- Apache Airflow DAG
- Retry policies
- Dependency management

---

## Tech Stack

| Category | Technology |
|-----------|-----------|
| Language | Python |
| Orchestration | Apache Airflow |
| Storage | Parquet |
| Database | PostgreSQL |
| Validation | Pandas |
| Configuration | YAML |
| Monitoring | Logs & Metrics |

---

## Project Structure

```text
nba-player-etl/
│
├── airflow/
├── config/
├── data/
│   ├── raw/
│   ├── bronze/
│   └── silver/
│
├── metrics/
│   ├── data_quality/
│   └── drift/
│
├── schema_registry/
│
├── src/
│   ├── generator/
│   ├── ingestion/
│   ├── validation/
│   ├── schema/
│   ├── quality/
│   ├── drift/
│   ├── loader/
│   ├── alerts/
│   └── common/
│
└── README.md
```

---

## Airflow Workflow

```text
generate_data
      │
      ▼
bronze_ingest
      │
      ▼
silver_transform
      │
      ▼
schema_check
      │
      ▼
data_quality
      │
      ▼
drift_profiler
      │
      ▼
drift_baseline
      │
      ▼
drift_detector
      │
      ▼
gold_load
```

---

## Running the Project

### Clone Repository

```bash
git clone <repository-url>
cd nba-player-etl
```

### Create Environment

```bash
python -m venv venv
source venv/bin/activate
```

### Install Dependencies

```bash
pip install -r requirements.txt
```

### Configure Environment

Create a `.env` file:

```env
POSTGRES_USER=
POSTGRES_PASSWORD=
POSTGRES_HOST=
POSTGRES_PORT=
POSTGRES_DB=
```

### Execute Pipeline

```bash
python -m src.generator.generate_csv
python -m src.ingestion.ingest_raw_parquet
python -m src.validation.validate_clean_parquet
python -m src.schema.schema_check_parquet
python -m src.quality.data_quality_check_parquet
python -m src.drift.profiler
python -m src.drift.baseline
python -m src.drift.detector
python -m src.loader.load_postgres
```

---

## Key Engineering Concepts Demonstrated

- Batch Data Processing
- Medallion Architecture
- Data Quality Monitoring
- Schema Governance
- Data Observability
- Incremental ETL
- Airflow Orchestration
- Data Drift Detection
- PostgreSQL Warehousing

---

## Future Enhancements

- Docker Deployment
- Kafka Streaming Ingestion
- Great Expectations Integration
- Prometheus Metrics
- Grafana Dashboards
- CI/CD Pipeline
- Cloud Storage Support (AWS S3)

---

## Author

**Ahamed Rilwan**
- GitHub: https://github.com/ahamril2265
- LinkedIn: https://www.linkedin.com/in/ahamedrilwan
