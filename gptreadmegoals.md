You are helping me design and implement a modern lakehouse platform for my existing energy analytics stack.

Current situation:
- I have three repos:
  1) data-pipeline: Prefect-based ETL that pulls energy prices and currently writes directly to Parquet in GCS.
  2) data-manager: enriches datasets, syncs to GCS, and runs analyses; also being moved to Prefect.
  3) revenue-models: runs Monte Carlo simulations and optimizations on the data.
- I have already started using Apache Iceberg on GCS, but the lakehouse logic is currently tangled inside the data-pipeline repo.
- I want to refactor so the lakehouse is a shared platform, not embedded in any one app.

Target architecture:
- Storage: GCS as the single data lake.
- Table format: Apache Iceberg as the core abstraction for all structured data (bronze/silver/gold).
- Catalog: a single Iceberg catalog (e.g. Nessie, Dataplex, Glue, or equivalent) with clear namespaces:
  - bronze.<domain>.<table>
  - silver.<domain>.<table>
  - gold.<domain>.<table>
- Zones:
  - raw: immutable storage of source JSON/XML files in GCS for replay/debug (e.g. gs://energy-lake/raw/...).
  - bronze: minimally structured Iceberg tables, close to source (may include a raw_payload column).
  - silver: cleaned, normalized, typed tables ready for analytics and joining.
  - gold: feature/metrics/result tables for modeling, dashboards, and Monte Carlo outputs.

New repo: `lakehouse-core`
- Acts as the “platform” and single source of truth for:
  - GCS layout and path conventions (raw/bronze/silver/gold).
  - Iceberg catalog configuration and initialization.
  - Table names, schemas, and partitioning for key domains:
    - energy_prices, weather, node_metadata, revenue_features, simulation_results, etc.
  - Optional dbt project for silver/gold transformations.
- Exposes a small Python package, e.g.:
  - lakehouse_core.paths: helpers for building GCS paths.
  - lakehouse_core.catalog: functions to obtain Iceberg catalog/clients.
  - lakehouse_core.tables: constants and helpers for table names and schemas.

Role of each existing repo after refactor:
- data-pipeline:
  - Uses `lakehouse-core` to know where to write.
  - Steps:
    1) Fetch raw data from APIs (JSON/XML).
    2) Persist original payloads to GCS `raw/` zone.
    3) Parse and write to Iceberg `bronze.energy_prices` (and other bronze tables) in Parquet via Iceberg.
    4) Optionally do light transforms into `silver` where useful, but no business logic.
- data-manager:
  - Uses `lakehouse-core` for table contracts.
  - Reads from `bronze`/`silver` Iceberg tables.
  - Performs enrichments, joins (e.g. prices + weather + node metadata).
  - Writes outputs into `silver` and `gold` Iceberg tables (e.g. gold.price_features, gold.node_stats).
- revenue-models:
  - Uses `lakehouse-core` to read from `gold` tables (e.g. gold.price_features, gold.scenario_inputs).
  - Runs Monte Carlo and optimization models.
  - Writes results back as Iceberg tables in `gold` (e.g. gold.revenue_sims, gold.scenario_results).
  - Can also export ad-hoc CSVs for inspection, but the canonical outputs stay in the lakehouse.

Tech stack / engines:
- Orchestration: Prefect for running flows in data-pipeline and data-manager.
- Table format: Apache Iceberg on GCS.
- Catalog: one consistent Iceberg catalog endpoint.
- Transformations: dbt-core and/or Spark/Trino as needed, but all working against Iceberg tables.
- Local analytics: DuckDB reading Iceberg/Parquet on GCS (or via snapshots) for quick modeling and exploration.
- BigQuery:
  - Optional, not the source of truth.
  - If used, it should access Iceberg tables via BigLake/external tables for ad-hoc SQL and dashboards, but storage and governance remain with Iceberg on GCS.

Design principles:
- Storage (GCS + Iceberg) is the system of record; compute engines are disposable.
- All repos treat `lakehouse-core` as the API for where data lives and how it’s structured.
- No repo hardcodes paths or schemas; all table definitions and layout live in `lakehouse-core`.
- Always keep a raw copy of source data (files and/or raw_payload), and treat bronze as minimally transformed.
- Silver/gold layers are the only ones used for downstream analytics, modeling, and reporting.

Given this, help me:
- Harden and refactor the existing Iceberg + GCS setup into a clean `lakehouse-core` repo.
- Extract any lakehouse logic from the data-pipeline repo into `lakehouse-core`.
- Provide idiomatic Python structure for the `lakehouse-core` package and examples of how the other repos should import and use it.
- Suggest a minimal, practical initial set of tables (bronze/silver/gold) for energy prices, weather, metadata, and revenue modeling to get this lakehouse running end-to-end.
