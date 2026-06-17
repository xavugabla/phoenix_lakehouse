# Contracts Core - Contract-Governed Control Layer

A Python-first framework for dataset governance that enforces contracts, validates parameters, and provides a unified interface for dataset execution.

## Overview

`contracts_core` provides a contract-governed control layer for datasets with:

- **Dataset Contracts in YAML**: Define parameters, schemas, partitioning, and storage paths once
- **Runtime Parameter Validation**: Ensure all parameters meet contract specifications
- **Contract-Defined Paths**: Storage paths generated from contracts, no hardcoding
- **Legacy Script Wrapper**: Execute existing scripts under governance
- **Run Manifests**: Track every dataset run with full metadata

## Key Features

✅ **Single Source of Truth**: All dataset metadata in one YAML contract  
✅ **Parameter Enforcement**: Validate types, required fields, and allowed values  
✅ **Path Governance**: Generate storage paths strictly from contracts  
✅ **Legacy-Friendly**: Wrap existing scripts without modification  
✅ **Manifest Tracking**: Full audit trail for every run  
✅ **Multi-Repository**: Import in any project for consistent behavior  

## Installation

```bash
# From the main repository
pip install -e .

# Or install just this package
pip install pydantic PyYAML
```

## Quick Start

### 1. Define a Dataset Contract

Create a YAML contract in `contracts_core/contracts/`:

```yaml
# my_dataset.yaml
dataset_id: my_dataset
version: "1.0.0"

params:
  - name: region
    type: string
    required: true
    allowed_values: ["US", "EU", "APAC"]
  
  - name: date
    type: string
    required: true

schema:
  columns:
    - name: id
      type: string
    - name: value
      type: double

partitioning:
  keys: ["region"]

storage:
  bronze: "bronze/my_domain/my_dataset"
  silver: "silver/my_domain/my_dataset"
  gold: "gold/my_domain/my_dataset_aggregated"

source:
  type: legacy_script
  script_path: "scripts/legacy/extract_my_dataset.py"
```

### 2. Run the Dataset

```python
from contracts_core import run_dataset

result = run_dataset(
    dataset_id="my_dataset",
    params={
        "region": "US",
        "date": "2024-01-15"
    }
)

print(f"Run ID: {result['run_id']}")
print(f"Status: {result['status']}")
print(f"Paths: {result['output_paths']}")
print(f"Manifest: {result['manifest_location']}")
```

### 3. Check the Results

The framework will:
1. Load and validate the contract
2. Validate your parameters
3. Generate the output paths
4. Execute your script (if source type is `legacy_script`)
5. Write a manifest with all run metadata

## Dataset Contract Structure

A dataset contract defines all governance rules for a dataset:

```yaml
dataset_id: unique_identifier       # Required: Unique dataset ID
version: "1.0.0"                    # Required: Contract version

# Runtime parameters
params:
  - name: param_name                # Parameter identifier
    type: string                    # string, integer, double, boolean, date, timestamp
    required: true                  # Is this parameter required?
    allowed_values: ["A", "B"]      # Optional: Allowed values list
    description: "Description"      # Optional: Human-readable description

# Expected schema
schema:
  columns:
    - name: column_name
      type: string                  # PyIceberg/Iceberg types

# Partitioning strategy (Hive-style)
partitioning:
  keys: ["key1", "key2"]            # Ordered partition keys

# Storage paths (zone paths)
storage:
  bronze: "bronze/domain/dataset"   # Raw/minimally transformed
  silver: "silver/domain/dataset"   # Cleaned, normalized
  gold: "gold/domain/aggregated"    # Features, metrics, results

# Source configuration
source:
  type: legacy_script               # legacy_script, cenace_api, etc.
  script_path: "path/to/script.py"  # For legacy_script type
  description: "Description"        # Optional: Source description
```

## Public API

### `run_dataset(dataset_id, params, **kwargs)`

Main entry point for running a dataset under governance.

**Arguments:**
- `dataset_id` (str): Unique identifier for the dataset
- `params` (dict): Runtime parameters
- `base_path` (str, optional): Base path for storage (default: env var or `./data`)
- `manifest_path` (str, optional): Path for manifests (default: env var or `./manifests`)
- `zone` (str, optional): Target zone (default: `"bronze"`)

**Returns:**
Dictionary with:
- `run_id`: Unique run identifier
- `output_paths`: Dictionary of storage paths for bronze/silver/gold
- `manifest_location`: Path to the run manifest
- `status`: "success" or "failed"
- `error`: Error message if failed (optional)

**Example:**
```python
result = run_dataset(
    dataset_id="cenace_pml",
    params={
        "market": "MDA",
        "region": "BCA",
        "start_date": "2024-01-01",
        "end_date": "2024-01-31"
    }
)
```

