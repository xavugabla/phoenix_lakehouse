# Contracts Core - Dataset Governance Framework

## Overview

The `contracts_core` package provides a contract-governed control layer for datasets, enabling a Python-first approach to dataset governance. This framework ensures that all datasets follow consistent patterns for parameters, paths, schemas, and execution.

## Purpose

In a lakehouse environment, datasets need governance to ensure:
- **Consistent Parameters**: All datasets validate runtime parameters
- **Standardized Paths**: Storage paths follow contract-defined patterns
- **Schema Enforcement**: Expected schemas are documented
- **Audit Trails**: Every run is tracked with full metadata
- **Legacy Integration**: Existing scripts work under governance

The `contracts_core` package achieves this by:
1. Defining dataset contracts in YAML (single source of truth)
2. Validating all inputs at runtime
3. Generating paths from contracts (no hardcoding)
4. Wrapping legacy scripts for execution
5. Emitting manifests for every run

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                      contracts_core                          │
│                                                              │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐     │
│  │   loader.py  │  │   params.py  │  │   paths.py   │     │
│  │              │  │              │  │              │     │
│  │ Load & Cache │  │  Validate    │  │  Generate    │     │
│  │  Contracts   │  │  Parameters  │  │   Paths      │     │
│  └──────────────┘  └──────────────┘  └──────────────┘     │
│                                                              │
│  ┌──────────────┐  ┌─────────────────────────────────┐    │
│  │ manifest.py  │  │      __init__.py                 │    │
│  │              │  │                                   │    │
│  │   Write      │  │    run_dataset()                 │    │
│  │  Manifests   │  │    (Public Interface)            │    │
│  └──────────────┘  └─────────────────────────────────┘    │
└─────────────────────────────────────────────────────────────┘
          │                            │
          ▼                            ▼
┌──────────────────────┐    ┌──────────────────────┐
│  Dataset Contracts   │    │   Legacy Scripts     │
│    (YAML files)      │    │  (Existing Code)     │
│                      │    │                      │
│  • cenace_pml.yaml   │    │  • extract_*.py      │
│  • node_master.yaml  │    │  • process_*.sh      │
│  • ...               │    │  • ...               │
└──────────────────────┘    └──────────────────────┘
```

## Key Concepts

### Dataset Contracts

A dataset contract is a YAML file that defines everything about a dataset:
- **Identity**: dataset_id, version
- **Parameters**: Name, type, required/optional, allowed values
- **Schema**: Expected columns and types
- **Partitioning**: Ordered partition keys (Hive-style)
- **Storage**: Path templates for bronze/silver/gold zones
- **Source**: Where data comes from (API, legacy script, etc.)

**Example:**
```yaml
dataset_id: cenace_pml
version: "1.0.0"
params:
  - name: market
    type: string
    required: true
    allowed_values: ["MDA", "MTR"]
partitioning:
  keys: ["market", "region", "node", "year"]
storage:
  bronze: "bronze/cenace/pml"
  silver: "silver/cenace/pml"
  gold: "gold/cenace/pml_aggregated"
source:
  type: cenace_api
```

### Parameter Validation

At runtime, all parameters are validated against the contract:
- **Required parameters** must be provided
- **Types** must match (string, integer, double, boolean, date, timestamp)
- **Allowed values** are enforced (if specified)

Invalid parameters are rejected before execution starts.

### Path Generation

Storage paths are generated from contracts, ensuring:
- **No hardcoded paths** in scripts or applications
- **Consistent structure** across all datasets
- **Zone-based organization** (bronze/silver/gold)
- **Partitioned paths** follow Hive-style conventions

**Example:**
```
Contract defines: "bronze/cenace/pml"
Parameters: market=MDA, region=BCA, year=2024
Generated path: /data/bronze/cenace/pml/market=MDA/region=BCA/year=2024
```

### Legacy Script Wrapper

Existing scripts can run under governance without modification:
1. Framework validates parameters
2. Framework generates the output path
3. Framework calls script with `--param1 value1 --output /path --run-id ID`
4. Script writes to the provided path
5. Framework captures exit code and output
6. Framework writes manifest

**Scripts don't choose paths** - the framework enforces them.

### Run Manifests

Every dataset run generates a JSON manifest:
- **Run metadata**: run_id, dataset_id, contract_version
- **Parameters**: All validated parameters used
- **Paths**: Generated storage paths
- **Timestamps**: Start and end times
- **Status**: success or failed
- **Error**: Error message if failed
- **Metadata**: Additional info (stdout, record counts, etc.)

Manifests provide a complete audit trail.

## Usage

### Basic Usage

```python
from contracts_core import run_dataset

