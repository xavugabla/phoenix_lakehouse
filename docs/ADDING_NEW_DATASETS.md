# Adding New Datasets to the Lakehouse

This guide explains how to add new datasets while maintaining lakehouse standards and consistency.

## Overview

When adding a new dataset, you must:
1. **Define table contracts** in `configs/tables/{domain}.yaml`
2. **Follow naming conventions** and structure standards
3. **Define schemas** in consuming repo (data-pipeline, etc.)
4. **Verify** the contract follows lakehouse standards
5. **Test** table creation and access

## Step-by-Step Process

### Step 1: Determine Dataset Domain

**Question:** What domain does this dataset belong to?

- **CENACE** → `configs/tables/cenace.yaml`
- **Weather** → `configs/tables/weather.yaml`
- **Revenue** → `configs/tables/revenue.yaml`
- **New domain?** → Create `configs/tables/{domain}.yaml`

**Example:**
- Energy prices → `cenace` domain
- Weather observations → `weather` domain
- Revenue simulations → `revenue` domain

### Step 2: Determine Zone

**Question:** What zone does this dataset belong to?

| Zone | Purpose | Data State |
|------|---------|------------|
| `raw` | Immutable source data | As-received (JSON, XML, CSV) |
| `bronze` | Minimally transformed | Parquet, ready for Iceberg |
| `silver` | Cleaned/normalized | Validated, deduplicated |
| `gold` | Features/metrics/results | Aggregated, business-ready |

**Guidelines:**
- **Raw**: Original API responses, file uploads
- **Bronze**: First structured format (Parquet), minimal cleaning
- **Silver**: Cleaned data, ready for analytics
- **Gold**: Aggregated metrics, ML features, business results

### Step 3: Define Table Contract

Create or edit `configs/tables/{domain}.yaml`:

```yaml
tables:
  {zone}.{table_name}:
    domain: "{domain}"
    zone: "{zone}"
    schema: "{table_name}_{zone}"  # Schema key (defined in consuming repo)
    partition_by: ["partition_key1", "partition_key2", ...]
    description: "Human-readable description of the dataset"
```

**Required Fields:**
- `domain`: Domain name (e.g., "cenace", "weather")
- `zone`: Zone name ("raw", "bronze", "silver", "gold")
- `schema`: Schema identifier (used in consuming repo)
- `partition_by`: List of partition keys (must exist in schema)

**Optional Fields:**
- `description`: Human-readable description

**Example:**
```yaml
# configs/tables/weather.yaml
tables:
  bronze.weather_observations:
    domain: "weather"
    zone: "bronze"
    schema: "weather_observations_bronze"
    partition_by: ["station_id", "year", "month"]
    description: "Hourly weather observations from NOAA stations"
```

### Step 4: Follow Naming Conventions

#### Table Names
- **Format:** `{zone}.{table_name}`
- **Case:** `snake_case` (lowercase with underscores)
- **Examples:**
  - ✅ `bronze.pend`
  - ✅ `silver.energy_prices_normalized`
  - ✅ `gold.revenue_simulations`
  - ❌ `Bronze.PEND` (wrong case)
  - ❌ `bronze-pend` (wrong separator)

#### Domain Names
- **Format:** `snake_case`, lowercase
- **Examples:** `cenace`, `weather`, `revenue`, `market_data`

#### Schema Keys
- **Format:** `{table_name}_{zone}`
- **Examples:** `pend_bronze`, `weather_observations_silver`

### Step 5: Define Partitioning Strategy

**Partitioning Guidelines:**

1. **Choose partition keys that:**
   - Are frequently used in WHERE clauses
   - Have reasonable cardinality (not too many unique values)
   - Are present in the data (not computed on-the-fly)

2. **Common patterns:**
   - **Time-based:** `["year", "month"]` or `["date"]`
   - **Geographic:** `["region", "zone"]` or `["country", "state"]`
   - **Entity-based:** `["market", "region", "node"]`
   - **Hybrid:** `["market", "region", "year", "month"]`

3. **Avoid:**
   - High-cardinality fields (e.g., `timestamp`, `id`)
   - Fields with too many nulls
   - Computed/derived fields not in source data

