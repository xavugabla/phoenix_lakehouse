# Migration Checklist

Use this checklist when migrating data from `data_pipeline/data/` to the lakehouse.

**Note:** Migration scripts belong in the **data-pipeline repo**, not in phoenix_lakehouse. phoenix_lakehouse is a pure library that provides contracts and paths.

## Prerequisites

### In phoenix_lakehouse repo:
- [ ] Verify installation: `pip install -e .`
- [ ] Verify config loads: `python -c "from lakehouse_core import get_lakehouse_config; print(get_lakehouse_config())"`
- [ ] Verify catalog initializes: `python -c "from lakehouse_core.catalogs import get_iceberg_catalog; cat = get_iceberg_catalog()"`
- [ ] Table contracts defined in `configs/tables/cenace.yaml`:
  - [ ] `bronze.pend` contract exists
  - [ ] `bronze.pml` contract exists

### In data-pipeline repo:
- [ ] `phoenix_lakehouse` installed as dependency: `pip install -e ../phoenix_lakehouse`
- [ ] GCS bucket `lakehouse_phoenix` exists and is accessible
- [ ] Service account has Storage Admin permissions
- [ ] `GOOGLE_APPLICATION_CREDENTIALS` environment variable set
- [ ] Can access GCS: `python -c "from google.cloud import storage; print(list(storage.Client().list_buckets()))"`

## Pre-Migration

### In phoenix_lakehouse repo:
- [ ] Review `DATA_ANALYSIS.md` to understand current data structure
- [ ] Verify table contracts in `configs/tables/cenace.yaml`:
  - [ ] `bronze.pend` contract exists
  - [ ] `bronze.pml` contract exists
  - [ ] Partition keys match data structure

### In data-pipeline repo:
- [ ] Create `data_pipeline/schemas/` directory
- [ ] Define PyIceberg schemas:
  - [ ] `data_pipeline/schemas/pend.py` with `PEND_BRONZE_SCHEMA`
  - [ ] `data_pipeline/schemas/pml.py` with `PML_BRONZE_SCHEMA`
- [ ] Create migration script: `data_pipeline/scripts/migrate_to_lakehouse.py`
  - [ ] Uses `lakehouse_core` imports
  - [ ] Reads from `data/consolidated/`
  - [ ] Writes to Iceberg tables via catalog

## Migration Steps (Run in data-pipeline repo)

### Raw Data Migration

- [ ] Create upload script in data-pipeline repo
- [ ] Upload `data/raw/cenace/` to `gs://lakehouse_phoenix/raw/cenace/`
- [ ] Use `lakehouse_core.paths.zone_prefix("raw")` to get path
- [ ] Preserve directory structure (for replay/debugging)
- [ ] Verify files uploaded correctly: `gsutil ls gs://lakehouse_phoenix/raw/cenace/`

### PEND Data Migration

- [ ] Run migration script: `python scripts/migrate_to_lakehouse.py --dataset pend`
- [ ] Script should:
  - [ ] Read consolidated Parquet files from `data/consolidated/pend/`
  - [ ] Extract partition values (market, region, zone, year) from path
  - [ ] Get table contract: `get_table_contract("bronze.pend")`
  - [ ] Get table location: `get_full_gcs_path("bronze.pend")`
  - [ ] Create Iceberg table using:
    - [ ] Schema: `PEND_BRONZE_SCHEMA` (from data-pipeline repo)
    - [ ] Partition spec from contract's `partition_by`
    - [ ] Location from `get_full_gcs_path()`
  - [ ] Write data to Iceberg table via `catalog.create_table()` or `table.append()`
- [ ] Verify table in catalog: `catalog.load_table(get_table_identifier("bronze.pend"))`
- [ ] Query sample data to verify correctness

### PML Data Migration

- [ ] Run migration script: `python scripts/migrate_to_lakehouse.py --dataset pml`
- [ ] Script should:
  - [ ] Read consolidated Parquet files from `data/consolidated/pml/`
  - [ ] Extract partition values (market, region, node, year) from path
  - [ ] Get table contract: `get_table_contract("bronze.pml")`
  - [ ] Get table location: `get_full_gcs_path("bronze.pml")`
  - [ ] Create Iceberg table using schema and partition spec
  - [ ] Write data to Iceberg table
- [ ] Verify table in catalog
- [ ] Query sample data to verify correctness

## Post-Migration Verification (Run in data-pipeline repo)

- [ ] Verify raw data in GCS: `gsutil ls -r gs://lakehouse_phoenix/raw/cenace/`
- [ ] Verify bronze tables exist (using phoenix_lakehouse):
  ```python
  from lakehouse_core.catalogs import get_iceberg_catalog
  from lakehouse_core.tables import get_table_identifier
  
  catalog = get_iceberg_catalog()
  pend_table = catalog.load_table(get_table_identifier("bronze.pend"))
  pml_table = catalog.load_table(get_table_identifier("bronze.pml"))
  print("✅ Tables exist")
  ```
- [ ] Verify row counts match source data:
  ```python
  df = pend_table.scan().to_pandas()
  print(f"Total rows: {len(df)}")
  ```
- [ ] Verify partition pruning works:
  ```python
  df = pend_table.scan(
      row_filter="market = 'MDA' AND region = 'SIN' AND zone = 'ACAPULCO'"
  ).to_pandas()
  print(f"Filtered rows: {len(df)}")
  ```
- [ ] Verify data quality (no nulls in required fields, valid timestamps)
- [ ] Verify GCS structure:
  ```bash
  gsutil ls gs://lakehouse_phoenix/bronze/cenace/
  gsutil ls gs://lakehouse_phoenix/iceberg/  # Catalog metadata
  ```

## Cleanup (After Verification)

- [ ] Archive or remove local `data/consolidated/` (optional, keep backup)
- [ ] Update ingestion pipeline to write directly to Iceberg
- [ ] Remove old consolidation logic (if no longer needed)

## Rollback Plan

If migration fails:
- [ ] Keep original `data/consolidated/` files until migration verified
- [ ] Iceberg tables can be dropped: `catalog.drop_table(identifier)`
- [ ] Raw data in GCS can be deleted if needed
- [ ] Re-run migration after fixing issues

