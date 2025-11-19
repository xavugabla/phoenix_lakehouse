# Data Migration Guide

This guide explains how to migrate existing data from `data_pipeline/data/` into the new lakehouse structure in GCS using `phoenix_lakehouse`.

## ⚠️ Important: Migration Location

**Migration code does NOT belong in phoenix_lakehouse repo.**

**phoenix_lakehouse is a pure library** - it defines contracts and paths, but does NOT:
- Run migrations
- Execute Prefect flows
- Perform ETL operations
- Use BigQuery as a catalog

The migration should be implemented in:
- `data-pipeline` repo (as a one-time migration script)
- Or a separate migration utility repo

`phoenix_lakehouse` provides the contracts and paths - you use it to know where to write.

## Migration Strategy

### Phase 1: Migrate Raw Data (Immutable)

**Source:** `data_pipeline/data/raw/cenace/`  
**Destination:** `gs://lakehouse_phoenix/raw/cenace/`

**Action:** Upload raw JSON files as-is, preserving structure for replay/debugging.

```python
# Example migration script (in data-pipeline repo)
from pathlib import Path
from google.cloud import storage
from lakehouse_core import get_lakehouse_config
from lakehouse_core.paths import zone_prefix

config = get_lakehouse_config()
raw_prefix = zone_prefix("raw")
# Result: "raw/" or "{prefix}/raw/"

# Upload raw files preserving structure
# raw/cenace/pend/sin/mda/zone=ACAPULCO/year=2025/{files}
# → gs://lakehouse_phoenix/raw/cenace/pend/sin/mda/zone=ACAPULCO/year=2025/{files}
```

### Phase 2: Migrate Consolidated Data to Bronze Iceberg Tables

**Source:** `data_pipeline/data/consolidated/` (Parquet files)  
**Destination:** Iceberg tables in `gs://lakehouse_phoenix/bronze/cenace/`

**Steps:**

1. **Read existing Parquet files**
2. **Create Iceberg tables** using `lakehouse_core` contracts
3. **Write data** to Iceberg tables
4. **Register in catalog**

## Migration Script Template

```python
"""
Migration script to move consolidated Parquet data to Iceberg tables.

This script should live in the data-pipeline repo, not phoenix_lakehouse.
It uses phoenix_lakehouse to get paths and catalog configuration.
"""
from pathlib import Path
import pandas as pd
import pyarrow as pa
from pyiceberg.partitioning import PartitionSpec, PartitionField
from pyiceberg.transforms import IdentityTransform

from lakehouse_core import get_lakehouse_config
from lakehouse_core.catalogs import get_iceberg_catalog
from lakehouse_core.tables import get_table_identifier, get_table_contract

# Import schemas from data-pipeline repo (domain-specific)
# from data_pipeline.schemas.pend import PEND_BRONZE_SCHEMA
# from data_pipeline.schemas.pml import PML_BRONZE_SCHEMA


def migrate_pend_to_iceberg():
    """Migrate PEND consolidated data to Iceberg bronze table."""
    config = get_lakehouse_config()
    catalog = get_iceberg_catalog()
    
    # Get table contract
    table_name = "bronze.pend"
    contract = get_table_contract(table_name)
    if not contract:
        raise ValueError(f"Table contract not found: {table_name}")
    
    # Get table identifier
    identifier = get_table_identifier(table_name)
    
    # Define schema (this should be in data-pipeline repo)
    # schema = PEND_BRONZE_SCHEMA
    
    # Create partition spec from contract
    partition_fields = [
        PartitionField(
            source_id=field_id,  # Field ID from schema
            field_id=partition_id,
            name=partition_key,
            transform=IdentityTransform(),
        )
        for partition_id, partition_key in enumerate(contract["partition_by"], start=1000)
    ]
    partition_spec = PartitionSpec(*partition_fields)
    
    # Create table if it doesn't exist
    try:
        table = catalog.load_table(identifier)
        print(f"Table {table_name} already exists, appending data...")
    except Exception:
        # Create new table
        # table_location = get_full_gcs_path(table_name)  # From paths module
        # catalog.create_table(
        #     identifier=identifier,
        #     schema=schema,
        #     partition_spec=partition_spec,
        #     location=table_location,
        # )
        print(f"Created table {table_name}")
        table = catalog.load_table(identifier)
    
    # Read consolidated Parquet files
    consolidated_path = Path("data/consolidated/pend/market=MDA/region=SIN")
    parquet_files = list(consolidated_path.rglob("*.parquet"))
    
    # Process each file
    for parquet_file in parquet_files:
        df = pd.read_parquet(parquet_file)
        
        # Extract partition values from path
        # e.g., "zone=ACAPULCO" -> zone="ACAPULCO"
        zone = parquet_file.parent.name.split("=")[1]
        
        # Add partition columns if not present
        if "zone" not in df.columns:
            df["zone"] = zone
        if "market" not in df.columns:
            df["market"] = "MDA"
        if "region" not in df.columns:
            df["region"] = "SIN"
        if "year" not in df.columns:
            df["year"] = df["timestamp"].dt.year
        
        # Convert to PyArrow table
        pa_table = pa.Table.from_pandas(df)
        
        # Append to Iceberg table
        table.append(pa_table)
        print(f"Appended {len(df)} rows from {parquet_file.name}")
    
    print(f"Migration complete for {table_name}")


def migrate_pml_to_iceberg():
    """Migrate PML consolidated data to Iceberg bronze table."""
    # Similar structure to migrate_pend_to_iceberg()
    # Use "bronze.pml" table contract
    pass


if __name__ == "__main__":
    migrate_pend_to_iceberg()
    migrate_pml_to_iceberg()
```

