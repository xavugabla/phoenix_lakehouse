# BigQuery + GCS Lakehouse Checklist

Use this guide to (re)publish the Iceberg metadata into BigQuery and verify that
all Prefect flows pull their entity catalogues from the BigQuery catalog.

## 1. Prerequisites

- Service account or workload identity with the following roles:
  - `roles/bigquery.admin`
  - `roles/storage.admin`
- `GOOGLE_APPLICATION_CREDENTIALS` must point to the service account JSON key
  when running locally.
- `configs/datasets.yaml` must have `lakehouse.catalog_type: "bigquery"` and
  the catalog block populated with `project`, `dataset`, and a catalog `name`.

## 2. Publish Entity Catalogs

1. Activate your virtual environment and authenticate with Google Cloud.
2. Run the Prefect flow (or call the underlying utility) to rebuild the
   catalogue tables and register them in BigQuery:

   ```bash
   # Prefect flow wrapper
   python orchestration/flows/migrate_catalogs.py

   # or call the utility directly
   python orchestration/utils/migrate_catalogs.py
   ```

   This script performs the following:
   - Creates/refreshes Iceberg tables for `cenace_*` catalogues in
     `gs://lakehouse_phoenix`.
   - Registers every table (including `pend`, `pml`, `psc`) with the BigQuery
     catalog namespace (`novagrid-476915.novagrid_dataset` by default).
   - Updates the JSON file catalog for backward compatibility.

## 3. Verify Metadata Registration

Run the audit helper to confirm the inferred table locations:

```bash
python orchestration/utils/audit_lakehouse.py
```

Then open the BigQuery console (or use `bq ls novagrid_dataset`) and confirm
that the following tables exist and are queryable:

- `cenace_node_catalog`
- `cenace_load_zones`
- `cenace_load_zone_nodes`
- `cenace_reserve_zones`
- `cenace_reserve_zone_nodes`
- `pend`, `pml`, `psc`

## 4. Smoke Tests

1. **Entity discovery**: Run `python - <<'PY' ...` to ensure extraction helpers
   are reading from the catalog:

   ```python
   from pipeline_tasks.extraction.cenace_pml import load_nodes_from_catalog
   print(len(load_nodes_from_catalog()))
   ```

   The log output should mention `source="bigquery"`.

2. **Prefect backfill**: Execute a small backfill chunk (e.g., `nodes_limit=1`)
   with `orchestration/flows/backfill.py` and confirm the flow logs the
   BigQuery catalog usage plus the consolidation step reports the updated
   metadata pointer.

3. **Query validation**: Use BigQuery (SQL) or PyIceberg to run:

   ```python
   from pipeline_tasks.io.iceberg import load_table_by_name
   table = load_table_by_name("cenace_node_catalog")
   print(table.scan(selected_fields=("node_id",)).to_pandas().head())
   ```

## 5. Troubleshooting

- If registration fails, re-run `migrate_catalogs.py` after verifying the
  service account has `BigQuery Admin` permissions.
- If extraction helpers fall back to JSON, ensure `lakehouse.catalog_type`
  is still `bigquery` and rerun the migration flow.
- Use `prefect logs --name publish-entity-catalogs` to inspect the migration
  flow output when running inside Prefect Cloud/work pools.


