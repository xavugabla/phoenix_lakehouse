# Iceberg Catalog Setup

This guide explains how the file-based/Hadoop-style Iceberg catalog works on GCS.

## Catalog Architecture

The catalog uses a **file-based/Hadoop-style** catalog stored directly in GCS. All Iceberg table metadata (snapshots, schemas, manifests) is stored under the warehouse path.

## Configuration

Edit `configs/lakehouse.yaml`:

```yaml
catalog:
  type: "hadoop"
  warehouse: "gs://lakehouse_phoenix/iceberg/"
```

The warehouse path:
- Must be a GCS path (`gs://bucket/path/`)
- Must end with `/`
- Will contain all Iceberg catalog metadata

## How It Works

1. **Catalog Initialization:**
   ```python
   from lakehouse_core.catalogs import get_iceberg_catalog
   
   catalog = get_iceberg_catalog()
   ```

2. **Table Creation:**
   When you create a table, the catalog stores metadata in GCS:
   ```
   gs://lakehouse_phoenix/iceberg/
     {namespace}/
       {table_name}/
         metadata/
           v1.metadata.json
           v2.metadata.json
           ...
   ```

3. **Table Access:**
   ```python
   from lakehouse_core.tables import get_table_identifier
   
   identifier = get_table_identifier("bronze.example_table")
   table = catalog.load_table(identifier)
   ```

## GCS Permissions

Your service account needs:
- **Storage Object Admin** role on the GCS bucket
- Read/write access to the warehouse path

## Verification

Verify the catalog works:

```python
from lakehouse_core.catalogs import get_iceberg_catalog

catalog = get_iceberg_catalog()
print(f"Catalog type: {catalog.__class__.__name__}")

# List namespaces (if any tables exist)
namespaces = catalog.list_namespaces()
print(f"Namespaces: {namespaces}")
```

## Notes

- **No BigQuery:** BigQuery is not used as an Iceberg catalog in this repo
- **No Sync:** There's no catalog synchronization - metadata lives directly in GCS
- **Portable:** The file-based catalog is portable and doesn't require external services
- **Simple:** All metadata is stored in a predictable GCS structure