## Step-by-Step Migration Process

### 1. Install phoenix_lakehouse in data-pipeline repo

```bash
# In data-pipeline repo
pip install -e ../phoenix_lakehouse  # Or from git/pypi
```

### 2. Define Schemas in data-pipeline repo

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

### 3. Create Migration Script

Use the template above, customize for your data structure.

### 4. Run Migration

```bash
# In data-pipeline repo
python scripts/migrate_to_lakehouse.py
```

## Using lakehouse_core API

The migration script uses `phoenix_lakehouse` to:

1. **Get configuration:**
   ```python
   from lakehouse_core import get_lakehouse_config
   config = get_lakehouse_config()
   # Access: config.bucket, config.zones, config.catalog
   ```

2. **Get catalog:**
   ```python
   from lakehouse_core.catalogs import get_iceberg_catalog
   catalog = get_iceberg_catalog()
   # Use catalog.create_table(), catalog.load_table()
   ```

3. **Get paths:**
   ```python
   from lakehouse_core.paths import zone_prefix, table_prefix, get_full_gcs_path
   bronze_path = zone_prefix("bronze")  # "bronze/"
   table_path = table_prefix("bronze.pend")  # "bronze/cenace/pend/"
   full_path = get_full_gcs_path("bronze.pend")  # "gs://lakehouse_phoenix/bronze/cenace/pend/"
   ```

4. **Get table contracts:**
   ```python
   from lakehouse_core.tables import get_table_contract, get_table_identifier
   contract = get_table_contract("bronze.pend")
   # Access: contract["domain"], contract["partition_by"], etc.
   identifier = get_table_identifier("bronze.pend")  # ("bronze", "pend")
   ```

## Data Mapping

### PEND Data

**Source Structure:**
```
data/consolidated/pend/market=MDA/region=SIN/zone=ACAPULCO/data_2025.parquet
```

**Target Structure:**
```
gs://lakehouse_phoenix/
  bronze/
    cenace/
      pend/
        data/
          {snapshot}/
            {uuid}.parquet  # Iceberg-managed
        metadata/
          v1.metadata.json
```

**Partitioning:**
- Extract `year` from `timestamp` column
- Use partition keys: `["market", "region", "zone", "year"]`

### PML Data

**Source Structure:**
```
data/consolidated/pml/market=MDA/region=SIN/node=05ASC-115/data_2025.parquet
```

**Target Structure:**
```
gs://lakehouse_phoenix/
  bronze/
    cenace/
      pml/
        data/
          {snapshot}/
            {uuid}.parquet
        metadata/
          v1.metadata.json
```

**Partitioning:**
- Extract `year` from `timestamp` column
- Use partition keys: `["market", "region", "node", "year"]`

## Verification

After migration, verify tables:

```python
from lakehouse_core.catalogs import get_iceberg_catalog
from lakehouse_core.tables import get_table_identifier

catalog = get_iceberg_catalog()
identifier = get_table_identifier("bronze.pend")
table = catalog.load_table(identifier)

# Query data
df = table.scan().to_pandas()
print(f"Total rows: {len(df)}")
print(df.head())
```

## Notes

- **Raw data**: Upload as-is, no Iceberg tables needed
- **Consolidated data**: Migrate to Iceberg bronze tables
- **Staged data**: Skip (temporary processing)
- **Manifests**: Not needed (Iceberg tracks metadata)

## Next Steps

1. Create migration script in `data-pipeline` repo
2. Define schemas in `data-pipeline` repo
3. Run migration for PEND and PML
4. Verify data in GCS and via catalog
5. Update ingestion pipeline to write directly to Iceberg