### `load_contract(dataset_id)`

Load a dataset contract.

**Arguments:**
- `dataset_id` (str): Dataset identifier

**Returns:**
- `DatasetContract`: Validated contract object

### `list_available_contracts()`

List all available dataset contracts.

**Returns:**
- `List[str]`: List of dataset IDs

## Legacy Script Integration

Legacy scripts receive parameters via command-line arguments:

```bash
./script.py --param1 value1 --param2 value2 --output /path/to/output --run-id RUN_ID
```

**Example Legacy Script:**

```python
#!/usr/bin/env python3
import argparse
import json
from pathlib import Path

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--region", type=str, required=True)
    parser.add_argument("--date", type=str, required=True)
    parser.add_argument("--output", type=str, required=True)
    parser.add_argument("--run-id", type=str, required=True)
    
    args = parser.parse_args()
    
    # Extract data
    data = extract_data(args.region, args.date)
    
    # Write to contract-defined path
    output_dir = Path(args.output)
    output_dir.mkdir(parents=True, exist_ok=True)
    
    output_file = output_dir / f"data_{args.run_id}.json"
    with open(output_file, 'w') as f:
        json.dump(data, f)
    
    return 0

if __name__ == "__main__":
    sys.exit(main())
```

**Key Points:**
- Legacy scripts don't choose paths - the framework does
- Scripts receive `--output` and `--run-id` automatically
- Scripts write to the provided output path
- Exit code 0 = success, non-zero = failure

## Run Manifests

Every run generates a manifest with complete metadata:

```json
{
  "run_id": "20240115_143022_abc123",
  "dataset_id": "my_dataset",
  "contract_version": "1.0.0",
  "params": {
    "region": "US",
    "date": "2024-01-15"
  },
  "paths": {
    "bronze": "/data/bronze/my_domain/my_dataset",
    "silver": "/data/silver/my_domain/my_dataset",
    "gold": "/data/gold/my_domain/my_dataset_aggregated"
  },
  "start_time": "2024-01-15T14:30:22.123456",
  "end_time": "2024-01-15T14:32:45.789012",
  "status": "success",
  "error": null,
  "metadata": {
    "stdout": "...",
    "record_count": 1000
  }
}
```

## Configuration

### Environment Variables

- `CONTRACTS_CORE_BASE_PATH`: Default base path for storage (default: `./data`)
- `CONTRACTS_CORE_MANIFEST_PATH`: Default path for manifests (default: `./manifests`)

### Example Setup

```bash
export CONTRACTS_CORE_BASE_PATH="gs://my-bucket"
export CONTRACTS_CORE_MANIFEST_PATH="gs://my-bucket/manifests"
```

## Adding a New Dataset

1. **Create a contract YAML** in `contracts_core/contracts/`
2. **Validate it** by running `list_available_contracts()`
3. **Test it** with `run_dataset()`
4. **Add a legacy script** if source type is `legacy_script`

That's it! No code changes needed in the framework.

## Module Reference

### `loader.py`
- Load and validate dataset contracts from YAML
- Contract validation with Pydantic models
- Contract caching

### `params.py`
- Runtime parameter validation
- Type conversion and checking
- Allowed values enforcement

### `paths.py`
- Storage path generation from contracts
- Partitioned path creation (Hive-style)
- No hardcoded paths

### `manifest.py`
- Run manifest creation
- Manifest persistence
- Status tracking (running, success, failed)

## Design Principles

1. **Contract-First**: All governance rules in YAML contracts
2. **No Hardcoding**: Paths, schemas, and params come from contracts
3. **Legacy-Friendly**: Wrap existing scripts without modification
4. **Audit Trail**: Full manifest for every run
5. **Multi-Repository**: Import anywhere for consistent behavior
6. **Python-First**: No external services or orchestration tools

## Testing

Run the test suite:

```bash
python test_contracts_core.py
```

Tests cover:
- Contract loading and validation
- Parameter validation
- Path generation
- Legacy script execution
- Manifest creation

## Success Criteria

✅ **Adding a dataset = adding a YAML contract**  
✅ **Multiple repos can import for identical behavior**  
✅ **Legacy scripts work under governance**  
✅ **No hardcoded paths or parameters**  
✅ **Full audit trail via manifests**  

## Examples

See:
- `contracts/cenace_pml.yaml` - API-based dataset contract
- `contracts/node_master.yaml` - Legacy script dataset contract
- `scripts/legacy/extract_node_master.py` - Example legacy script
- `test_contracts_core.py` - Complete test examples

## License

Proprietary - Part of phoenix_lakehouse
