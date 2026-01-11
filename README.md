# Lakehouse Core

A minimal platform library for Apache Iceberg + GCS lakehouse architecture, now with contract-governed dataset execution.

## Purpose

This repository provides the **contracts and definitions** for a shared lakehouse platform:
- GCS storage layout definitions (raw/bronze/silver/gold zones)
- Iceberg catalog configuration (SQL catalog with SQLite for metadata)
- Table contracts: schemas, table names, namespaces, partitioning
- **Dataset governance framework (`contracts_core`)** for contract-based execution
- Minimal Python package exposing these definitions

## Packages

### 1. `lakehouse_core` - Platform Definitions
Defines storage layout, catalog configuration, and table contracts.

### 2. `contracts_core` - Dataset Governance (NEW!)
Contract-governed control layer for dataset execution with:
- Dataset contracts in YAML
- Runtime parameter validation
- Contract-defined storage paths
- Legacy script wrapper execution
- Run manifests for tracking

## What This Repo Does

✅ Defines where data lives in GCS (zone paths)  
✅ Configures the Iceberg catalog (SQL/SQLite for metadata)  
✅ Provides table contracts (names, zones, partitions)  
✅ **Governs dataset execution with contracts**  
✅ **Validates parameters and generates paths**  
✅ **Wraps legacy scripts under governance**  
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

### lakehouse_core - Platform Definitions

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

### contracts_core - Dataset Governance

```python
from contracts_core import run_dataset, list_available_contracts

# List available datasets
contracts = list_available_contracts()
print(f"Available: {contracts}")

# Run a dataset with governance
result = run_dataset(
    dataset_id="cenace_pml",
    params={
        "market": "MDA",
        "region": "BCA",
        "start_date": "2024-01-01",
        "end_date": "2024-01-31"
    }
)

print(f"Run ID: {result['run_id']}")
print(f"Status: {result['status']}")
print(f"Paths: {result['output_paths']}")
print(f"Manifest: {result['manifest_location']}")
```

See `examples_contracts_core.py` for more examples.

## Configuration

### Core Configuration

Edit `configs/lakehouse.yaml` to configure:
- GCS bucket and prefix
- Iceberg catalog (SQL/SQLite, URI and warehouse path)
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
- **Catalog**: SQL catalog (SQLite) for metadata, GCS warehouse for table data (`gs://lakehouse_phoenix/iceberg/`)
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

**Note:** BigQuery is not used as an Iceberg catalog in this repo. BigQuery may be used as a compute engine (via BigLake/external tables) in consuming repositories, but the catalog uses SQL (SQLite) for metadata storage.

## Dataset Governance with contracts_core

The `contracts_core` package provides contract-governed dataset execution:

### Key Features

- **YAML Contracts**: Define parameters, schemas, partitioning, and storage paths once
- **Parameter Validation**: Enforce types, required fields, and allowed values
- **Path Generation**: Storage paths generated from contracts (no hardcoding)
- **Legacy Scripts**: Wrap existing scripts without modification
- **Run Manifests**: Track every run with complete metadata

### Quick Start

1. **Create a dataset contract** in `src/contracts_core/contracts/`:
   ```yaml
   dataset_id: my_dataset
   version: "1.0.0"
   params:
     - name: region
       type: string
       required: true
   storage:
     bronze: "bronze/domain/dataset"
     silver: "silver/domain/dataset"
     gold: "gold/domain/dataset"
   source:
     type: legacy_script
     script_path: "scripts/legacy/extract.py"
   ```

2. **Run the dataset**:
   ```python
   from contracts_core import run_dataset
   
   result = run_dataset(
       dataset_id="my_dataset",
       params={"region": "US"}
   )
   ```

3. **Check results**: Manifest written with paths, timestamps, and status.

### Documentation

- **API Reference**: `src/contracts_core/README.md`
- **Integration Guide**: `docs/CONTRACTS_CORE_GUIDE.md`
- **Examples**: `examples_contracts_core.py`

### Benefits

✅ Adding a dataset = adding a YAML contract  
✅ Multiple repositories can import for identical behavior  
✅ Legacy scripts execute under governance  
✅ No hardcoded paths or parameters  

## License

Proprietary