# Run a dataset
result = run_dataset(
    dataset_id="cenace_pml",
    params={
        "market": "MDA",
        "region": "BCA",
        "start_date": "2024-01-01",
        "end_date": "2024-01-31"
    }
)

# Check result
print(f"Status: {result['status']}")
print(f"Paths: {result['output_paths']}")
print(f"Manifest: {result['manifest_location']}")
```

### List Available Datasets

```python
from contracts_core import list_available_contracts

contracts = list_available_contracts()
print(f"Available datasets: {contracts}")
```

### Load a Contract

```python
from contracts_core import load_contract

contract = load_contract("cenace_pml")
print(f"Version: {contract.version}")
print(f"Parameters: {[p.name for p in contract.params]}")
```

## Integration with lakehouse_core

The `contracts_core` package complements `lakehouse_core`:

- **lakehouse_core**: Defines storage layout, catalog, and table contracts
- **contracts_core**: Governs dataset execution, parameters, and paths

Both packages can be used together:
- Use `lakehouse_core` for Iceberg table definitions and catalog
- Use `contracts_core` for dataset ingestion governance

Or independently:
- `lakehouse_core` can be used without `contracts_core`
- `contracts_core` can be used without `lakehouse_core`

## Adding a New Dataset

1. **Create a contract** in `src/contracts_core/contracts/`:
   ```yaml
   # my_new_dataset.yaml
   dataset_id: my_new_dataset
   version: "1.0.0"
   # ... rest of contract
   ```

2. **Test it**:
   ```python
   from contracts_core import run_dataset
   result = run_dataset("my_new_dataset", params={...})
   ```

3. **Done!** No code changes needed.

## Environment Variables

Configure paths via environment variables:

```bash
# Base path for storage (default: ./data)
export CONTRACTS_CORE_BASE_PATH="gs://my-bucket"

# Path for manifests (default: ./manifests)
export CONTRACTS_CORE_MANIFEST_PATH="gs://my-bucket/manifests"
```

## Benefits

✅ **Governance Without Friction**: Legacy scripts work as-is  
✅ **Single Source of Truth**: All dataset rules in one YAML file  
✅ **No Hardcoding**: Paths and schemas come from contracts  
✅ **Full Audit Trail**: Every run tracked in manifests  
✅ **Multi-Repository**: Import in any project for consistency  
✅ **Python-First**: No external services or dependencies  

## Constraints

- No orchestration tools (Prefect, Airflow, etc.)
- No frontend modifications
- No extensive refactoring
- Python-first development
- Works with existing legacy scripts

## Examples

See:
- `src/contracts_core/contracts/cenace_pml.yaml` - API dataset
- `src/contracts_core/contracts/node_master.yaml` - Legacy script dataset
- `scripts/legacy/extract_node_master.py` - Example legacy script
- `test_contracts_core.py` - Complete test examples

## Documentation

- **Package README**: `src/contracts_core/README.md` - Complete API reference
- **This Guide**: Overview and integration guide
- **Contracts**: `src/contracts_core/contracts/*.yaml` - Example contracts

## Testing

```bash
# Run the test suite
python test_contracts_core.py
```

Tests validate:
- Contract loading
- Parameter validation
- Path generation
- Legacy script execution
- Manifest creation

## Future Extensions

Possible future enhancements:
- API client templates for different source types
- Data quality checks in contracts
- Schema evolution tracking
- Multi-zone execution in a single run
- Retry and failure handling policies
- Contract versioning and migration

## License

Proprietary - Part of phoenix_lakehouse
