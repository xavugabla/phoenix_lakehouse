# Iceberg Catalog Setup

This guide explains how the SQL-based Iceberg catalog works with SQLite and GCS.

## Catalog Architecture

The catalog uses a **SQL catalog (SQLite)** for storing Iceberg table metadata (table names, schemas, etc.). The actual table data (Parquet files, manifests, snapshots) is stored in GCS under the warehouse path.

## Configuration

Edit `configs/lakehouse.yaml`:

```yaml
catalog:
  type: "sql"
  uri: "sqlite:///iceberg_catalog.db"  # SQLite database path
  warehouse: "gs://lakehouse_phoenix/iceberg/"  # GCS path for table data
```

Configuration options:
- **uri**: SQLite database URI (e.g., `sqlite:///iceberg_catalog.db` for relative path, or `sqlite:////absolute/path/to/db.db` for absolute path)
- **warehouse**: GCS path where table data is stored
  - Must be a GCS path (`gs://bucket/path/`)
  - Must end with `/`
  - Contains Iceberg table data (Parquet files, metadata files)

## How It Works

1. **Catalog Initialization:**
   ```python
   from lakehouse_core.catalogs import get_iceberg_catalog
   
   catalog = get_iceberg_catalog()
   ```

2. **Table Creation:**
   When you create a table:
   - Catalog metadata (table name, schema reference) is stored in SQLite database
   - Table data (Parquet files, manifests, snapshots) is stored in GCS:
   ```
   gs://lakehouse_phoenix/iceberg/
     {namespace}/
       {table_name}/
         data/
           *.parquet
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

## SQLite Database Location

The SQLite database file stores catalog metadata. Choose a location that:
- Is accessible to all processes that need to access the catalog
- Can be backed up regularly
- Is on persistent storage (not ephemeral/temporary)

Common locations:
- **Local development**: `sqlite:///iceberg_catalog.db` (project root)
- **VM/Server**: `sqlite:////var/lib/iceberg/catalog.db` (absolute path)
- **Shared storage**: `sqlite:////mnt/shared/iceberg_catalog.db` (if using shared filesystem)

## Notes

- **No BigQuery:** BigQuery is not used as an Iceberg catalog in this repo
- **SQLite Metadata:** Catalog metadata (table names, schemas) is stored in SQLite
- **GCS Data:** Table data (Parquet files, manifests) is stored in GCS warehouse
- **Portable:** SQLite database can be easily backed up and moved
- **Simple:** No external catalog service required - just SQLite and GCS

