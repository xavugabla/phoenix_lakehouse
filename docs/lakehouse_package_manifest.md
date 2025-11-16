# Lakehouse Package Manifest

Purpose: isolate every Iceberg/GCS-centric piece so it can be copied into a dedicated **data platform** repository while leaving this mono-repo focused on ETL/orchestration. Everything listed below either defines *where data lives in GCS*, *how Iceberg tables are created/registered*, or *how clients query the lakehouse*.

> ✅ Copy the items in this manifest into the new repo.  
> ⛔ Do **not** delete them from this repo until the lakehouse repo is live.

---

## 1. Component Inventory

| Category | Path(s) | Role / Notes | Key Dependencies |
| --- | --- | --- | --- |
| **Config & Dependencies** | `configs/datasets.yaml` (only `lakehouse` + storage defaults), `configs/connections.env.example`, `prefect.yaml`, `pyproject.toml`, `requirements.txt`, `requirements-workpool.txt` | Defines buckets (`lakehouse.gcs_bucket`, `lakehouse.gcs_prefix`), BigQuery catalog (`catalog.*`), and Python deps required by PyIceberg, PyArrow, GCS/BigQuery clients, Prefect flows. | `pydantic`, `pyyaml`, `prefect`, `pyiceberg[gcp,pandas,pyarrow]`, `google-cloud-storage`, `google-cloud-bigquery`, `pyarrow`, `structlog` |
| **Catalog Data** | `catalogues/iceberg_catalog.json` (generated file), entire `catalogues/cenace_catalogues/` subtree | File-based catalog (maps table → GCS metadata) plus raw/entity catalogues seed data imported into Iceberg. Required for bootstrap + fallbacks. | `google-cloud-storage` (lookup updates), `json` |
| **Iceberg I/O** | `src/pipeline_tasks/io/iceberg.py`, `src/pipeline_tasks/io/iceberg_catalog.py`, `src/pipeline_tasks/io/catalog_sync.py`, `src/pipeline_tasks/io/gcs.py`, `src/pipeline_tasks/io/local.py` (just filesystem helpers referenced by the above) | Loads catalogs, tables, discovers metadata, uploads/downloads from GCS, registers tables in BigQuery, and keeps JSON catalog in sync. | `pyiceberg`, `google-auth`, `google-cloud-storage`, `pyarrow`, `pandas` |
| **Schemas & Contracts** | `src/pipeline_tasks/schemas/master_schemas.py`, `src/pipeline_tasks/schemas/cenace_{pend,pml,psc}.py`, `src/pipeline_tasks/schemas/catalog_node.py`, `src/pipeline_tasks/schemas/master_schemas.py` | Ground-truth Iceberg schemas (PyIceberg `Schema`), PyArrow schemas for Parquet staging, and Pydantic models for partitions/manifests. Needed to create tables and validate writes. | `pyiceberg`, `pyarrow`, `pydantic` |
| **Consolidation → Iceberg Writers** | `src/pipeline_tasks/consolidate/cenace_{pend,pml,psc}.py` | Prefect tasks that load staged data, conform schemas, create tables if missing, write to Iceberg (in-memory catalog → GCS), and call `publish_table_metadata`. | `prefect`, `pyarrow`, `pyiceberg`, `pandas`, `structlog` |
| **Lakehouse Utilities & Storage** | `src/pipeline_tasks/storage/{manifest.py,sync.py}`, `src/pipeline_tasks/config.py` (for `LakehouseConfig`), `src/pipeline_tasks/extraction/helpers.py` (only `fetch_catalog_dataframe`, `chunk_date_range`), `src/pipeline_tasks/pipeline_tasks/__init__` (if needed for imports) | Manifest model used when syncing files, config models exposing lakehouse settings, helpers that query Iceberg catalogs for latest timestamps/nodes, etc. | `prefect`, `pydantic`, `pyiceberg`, `pandas` |
| **Prefect Flows & Tasks** | `orchestration/flows/backfill.py`, `orchestration/flows/cenace_daily.py`, `orchestration/flows/migrate_local_to_lakehouse.py`, `orchestration/tasks/iceberg_tasks.py`, `orchestration/utils/{audit_lakehouse.py,migrate_catalogs.py}` | Operational entrypoints: backfill/daily flows write to lakehouse; migration/audit flows bootstrap tables & catalogs; `iceberg_tasks` provides latest-timestamp lookup. | `prefect`, `pyiceberg`, `pandas`, `pyarrow`, `google-cloud-*` |
| **Client Examples & Analysis** | `examples/query_from_python.py`, `examples/query_from_duckdb.py`, `examples/web_app_backend.py`, `src/analysis/example_lakehouse_query.py` | Ready-made integrations for PyIceberg, DuckDB, and FastAPI backends that demonstrate how downstream systems query the lakehouse. | `pyiceberg`, `duckdb`, `fastapi`, `pandas` |
| **Documentation** | `LAKEHOUSE_VERIFICATION.md`, `docs/QUERYING_ICEBERG.md`, `docs/BQ_CATALOG_SETUP.md`, `docs/GCS_CREDENTIALS_SETUP.md`, `docs/FIX_STORAGE_*` (optional historical context) | Process knowledge: how to register tables, verify catalogs, set up credentials, and query Iceberg. Move these so the new repo carries the institutional memory. | n/a |
| **Support Scripts** | `populate_catalogue.py`, `run_local.py` (if used for lakehouse drills), `workpool-config.json`, `workpool-packages.json`, `deploy.ps1` (if deployments manage lakehouse flows) | Optional but handy references for automation and deployment packaging. | Powershell/Python |

