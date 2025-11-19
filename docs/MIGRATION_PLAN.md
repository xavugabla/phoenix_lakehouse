# Migration Plan: data_pipeline → phoenix_lakehouse

## Important Context

**phoenix_lakehouse is a pure library** - it does NOT run migrations, Prefect flows, or ETL.

**Migration work happens in the data-pipeline repo** using phoenix_lakehouse as a dependency.

## Current State

### phoenix_lakehouse (This Repo)
- ✅ Pure library: defines contracts, paths, catalog
- ✅ File-based/Hadoop catalog on GCS
- ✅ No ETL, no Prefect, no BigQuery catalog
- ✅ Table contracts defined in `configs/tables/cenace.yaml`

### data_pipeline (Source Data)
- ✅ Has consolidated Parquet files: `data/consolidated/pend/`, `data/consolidated/pml/`
- ✅ Has raw JSON files: `data/raw/cenace/`
- ❌ Needs migration scripts (to be created)

## Migration Strategy

### Phase 1: Setup & Verification

**In phoenix_lakehouse repo:**
```bash
# 1. Verify installation
pip install -e .

# 2. Verify config loads
python -c "from lakehouse_core import get_lakehouse_config; print(get_lakehouse_config())"

# 3. Verify catalog initializes
python -c "from lakehouse_core.catalogs import get_iceberg_catalog; cat = get_iceberg_catalog(); print('Catalog OK')"

# 4. Verify table contracts exist
python -c "from lakehouse_core.tables import get_table_contract; print(get_table_contract('bronze.pend'))"
```

**In data-pipeline repo:**
```bash
# 1. Install phoenix_lakehouse as dependency
pip install -e ../phoenix_lakehouse  # Or from git/pypi

# 2. Verify GCP credentials
echo $env:GOOGLE_APPLICATION_CREDENTIALS  # Windows
# Should point to service account JSON

# 3. Verify GCS bucket access
python -c "from google.cloud import storage; client = storage.Client(); print(list(client.list_buckets()))"
```

### Phase 2: Create Migration Scripts (in data-pipeline repo)

Create `data_pipeline/scripts/migrate_to_lakehouse.py`:

