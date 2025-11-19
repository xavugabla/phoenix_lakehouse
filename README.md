# Lakehouse Core

A minimal platform library for Apache Iceberg + GCS lakehouse architecture.

## Purpose

This repository provides the **contracts and definitions** for a shared lakehouse platform:
- GCS storage layout definitions (raw/bronze/silver/gold zones)
- Iceberg catalog configuration (unified file-based/Hadoop catalog on GCS)
- Table contracts: schemas, table names, namespaces, partitioning
- Minimal Python package exposing these definitions

## What This Repo Does

✅ Defines where data lives in GCS (zone paths)  
✅ Configures the unified Iceberg catalog (file-based on GCS)  
✅ Provides table contracts (names, zones, partitions)  
✅ Exposes a clean Python API for consuming repositories  

## What This Repo Does NOT Do

❌ Run ingestion flows or ETL  
❌ Execute Prefect workflows  
❌ Store domain-specific schemas (those belong in consuming repos)  
❌ Write data to Iceberg (only table creation contracts)  
❌ Use BigQuery as an Iceberg catalog (BigQuery may be used as compute engine in other repos)  

## Installation

```bash
pip install -e .
```

## Usage

```python
from lakehouse_core import get_lakehouse_config
from lakehouse_core.catalogs import get_iceberg_catalog
from lakehouse_core.tables import get_table_identifier
from lakehouse_core.paths import zone_prefix, table_prefix

# Load configuration
cfg = get_lakehouse_config()

# Get catalog
catalog = get_iceberg_catalog()

# Get table identifier
identifier = get_table_identifier("bronze.your_table_name")

# Load table
table = catalog.load_table(identifier)

# Get GCS paths
zone_path = zone_prefix("bronze")
table_path = table_prefix("bronze.your_table_name")
```

## Configuration

### Core Configuration

Edit `configs/lakehouse.yaml` to configure:
- GCS bucket and prefix
- Iceberg catalog (file-based/Hadoop, warehouse path)
- Zone paths (raw/bronze/silver/gold)

### Table Contracts

Table contracts can be defined in two ways:

1. **Modular (Recommended)**: Create domain-specific files in `configs/tables/`
   ```yaml
   # configs/tables/cenace.yaml
   tables:
     bronze.pend:
       domain: "cenace"
       zone: "bronze"
       schema: "pend_bronze"
       partition_by: ["market", "region", "zone", "year"]
   ```

2. **Inline**: Add to `tables: {}` in `configs/lakehouse.yaml` (for small projects)

The modular approach scales better as you add more domains.

## Architecture

- **Storage**: GCS as the single data lake
- **Table Format**: Apache Iceberg
- **Catalog**: File-based/Hadoop-style catalog on GCS (warehouse: `gs://lakehouse_phoenix/iceberg/`)
- **Zones**: raw (immutable), bronze (minimal), silver (cleaned), gold (features/metrics)

This platform is domain-agnostic. Domain-specific schemas, datasets, and business logic belong in consuming repositories (data-pipeline, data-manager, revenue-models, etc.).

## Adding New Datasets

When adding a new dataset, follow the standards guide:

1. **Define table contract** in `configs/tables/{domain}.yaml`
2. **Follow naming conventions** (snake_case, lowercase)
3. **Define schema** in consuming repo
4. **Validate contract**: `python scripts/validate_table_contract.py bronze.your_table`
5. **Test table creation** in consuming repo

See `docs/ADDING_NEW_DATASETS.md` for complete guide and standards checklist.

**Note:** BigQuery is not used as an Iceberg catalog in this repo. BigQuery may be used as a compute engine (via BigLake/external tables) in consuming repositories, but the catalog is exclusively file-based on GCS.

## License

Proprietary