---

## 2. Proposed Lakehouse Repo Layout

```
lakehouse-platform/
├─ README.md                        # New overview + diagram
├─ pyproject.toml / requirements/*.txt
├─ configs/
│  └─ datasets.yaml                 # Trim to lakehouse + shared defaults
├─ catalogues/
│  ├─ iceberg_catalog.json
│  └─ cenace_catalogues/*.json
├─ docs/
│  ├─ LAKEHOUSE_VERIFICATION.md
│  ├─ QUERYING_ICEBERG.md
│  ├─ BQ_CATALOG_SETUP.md
│  └─ GCS_CREDENTIALS_SETUP.md
├─ src/
│  └─ lakehouse/                    # Rename `pipeline_tasks` → `lakehouse`
│     ├─ config.py                  # Keep LakehouseConfig models
│     ├─ io/{iceberg.py,...}
│     ├─ schemas/
│     ├─ storage/
│     ├─ consolidate/
│     └─ utils/ (audit helpers, manifests, etc.)
├─ orchestration/
│  ├─ flows/{backfill.py,cenace_daily.py,migrate_local_to_lakehouse.py}
│  ├─ tasks/iceberg_tasks.py
│  └─ utils/{audit_lakehouse.py,migrate_catalogs.py}
├─ examples/
│  ├─ query_from_python.py
│  ├─ query_from_duckdb.py
│  └─ web_app_backend.py
└─ analysis/example_lakehouse_query.py
```

**Renaming note:** after copying, update imports from `pipeline_tasks` → new package name (`lakehouse` recommended) to decouple from the ETL brain. Keep module boundaries identical to simplify later syncing.

---

## 3. Copy Checklist & Sequencing

1. **Config + dependencies**
   - Copy `pyproject.toml`, `requirements*.txt`, `prefect.yaml`.
   - Prune optional extras after verifying nothing depends on them.
2. **Shared data assets**
   - Copy `catalogues/` in full (JSON catalogues) and ensure `.gitignore` keeps generated manifests private.
3. **Source modules**
   - Copy `src/pipeline_tasks/` subpackages listed in the inventory.
   - Delete extraction/transform modules **only after** the new repo compiles and tests; until then keep them here.
4. **Orchestration + scripts**
   - Copy the targeted Prefect flows/tasks + utils.
5. **Docs + examples**
   - Move the four lakehouse docs plus examples and `LAKEHOUSE_VERIFICATION.md`.
6. **Deployment assets**
   - Copy `workpool-*.json`, `deploy.ps1`, and `run_local.py` if they’re tied to lakehouse verification.

> **Tip:** use `robocopy`/`rsync` with explicit include lists to avoid copying ETL-specific directories such as `src/pipeline_tasks/extraction/` or `src/scrapers/`.

---

## 4. Dependency & Environment Notes

- **Python:** 3.10+ (PyIceberg and Prefect align on ≥3.10).  
- **Core libs:** `pyiceberg[gcp,pandas,pyarrow]`, `pyarrow>=14`, `prefect>=2.14`, `google-cloud-storage`, `google-cloud-bigquery`, `pandas`, `structlog`.  
- **Optional libs:** `duckdb`, `fastapi`, `uvicorn` (only needed if you keep the example services).  
- **Environment variables:**  
  - `GOOGLE_APPLICATION_CREDENTIALS` → service-account JSON with Storage Admin + BigQuery Admin.  
  - `BIGQUERY_CATALOG_LOCATION` (defaults to `US`) if you store metadata outside the default region.  
  - Prefect cloud/work-pool variables as needed.
- **GCS layout:** tables live at `gs://{lakehouse.gcs_bucket}/{lakehouse.gcs_prefix or ""}/{table_name}` with sub-folders `data/` and `metadata/`.
- **BigQuery catalog:** refer to `LakehouseConfig.catalog.*` (project/dataset/name). `orchestration/utils/migrate_catalogs.py` assumes dataset already exists or can be created.

---

## 5. Handoff & Verification Workflow

1. **Bootstrap repo**
   - Copy files per checklist.
   - Rename package to `lakehouse` and run `python -m pip install -e .[dev]`.
2. **Smoke tests**
   - `python orchestration/utils/audit_lakehouse.py` → confirms config & bucket layout.
   - `python orchestration/flows/migrate_local_to_lakehouse.py --dataset pend` (or run via Prefect) to ensure table creation + metadata updates still work.
   - `python orchestration/utils/migrate_catalogs.py` → republish entity catalogues and register with BigQuery.
3. **Client validation**
   - Run `examples/query_from_python.py` (PyIceberg) and `examples/query_from_duckdb.py`.
   - If exposing APIs, `uvicorn examples.web_app_backend:app --reload` should succeed.
4. **Production readiness**
   - Import flows into Prefect Cloud/work pool via `prefect deploy` + `workpool-config.json`.
   - Confirm `configs/datasets.yaml` lakehouse block matches new bucket/project before unlocking writes.
5. **Backwards compatibility**
   - Until the ETL repo stops referencing these modules, keep them as a git submodule or vendor copy. After switchover, remove duplicated directories from this repo.

---

## 6. Items That Stay Behind (ETL Brain)

- `src/pipeline_tasks/extraction/*`, `src/pipeline_tasks/transform/*`, `src/scrapers/*`, `data/*` raw/staged/consolidated directories.
- Tests targeting extraction/transformation.
- Any infra scripts that deploy scrapers or ingestion-only jobs.

Documenting this boundary now will prevent circular dependencies once the lakehouse components live in their own repository.

