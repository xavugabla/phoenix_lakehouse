# Lakehouse Architecture Verification

## File-Based Catalog (Default)

### How It Works

When consolidation tasks write to Iceberg tables using the in-memory catalog, they:
1. Write Parquet data files to GCS (`gs://lakehouse_phoenix/{table_name}/data/`)
2. Write metadata files to GCS (`gs://lakehouse_phoenix/{table_name}/metadata/`)
3. Create a `metadata.json` file pointing to the latest metadata
4. **Automatically update** the file-based catalog (`catalogues/iceberg_catalog.json`) with the metadata location

The file-based catalog:
- Maps table names to GCS metadata locations
- Is automatically updated on each write
- Requires no external services (no BigQuery needed)
- Works from any environment (web app, local, cloud)

### Verification Status

✅ **File-based catalog is the default** - no BigQuery required for basic functionality

### How to Verify Tables

1. **Check Catalog File**:
   ```bash
   cat catalogues/iceberg_catalog.json
   ```
   Should show table names mapped to GCS metadata locations

2. **Via Python (Recommended)**:
   ```python
   from pipeline_tasks.io.iceberg import load_table_by_name
   
   table = load_table_by_name("pend")
   df = table.scan(limit=10).to_pandas()
   print(f"Found {len(df)} rows")
   ```

3. **Check GCS Structure**:
   ```bash
   gsutil ls gs://lakehouse_phoenix/pend/
   ```
   Should show:
   - `data/` directory with Parquet files
   - `metadata/` directory with metadata files

### BigQuery Catalog (Optional)

BigQuery catalog is **optional** and only needed if you want to query via BigQuery SQL. It is not required for:
- Writing data (uses in-memory catalog)
- Reading data (uses file-based catalog or direct GCS paths)
- Web app queries (use PyIceberg or DuckDB)
- Local project queries (use PyIceberg)

### Testing Checklist

- [x] File-based catalog is created and updated automatically
- [x] Tables can be queried using `load_table_by_name()`
- [x] Migration script updates catalog after writing
- [x] Consolidation tasks update catalog after writing
- [ ] Backfill flow can query latest timestamps (uses file-based catalog)
- [ ] Daily flow can append new data and update catalog