```python
"""
Migration script to move consolidated Parquet → Iceberg bronze tables.

This script lives in data-pipeline repo and uses phoenix_lakehouse.
"""
from pathlib import Path
import pandas as pd
import pyarrow as pa
from pyiceberg.partitioning import PartitionSpec, PartitionField
from pyiceberg.transforms import IdentityTransform

# Use phoenix_lakehouse
from lakehouse_core import get_lakehouse_config
from lakehouse_core.catalogs import get_iceberg_catalog
from lakehouse_core.tables import get_table_identifier, get_table_contract
from lakehouse_core.paths import get_full_gcs_path

# Domain schemas (define in data-pipeline repo)
from data_pipeline.schemas.pend import PEND_BRONZE_SCHEMA
from data_pipeline.schemas.pml import PML_BRONZE_SCHEMA


def create_partition_spec(partition_keys: list, schema) -> PartitionSpec:
    """Create Iceberg partition spec from partition keys."""
    fields = []
    for idx, key in enumerate(partition_keys):
        # Find field ID in schema
        field = next((f for f in schema.fields if f.name == key), None)
        if not field:
            raise ValueError(f"Partition key '{key}' not found in schema")
        fields.append(
            PartitionField(
                source_id=field.field_id,
                field_id=1000 + idx,  # Partition field IDs
                name=key,
                transform=IdentityTransform(),
            )
        )
    return PartitionSpec(*fields)


def migrate_pend():
    """Migrate PEND consolidated data to Iceberg bronze table."""
    print("Starting PEND migration...")
    
    config = get_lakehouse_config()
    catalog = get_iceberg_catalog()
    
    table_name = "bronze.pend"
    contract = get_table_contract(table_name)
    if not contract:
        raise ValueError(f"Table contract not found: {table_name}")
    
    identifier = get_table_identifier(table_name)
    table_location = get_full_gcs_path(table_name)
    
    print(f"Table location: {table_location}")
    print(f"Partition keys: {contract['partition_by']}")
    
    # Create partition spec
    partition_spec = create_partition_spec(contract["partition_by"], PEND_BRONZE_SCHEMA)
    
    # Create table if it doesn't exist
    try:
        table = catalog.load_table(identifier)
        print(f"Table {table_name} already exists, will append data...")
    except Exception:
        print(f"Creating table {table_name}...")
        table = catalog.create_table(
            identifier=identifier,
            schema=PEND_BRONZE_SCHEMA,
            partition_spec=partition_spec,
            location=table_location,
        )
        print(f"✅ Created table {table_name}")
    
    # Read consolidated Parquet files
    source_root = Path("data/consolidated/pend")
    parquet_files = list(source_root.rglob("*.parquet"))
    
    print(f"Found {len(parquet_files)} Parquet files to migrate")
    
    total_rows = 0
    for parquet_file in parquet_files:
        # Extract partition values from path
        # e.g., "market=MDA/region=SIN/zone=ACAPULCO/data_2025.parquet"
        path_parts = parquet_file.parts
        
        market = None
        region = None
        zone = None
        
        for part in path_parts:
            if part.startswith("market="):
                market = part.split("=")[1]
            elif part.startswith("region="):
                region = part.split("=")[1]
            elif part.startswith("zone="):
                zone = part.split("=")[1]
        
        # Read Parquet file
        df = pd.read_parquet(parquet_file)
        
        # Add partition columns if not present
        if "market" not in df.columns and market:
            df["market"] = market
        if "region" not in df.columns and region:
            df["region"] = region
        if "zone" not in df.columns and zone:
            df["zone"] = zone
        if "year" not in df.columns:
            df["year"] = df["timestamp"].dt.year
        
        # Convert to PyArrow
        pa_table = pa.Table.from_pandas(df)
        
        # Append to Iceberg table
        table.append(pa_table)
        total_rows += len(df)
        print(f"  ✅ Migrated {len(df)} rows from {parquet_file.name}")
    
    print(f"✅ PEND migration complete: {total_rows} total rows")


def migrate_pml():
    """Migrate PML consolidated data to Iceberg bronze table."""
    print("Starting PML migration...")
    
    # Similar to migrate_pend() but for PML
    # Use "bronze.pml" table contract
    # Extract "node" instead of "zone" from path
    pass


if __name__ == "__main__":
    migrate_pend()
    migrate_pml()
```

### Phase 3: Define Schemas (in data-pipeline repo)

Create `data_pipeline/schemas/pend.py`:

```python
from pyiceberg.schema import Schema
from pyiceberg.types import NestedField, StringType, TimestampType, DoubleType

PEND_BRONZE_SCHEMA = Schema(
    NestedField(1, "timestamp", TimestampType(), required=True),
    NestedField(2, "zone", StringType(), required=True),
    NestedField(3, "pz", DoubleType(), required=False),
    NestedField(4, "pz_ene", DoubleType(), required=False),
    NestedField(5, "pz_per", DoubleType(), required=False),
    NestedField(6, "pz_cng", DoubleType(), required=False),
    NestedField(7, "market", StringType(), required=True),
    NestedField(8, "region", StringType(), required=True),
)
```

Create `data_pipeline/schemas/pml.py`:

```python
from pyiceberg.schema import Schema
from pyiceberg.types import NestedField, StringType, TimestampType, DoubleType

PML_BRONZE_SCHEMA = Schema(
    NestedField(1, "timestamp", TimestampType(), required=True),
    NestedField(2, "node", StringType(), required=True),
    NestedField(3, "pml", DoubleType(), required=False),
    NestedField(4, "pml_ene", DoubleType(), required=False),
    NestedField(5, "pml_per", DoubleType(), required=False),
    NestedField(6, "pml_cng", DoubleType(), required=False),
    NestedField(7, "market", StringType(), required=True),
    NestedField(8, "region", StringType(), required=True),
)
```

### Phase 4: Run Migration

