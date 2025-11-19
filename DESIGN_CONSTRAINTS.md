# Design Constraints & Compliance

This document verifies that phoenix_lakehouse adheres to its design constraints.

## ✅ Constraint 1: Pure Library (No ETL/APIs/Prefect)

**Status:** ✅ COMPLIANT

- ✅ No ETL logic in codebase
- ✅ No API calls or HTTP clients
- ✅ No Prefect imports or flows
- ✅ No data processing or transformation
- ✅ Only defines contracts and configuration

**Verification:**
```bash
# No ETL/API/Prefect references found in src/
grep -ri "prefect\|etl\|api\|http" src/  # Only "API" in docstrings
```

## ✅ Constraint 2: File-Based/Hadoop Catalog Only

**Status:** ✅ COMPLIANT

**Config (`configs/lakehouse.yaml`):**
```yaml
catalog:
  type: "hadoop"
  warehouse: "gs://lakehouse_phoenix/iceberg/"
```

**Implementation (`src/lakehouse_core/catalogs.py`):**
- ✅ Only supports `type: "hadoop"`
- ✅ Raises error if any other type is specified
- ✅ No BigQuery catalog code
- ✅ Uses `load_catalog()` with Hadoop type only

**Verification:**
- No `google-cloud-bigquery` dependency (removed)
- No BigQuery client instantiation
- Catalog type validation enforces "hadoop"

## ✅ Constraint 3: Modular Config Layout

**Status:** ✅ COMPLIANT

**Structure:**
```
configs/
├── lakehouse.yaml          # Core: bucket, prefix, zones, catalog
└── tables/
    ├── cenace.yaml         # Domain-specific table contracts
    ├── weather.yaml        # (when added)
    └── revenue.yaml         # (when added)
```

**Loading Logic (`src/lakehouse_core/config.py`):**
- ✅ Loads `configs/lakehouse.yaml` first
- ✅ Automatically loads all `configs/tables/*.yaml` files
- ✅ Merges tables: modular tables loaded first, then main config (main takes precedence)
- ✅ Error handling for duplicate table names

**Precedence Order:**
1. Modular tables (`configs/tables/*.yaml`) loaded first
2. Main config (`configs/lakehouse.yaml`) tables override modular on conflicts

## ✅ Constraint 4: Table Contracts Only

**Status:** ✅ COMPLIANT

**Allowed Fields in `configs/tables/*.yaml`:**
- ✅ `table_name` (e.g., `bronze.pend`)
- ✅ `domain` (e.g., `"cenace"`)
- ✅ `zone` (e.g., `"bronze"`)
- ✅ `schema` (schema key reference, e.g., `"pend_bronze"`)
- ✅ `partition_by` (list of partition keys)
- ✅ `description` (optional metadata)

**Not Allowed (and not present):**
- ❌ ETL logic
- ❌ Paths or file operations
- ❌ HTTP/API endpoints
- ❌ Pipeline details
- ❌ Data transformation rules

**Example (`configs/tables/cenace.yaml`):**
```yaml
tables:
  bronze.pend:
    domain: "cenace"           # ✅ Allowed
    zone: "bronze"              # ✅ Allowed
    schema: "pend_bronze"       # ✅ Allowed
    partition_by: ["market", "region", "zone", "year"]  # ✅ Allowed
    description: "..."           # ✅ Allowed (metadata)
```

## ✅ Constraint 5: Python API Surface

**Status:** ✅ COMPLIANT

**Exposed Functions:**

1. ✅ `get_lakehouse_config()` - Loads and returns config
   - Location: `src/lakehouse_core/config.py`
   - Returns: `LakehouseConfig` instance

2. ✅ `get_iceberg_catalog()` - Returns Hadoop catalog
   - Location: `src/lakehouse_core/catalogs.py`
   - Returns: PyIceberg `Catalog` instance (Hadoop type only)

3. ✅ `zone_prefix(zone)` - Get GCS zone prefix
   - Location: `src/lakehouse_core/paths.py`
   - Returns: Zone path string

4. ✅ `table_prefix(table_name)` - Get GCS table prefix
   - Location: `src/lakehouse_core/paths.py`
   - Returns: Table path string

5. ✅ `get_table_identifier(name)` - Convert to identifier tuple
   - Location: `src/lakehouse_core/tables.py`
   - Returns: `Identifier` tuple

6. ✅ `schemas` module - Column-level type definitions
   - Location: `src/lakehouse_core/schemas/`
   - Provides: PyIceberg schema utilities (no ETL)

**Package Exports (`src/lakehouse_core/__init__.py`):**
```python
from .config import get_lakehouse_config
from .catalogs import get_iceberg_catalog
from .tables import get_table_identifier
```

## Verification Checklist

- [x] No BigQuery catalog code
- [x] No ETL/transformation logic
- [x] No API/HTTP clients
- [x] No Prefect dependencies
- [x] Catalog type is "hadoop" only
- [x] Config layout is modular
- [x] Table contracts contain only allowed fields
- [x] Python API matches specification
- [x] All code respects library boundaries

## Boundary Enforcement

The codebase enforces boundaries through:

1. **Catalog Type Validation**: `catalogs.py` raises error if type != "hadoop"
2. **Config Structure**: Pydantic models validate allowed fields only
3. **No External Dependencies**: Removed BigQuery, Prefect, etc.
4. **Clear Separation**: Table contracts are pure metadata, no logic

## Maintenance

When adding new features, verify:
- ✅ Does it define contracts/config? → Allowed
- ✅ Does it perform ETL/processing? → NOT ALLOWED
- ✅ Does it use BigQuery as catalog? → NOT ALLOWED
- ✅ Does it call APIs or run flows? → NOT ALLOWED

