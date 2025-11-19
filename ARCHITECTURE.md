# Lakehouse Core Architecture

## Overview

This repository defines the **contracts and layout** for a shared Apache Iceberg + GCS lakehouse platform. It provides a minimal Python library that consuming repositories (data-pipeline, data-manager, revenue-models) import to know where data lives and how to access it.

## Core Components

### 1. Configuration (`config.py`)

- Loads and validates `configs/lakehouse.yaml`
- Exposes `get_lakehouse_config()` function
- Provides Pydantic models for type safety

### 2. Catalog (`catalogs.py`)

- **Unified Catalog: File-based/Hadoop-style on GCS**
- Exposes `get_iceberg_catalog()` function
- Returns configured PyIceberg Catalog instance
- Single source of truth for table metadata
- All metadata stored in GCS under warehouse path: `gs://lakehouse_phoenix/iceberg/`

**Note:** BigQuery is **not** used for catalog management in this repo. BigQuery may be used as a compute engine (via BigLake/external tables) in consuming repositories, but it is not part of the catalog system here.

### 3. Paths (`paths.py`)

- `zone_prefix(zone)` - Get GCS prefix for a zone
- `table_prefix(table_name)` - Get GCS prefix for a table
- `get_full_gcs_path(table_name)` - Get full GCS path
- Ensures no hardcoded paths in consuming repos

### 4. Tables (`tables.py`)

- `get_table_identifier(name)` - Convert "bronze.table" to identifier tuple
- `get_table_contract(table_name)` - Get table contract from config
- Convenience functions for table operations

### 5. Schemas (`schemas/`)

- Generic schema utilities (PyIceberg types)
- Domain-specific schemas belong in consuming repositories

## Configuration Structure

### Core Configuration (`configs/lakehouse.yaml`)

```yaml
bucket: "lakehouse_phoenix"
prefix: ""
zones:
  raw: "raw"
  bronze: "bronze"
  silver: "silver"
  gold: "gold"
catalog:
  type: "hadoop"
  warehouse: "gs://lakehouse_phoenix/iceberg/"
tables: {}  # Can be inline or loaded from modular files
```

### Modular Table Contracts (`configs/tables/*.yaml`)

Table contracts are organized by domain in separate files:

```
configs/tables/
├── cenace.yaml      # CENACE energy data
├── weather.yaml     # Weather observations
└── revenue.yaml     # Revenue modeling
```

Each file contains domain-specific table contracts:

```yaml
# configs/tables/cenace.yaml
tables:
  bronze.pend:
    domain: "cenace"
    zone: "bronze"
    schema: "pend_bronze"
    partition_by: ["market", "region", "zone", "year"]
```

**Benefits:**
- **Modular**: Each domain is self-contained
- **Scalable**: Add domains without touching existing configs
- **Maintainable**: Clear separation, easy to find/edit
- **Version Control**: Clean git diffs per domain

## API Surface

The package exposes a minimal API:

```python
from lakehouse_core import get_lakehouse_config
from lakehouse_core.catalogs import get_iceberg_catalog
from lakehouse_core.tables import get_table_identifier
from lakehouse_core.paths import zone_prefix, table_prefix

# Get config
cfg = get_lakehouse_config()

# Get catalog
catalog = get_iceberg_catalog()

# Get table identifier
identifier = get_table_identifier("bronze.example_table")

# Load table
table = catalog.load_table(identifier)

# Get paths
zone_path = zone_prefix("bronze")
table_path = table_prefix("bronze.example_table")
```

## Catalog Decision

**File-based/Hadoop-style catalog on GCS** is the unified catalog for all Iceberg table metadata. This provides:
- Single source of truth stored in GCS
- No external catalog service dependencies
- All metadata (snapshots, schemas, manifests) under warehouse path
- Simple, portable catalog structure

The warehouse path `gs://lakehouse_phoenix/iceberg/` contains:
- Table metadata files
- Schema definitions
- Snapshot manifests
- All Iceberg catalog metadata

BigQuery is expressly out-of-scope for catalog management in this repo. It may be used in consuming repositories as a compute engine, but not as an Iceberg catalog.

## Storage Layout

GCS bucket structure:
```
gs://lakehouse_phoenix/
  iceberg/        # Iceberg catalog metadata (warehouse)
  raw/            # Immutable source data
  bronze/         # Minimally transformed
  silver/         # Cleaned, normalized
  gold/           # Features, metrics, results
```

Each zone can have domain subdirectories based on table contracts.

## Dependencies

Core runtime dependencies:
- `PyYAML` - Config parsing
- `google-cloud-storage` - GCS access for catalog and data
- `google-auth` - GCP authentication
- `pydantic` - Config validation
- `pyiceberg[gcp]` - Iceberg operations with GCS support

See `requirements.txt` and `pyproject.toml` for full list.

## Setup

See `SETUP.md` for detailed setup instructions. Quick start:

```powershell
.\setup.ps1
```

## Next Steps

1. Define table contracts in `configs/lakehouse.yaml` as datasets are introduced
2. Consuming repos import this package and use the API
3. Domain-specific schemas defined in consuming repos
4. All data operations use this platform's contracts