**Example:**
```yaml
partition_by: ["market", "region", "zone", "year"]  # ✅ Good
partition_by: ["timestamp", "id"]  # ❌ Bad (too granular)
```

### Step 6: Define Schema in Consuming Repo

**In data-pipeline repo (or other consuming repo):**

Create `{repo}/schemas/{domain}/{table_name}.py`:

```python
from pyiceberg.schema import Schema
from pyiceberg.types import (
    NestedField, StringType, TimestampType, DoubleType, IntegerType
)

{SCHEMA_NAME} = Schema(
    NestedField(1, "timestamp", TimestampType(), required=True),
    NestedField(2, "field1", StringType(), required=True),
    NestedField(3, "field2", DoubleType(), required=False),
    # ... more fields
    # Ensure partition_by fields are included!
    NestedField(10, "partition_key1", StringType(), required=True),
    NestedField(11, "partition_key2", IntegerType(), required=True),
)
```

**Critical:** All fields in `partition_by` must exist in the schema!

### Step 7: Validate Table Contract

Run validation to ensure the contract follows standards:

```python
# In phoenix_lakehouse repo
from lakehouse_core import get_lakehouse_config
from lakehouse_core.tables import get_table_contract, get_table_identifier

config = get_lakehouse_config()
table_name = "bronze.your_new_table"

# Check contract exists
contract = get_table_contract(table_name)
assert contract, f"Table contract not found: {table_name}"

# Check required fields
assert "domain" in contract, "Missing 'domain' field"
assert "zone" in contract, "Missing 'zone' field"
assert "schema" in contract, "Missing 'schema' field"
assert "partition_by" in contract, "Missing 'partition_by' field"
assert isinstance(contract["partition_by"], list), "partition_by must be a list"

# Check naming conventions
zone, table_base = table_name.split(".", 1)
assert zone in ["raw", "bronze", "silver", "gold"], f"Invalid zone: {zone}"
assert table_base == table_base.lower(), "Table name must be lowercase"
assert "_" in table_base or table_base.isalnum(), "Table name must be snake_case"

# Check identifier format
identifier = get_table_identifier(table_name)
assert len(identifier) == 2, "Identifier must be (namespace, table_name) tuple"

print("✅ Table contract validation passed")
```

### Step 8: Test Table Creation

**In consuming repo (data-pipeline):**

```python
from lakehouse_core.catalogs import get_iceberg_catalog
from lakehouse_core.tables import get_table_identifier, get_table_contract
from lakehouse_core.paths import get_full_gcs_path
from your_schemas import YOUR_SCHEMA

catalog = get_iceberg_catalog()
table_name = "bronze.your_new_table"
contract = get_table_contract(table_name)
identifier = get_table_identifier(table_name)
location = get_full_gcs_path(table_name)

# Create partition spec (helper function in consuming repo)
partition_spec = create_partition_spec(contract["partition_by"], YOUR_SCHEMA)

# Create table
table = catalog.create_table(
    identifier=identifier,
    schema=YOUR_SCHEMA,
    partition_spec=partition_spec,
    location=location,
)

print(f"✅ Table created: {table_name}")
print(f"   Location: {location}")
print(f"   Partitions: {contract['partition_by']}")
```

### Step 9: Verify Paths and Catalog

```python
from lakehouse_core.paths import zone_prefix, table_prefix, get_full_gcs_path

# Verify paths
zone_path = zone_prefix(contract["zone"])
table_path = table_prefix(table_name)
full_path = get_full_gcs_path(table_name)

print(f"Zone path: {zone_path}")
print(f"Table path: {table_path}")
print(f"Full GCS path: {full_path}")

# Expected format: gs://lakehouse_phoenix/{zone}/{domain}/{table_name}/
assert full_path.startswith("gs://lakehouse_phoenix/"), "Invalid GCS path"
assert contract["domain"] in full_path, "Domain not in path"
assert contract["zone"] in full_path, "Zone not in path"
```

## Standards Checklist

Before submitting a new dataset, verify:

### Contract Standards
- [ ] Table name follows `{zone}.{table_name}` format
- [ ] Table name is `snake_case` (lowercase with underscores)
- [ ] Domain name is lowercase, descriptive
- [ ] Zone is one of: `raw`, `bronze`, `silver`, `gold`
- [ ] Schema key follows `{table_name}_{zone}` pattern
- [ ] `partition_by` is a list of strings
- [ ] All partition keys exist in the schema
- [ ] Description is clear and informative

