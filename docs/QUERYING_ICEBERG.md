# Querying Iceberg Tables

This guide explains how to query Iceberg tables from your web app, local projects, and other tools.

## Architecture Overview

Iceberg tables are **self-describing** - all schema and metadata information is stored in GCS metadata files. You don't need BigQuery or any catalog service to query them. The file-based catalog (`catalogues/iceberg_catalog.json`) simply maps table names to GCS metadata locations for convenience.

### How Catalogues Stay Updated

- **Entity catalogues** (nodes, zones): Static reference data, updated by re-running migration when needed
- **Data tables** (pend, pml, psc): **Automatically updated** when new data is written
  - Iceberg metadata files in GCS are updated on each write
  - No separate catalog update step needed
  - Any tool reading Iceberg will see the latest data automatically

## Querying from Python (PyIceberg)

### Using File-Based Catalog

```python
from pipeline_tasks.io.iceberg import load_table_by_name
import pandas as pd

# Load table by name (uses file-based catalog)
table = load_table_by_name("pend")

# Query with filters
df = table.scan(
    row_filter="region = 'SIN' AND market = 'MDA'",
    selected_fields=("timestamp", "zone", "price")
).to_pandas()

print(df.head())
```

### Using Direct GCS Path

```python
from pipeline_tasks.io.iceberg import load_table_from_gcs_path

# Load table directly from GCS metadata location
metadata_location = "gs://lakehouse_phoenix/pend/metadata/00000-abc123.metadata.json"
table = load_table_from_gcs_path(metadata_location)

# Query the table
df = table.scan().to_pandas()
```

### Getting Table Path from Catalog

```python
from pipeline_tasks.io.iceberg_catalog import get_table_path

# Get metadata location for a table
metadata_location = get_table_path("pend")
if metadata_location:
    table = load_table_from_gcs_path(metadata_location)
```

## Querying from Web App (Backend API)

### FastAPI Example

```python
from fastapi import FastAPI
from pipeline_tasks.io.iceberg import load_table_by_name
import pandas as pd

app = FastAPI()

@app.get("/api/data/{table_name}")
async def get_table_data(
    table_name: str,
    region: str = None,
    market: str = None,
    limit: int = 100
):
    """Query Iceberg table via REST API."""
    try:
        table = load_table_by_name(table_name)
        
        # Build filter
        filters = []
        if region:
            filters.append(f"region = '{region}'")
        if market:
            filters.append(f"market = '{market}'")
        
        row_filter = " AND ".join(filters) if filters else None
        
        # Query table
        df = table.scan(
            row_filter=row_filter,
            limit=limit
        ).to_pandas()
        
        return df.to_dict(orient="records")
    except Exception as e:
        return {"error": str(e)}
```

### Flask Example

```python
from flask import Flask, jsonify
from pipeline_tasks.io.iceberg import load_table_by_name

app = Flask(__name__)

@app.route("/api/data/<table_name>")
def get_table_data(table_name):
    """Query Iceberg table via REST API."""
    try:
        table = load_table_by_name(table_name)
        df = table.scan(limit=100).to_pandas()
        return jsonify(df.to_dict(orient="records"))
    except Exception as e:
        return jsonify({"error": str(e)}), 500
```

## Querying with DuckDB

DuckDB can query Iceberg tables directly from GCS:

```python
import duckdb
from pipeline_tasks.io.iceberg_catalog import get_table_path

# Get metadata location
metadata_location = get_table_path("pend")

# Query with DuckDB
conn = duckdb.connect()
result = conn.execute(f"""
    SELECT * 
    FROM read_iceberg('{metadata_location}')
    WHERE region = 'SIN' AND market = 'MDA'
    LIMIT 100
""").fetchdf()

print(result)
```

**Note**: Requires DuckDB with Iceberg extension installed.

## Querying from Local Projects

### Setup

1. Install dependencies:
```bash
pip install pyiceberg[gcp,pandas,pyarrow]
```

2. Authenticate with GCP:
```bash
gcloud auth application-default login
```

3. Use the catalog or direct paths:

```python
# Option 1: Use file-based catalog (if you have access to the catalog file)
from pipeline_tasks.io.iceberg_catalog import get_table_path
from pipeline_tasks.io.iceberg import load_table_from_gcs_path

metadata_location = get_table_path("pend")
table = load_table_from_gcs_path(metadata_location)

# Option 2: Use direct GCS path (if you know the metadata location)
table = load_table_from_gcs_path("gs://lakehouse_phoenix/pend/metadata/00000-abc123.metadata.json")
```

## Finding Latest Metadata Location

If you need to find the latest metadata file for a table:

```python
from pipeline_tasks.io.iceberg_catalog import find_latest_metadata_location

table_base_path = "gs://lakehouse_phoenix/pend"
metadata_location = find_latest_metadata_location(table_base_path)

if metadata_location:
    print(f"Latest metadata: {metadata_location}")
```

## Common Query Patterns

### Get Latest Timestamp

```python
from pipeline_tasks.io.iceberg import load_table_by_name
import pandas as pd

table = load_table_by_name("pend")
df = table.scan(
    row_filter="region = 'SIN' AND market = 'MDA'",
    selected_fields=("timestamp",)
).to_pandas()

latest_ts = df['timestamp'].max()
print(f"Latest timestamp: {latest_ts}")
```

### Get Data for Specific Time Range

```python
table = load_table_by_name("pend")
df = table.scan(
    row_filter="region = 'SIN' AND market = 'MDA' AND timestamp >= '2024-01-01' AND timestamp < '2024-02-01'"
).to_pandas()
```

### Get Distinct Values

```python
table = load_table_by_name("pend")
df = table.scan(selected_fields=("region", "market")).to_pandas()
distinct_regions = df['region'].unique()
```

## Performance Tips

1. **Use filters**: Always filter at the Iceberg level, not in pandas
2. **Select specific fields**: Use `selected_fields` to only read needed columns
3. **Use DuckDB for large queries**: DuckDB is more efficient for complex queries
4. **Cache catalog**: The file-based catalog is cached, but you can cache table objects too

## Troubleshooting

### Table Not Found

If you get "Table not found" errors:
1. Check that the table exists in `catalogues/iceberg_catalog.json`
2. Verify the GCS path is correct
3. Ensure you have GCP authentication set up

### Authentication Errors

Make sure you're authenticated:
```bash
gcloud auth application-default login
```

### Metadata Location Not Found

If metadata location can't be found:
1. Check that the table was written successfully
2. Verify GCS bucket permissions
3. Try finding metadata manually using `find_latest_metadata_location()`

