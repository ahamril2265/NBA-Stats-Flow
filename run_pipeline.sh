#!/bin/bash
set -e  # Exit immediately on any failure

echo "=============================="
echo " NBA PLAYER ETL PIPELINE START "
echo "=============================="

SNAPSHOT_DATE=$(date +%F)
echo "Snapshot Date: $SNAPSHOT_DATE"
echo

# -------- Phase 1: Data Generation --------
echo "▶ Phase 1: Data Generation"
python3 -m src.generator.generate_csv
echo "✔ Data generation completed"
echo

# -------- Phase 2: Bronze Ingestion --------
echo "▶ Phase 2: Bronze Ingestion"
python3 -m src.ingestion.ingest_raw_parquet
echo "✔ Bronze ingestion completed"
echo

#echo "▶ Phase 2: Bronze Ingestion"
#python3 -m src.ingestion.ingest_raw_csv
#echo "✔ Bronze ingestion completed"
#echo

# -------- Phase 3: Silver Transformation --------
echo "▶ Phase 3: Silver Transformation"
python3 -m src.validation.validate_clean_parquet
echo "✔ Silver transformation completed"
echo

#echo "▶ Phase 3: Silver Transformation"
#python3 -m src.validation.validate_clean_csv
#echo "✔ Silver transformation completed"
#echo

# -------- Phase 2.2: Schema Enforcement --------
echo "▶ Phase 2.2: Schema Enforcement (Parquet)"
python3 -m src.schema.schema_check_parquet
echo "✔ Parquet schema enforcement passed"
echo

#echo "▶ Phase 2.2: Schema Enforcement (CSV)"
#python3 -m src.schema.schema_check_csv
#echo "✔ CSV schema enforcement passed"
#echo

# -------- Phase 2.3: Data Quality Checks --------
echo "▶ Phase 2.3: Data Quality Check (Parquet)"
python3 -m src.quality.data_quality_check_parquet
echo "✔ Parquet data quality check passed"
echo

#echo "▶ Phase 2.3: Data Quality Check (CSV)"
#python3 -m src.quality.data_quality_check_csv
#echo "✔ CSV data quality check passed"
#echo

# -------- Phase 5: Gold Load --------
echo "▶ Phase 5: Gold Load (PostgreSQL)"
python3 -m src.loader.load_postgres
echo "✔ Gold load completed"
echo

echo "=============================="
echo " PIPELINE COMPLETED SUCCESSFULLY "
echo "=============================="