### Partitioning Standards
- [ ] Partition keys are frequently queried
- [ ] Partition keys have reasonable cardinality
- [ ] Partition keys exist in source data (not computed)
- [ ] Partition strategy supports common query patterns

### Schema Standards
- [ ] Schema defined in consuming repo
- [ ] All partition keys included in schema
- [ ] Required fields marked appropriately
- [ ] Data types match actual data
- [ ] Field names are descriptive

### Path Standards
- [ ] Path follows: `gs://{bucket}/{zone}/{domain}/{table_name}/`
- [ ] No hardcoded paths in consuming repo
- [ ] Uses `lakehouse_core.paths` functions

### Catalog Standards
- [ ] Table registered in Iceberg catalog
- [ ] Uses `lakehouse_core.catalogs.get_iceberg_catalog()`
- [ ] Table identifier uses `lakehouse_core.tables.get_table_identifier()`

## Common Mistakes to Avoid

### ❌ Wrong: Hardcoded Paths
```python
# DON'T DO THIS
table_location = "gs://lakehouse_phoenix/bronze/cenace/pend/"
```

### ✅ Right: Use lakehouse_core
```python
# DO THIS
from lakehouse_core.paths import get_full_gcs_path
table_location = get_full_gcs_path("bronze.pend")
```

### ❌ Wrong: Missing Partition Keys in Schema
```python
# Schema missing "year" field but partition_by includes it
partition_by: ["market", "region", "year"]  # ❌ "year" not in schema
```

### ✅ Right: Include All Partition Keys
```python
# Schema includes all partition keys
Schema(
    NestedField(1, "market", StringType(), required=True),
    NestedField(2, "region", StringType(), required=True),
    NestedField(3, "year", IntegerType(), required=True),  # ✅ Included
)
```

### ❌ Wrong: Inconsistent Naming
```yaml
tables:
  Bronze.PEND:  # ❌ Wrong case
    domain: "CENACE"  # ❌ Wrong case
```

### ✅ Right: Consistent Naming
```yaml
tables:
  bronze.pend:  # ✅ Lowercase
    domain: "cenace"  # ✅ Lowercase
```

## Validation Script

Create `scripts/validate_table_contract.py` in phoenix_lakehouse:

```python
"""
Validate a table contract follows lakehouse standards.
"""
import sys
from lakehouse_core import get_lakehouse_config
from lakehouse_core.tables import get_table_contract, get_table_identifier

def validate_table_contract(table_name: str) -> bool:
    """Validate table contract follows standards."""
    config = get_lakehouse_config()
    contract = get_table_contract(table_name)
    
    if not contract:
        print(f"❌ Table contract not found: {table_name}")
        return False
    
    errors = []
    
    # Check required fields
    for field in ["domain", "zone", "schema", "partition_by"]:
        if field not in contract:
            errors.append(f"Missing required field: {field}")
    
    # Check zone is valid
    if contract.get("zone") not in ["raw", "bronze", "silver", "gold"]:
        errors.append(f"Invalid zone: {contract.get('zone')}")
    
    # Check partition_by is list
    if not isinstance(contract.get("partition_by"), list):
        errors.append("partition_by must be a list")
    
    # Check naming
    zone, table_base = table_name.split(".", 1)
    if table_base != table_base.lower():
        errors.append("Table name must be lowercase")
    
    if errors:
        print(f"❌ Validation failed for {table_name}:")
        for error in errors:
            print(f"   - {error}")
        return False
    
    print(f"✅ Table contract valid: {table_name}")
    return True

if __name__ == "__main__":
    table_name = sys.argv[1] if len(sys.argv) > 1 else "bronze.pend"
    validate_table_contract(table_name)
```

## Summary

**Adding a new dataset:**
1. Create/edit `configs/tables/{domain}.yaml`
2. Follow naming conventions
3. Define partitioning strategy
4. Define schema in consuming repo
5. Validate contract
6. Test table creation
7. Verify paths and catalog

**Key principle:** phoenix_lakehouse defines contracts and paths. Consuming repos define schemas and perform ETL.