**In data-pipeline repo:**

```bash
# 1. Test with one file first
python scripts/migrate_to_lakehouse.py --dry-run

# 2. Run full migration
python scripts/migrate_to_lakehouse.py

# 3. Verify data
python -c "
from lakehouse_core.catalogs import get_iceberg_catalog
from lakehouse_core.tables import get_table_identifier

catalog = get_iceberg_catalog()
table = catalog.load_table(get_table_identifier('bronze.pend'))
df = table.scan().to_pandas()
print(f'Total rows: {len(df)}')
print(df.head())
"
```

### Phase 5: Migrate Raw Data (Optional)

Upload raw JSON files to GCS for replay/debugging:

```python
# Simple upload script (in data-pipeline repo)
from pathlib import Path
from google.cloud import storage
from lakehouse_core.paths import zone_prefix

config = get_lakehouse_config()
raw_prefix = zone_prefix("raw")  # "raw/"

client = storage.Client()
bucket = client.bucket(config.bucket)

source_root = Path("data/raw/cenace")
for json_file in source_root.rglob("*.json"):
    # Preserve relative path structure
    relative_path = json_file.relative_to(source_root)
    blob_path = f"{raw_prefix}cenace/{relative_path}"
    
    blob = bucket.blob(blob_path)
    blob.upload_from_filename(str(json_file))
    print(f"Uploaded {blob_path}")
```

## Verification Steps

### 1. Verify Tables Exist

```python
from lakehouse_core.catalogs import get_iceberg_catalog
from lakehouse_core.tables import get_table_identifier

catalog = get_iceberg_catalog()

# List namespaces
namespaces = catalog.list_namespaces()
print(f"Namespaces: {namespaces}")

# Load tables
pend_table = catalog.load_table(get_table_identifier("bronze.pend"))
pml_table = catalog.load_table(get_table_identifier("bronze.pml"))

print("✅ Tables exist and are accessible")
```

### 2. Verify Data

```python
# Query sample data
df = pend_table.scan(limit=10).to_pandas()
print(f"Sample rows: {len(df)}")
print(df.head())

# Verify partitions
df = pend_table.scan(
    row_filter="market = 'MDA' AND region = 'SIN' AND zone = 'ACAPULCO'"
).to_pandas()
print(f"Filtered rows: {len(df)}")
```

### 3. Verify GCS Structure

```bash
# Check GCS bucket structure
gsutil ls gs://lakehouse_phoenix/bronze/cenace/
gsutil ls gs://lakehouse_phoenix/iceberg/  # Catalog metadata
```

## What phoenix_lakehouse Provides

✅ **Table contracts** - From `configs/tables/cenace.yaml`  
✅ **GCS paths** - Via `zone_prefix()`, `table_prefix()`, `get_full_gcs_path()`  
✅ **Catalog access** - Via `get_iceberg_catalog()` (Hadoop/file-based)  
✅ **Table identifiers** - Via `get_table_identifier()`  

## What phoenix_lakehouse Does NOT Provide

❌ Migration scripts (create in data-pipeline repo)  
❌ Prefect flows (belongs in data-pipeline repo)  
❌ Schema definitions (define in data-pipeline repo)  
❌ ETL logic (belongs in data-pipeline repo)  

## Key Differences from Old Approach

| Old (Removed) | New (Current) |
|---------------|---------------|
| `orchestration/utils/migrate_catalogs.py` | Migration script in data-pipeline repo |
| `orchestration/flows/migrate_local_to_lakehouse.py` | Migration script in data-pipeline repo |
| BigQuery catalog | File-based/Hadoop catalog only |
| Prefect flows in lakehouse repo | Prefect flows in data-pipeline repo |
| Examples/query scripts | Examples in data-pipeline repo |

## Next Steps

1. ✅ Table contracts already defined in `configs/tables/cenace.yaml`
2. ⏳ Create migration script in data-pipeline repo (use template above)
3. ⏳ Define schemas in data-pipeline repo
4. ⏳ Run migration
5. ⏳ Verify data in GCS and via catalog

