# Data Pipeline Analysis & Lakehouse Migration Plan

## Current Data Structure

### Location
`C:\Users\xavie\Finalboss\data_pipeline\data\`

### Directory Structure

```
data/
├── raw/                    # Raw source data (immutable)
│   └── cenace/
│       ├── pend/          # Energy prices by zone
│       │   └── sin/mda/zone={ZONE}/year=2025/{files}
│       └── pml/           # Locational marginal prices by node
│           └── sin/mda/node={NODE}/year=2025/{files}
│
├── staged/                 # Intermediate processing (temporary)
│   ├── pend/
│   │   └── market=MDA/region=SIN/zone={ZONE}/year=2025/{parquet}
│   └── pml/
│       └── market=MDA/region=SIN/node={NODE}/year=2025/{parquet}
│
├── consolidated/          # Final processed data (ready for lakehouse)
│   ├── pend/
│   │   └── market=MDA/region=SIN/zone={ZONE}/data_2025.parquet
│   └── pml/
│       └── market=MDA/region=SIN/node={NODE}/data_2025.parquet
│
└── manifests/            # Sync tracking manifests (JSON)
    └── sync_*.json
```

## Dataset Analysis

### 1. PEND (Precios de Energía en Nodos Distribuidos)
**Purpose:** Energy prices by load zone

**Schema:**
- `timestamp` (datetime) - UTC timestamp
- `zone` (string) - Load zone name (e.g., ACAPULCO, GUADALAJARA)
- `pz` (float) - Total price ($/MWh)
- `pz_ene` (float) - Energy component ($/MWh)
- `pz_per` (float) - Loss component ($/MWh)
- `pz_cng` (float) - Congestion component ($/MWh)
- `market` (string) - Market type (MDA, MTR)
- `region` (string) - Control region (SIN, BCA, BCS)

**Current Partitioning:**
- Hive-style: `market=MDA/region=SIN/zone={ZONE}/`
- Files: `data_2025.parquet` (year-based)

**Volume:**
- ~100+ zones in SIN region
- ~744 rows per zone per year (hourly data)
- Currently: 2025 data only

### 2. PML (Precios Marginales Locales)
**Purpose:** Locational marginal prices by node

**Schema:**
- `timestamp` (datetime) - UTC timestamp
- `node` (string) - Node ID (e.g., 05ASC-115)
- `pml` (float) - Locational marginal price ($/MWh)
- `pml_ene` (float) - Energy component ($/MWh)
- `pml_per` (float) - Loss component ($/MWh)
- `pml_cng` (float) - Congestion component ($/MWh)
- `market` (string) - Market type (MDA, MTR)
- `region` (string) - Control region (SIN, BCA, BCS)

**Current Partitioning:**
- Hive-style: `market=MDA/region=SIN/node={NODE}/`
- Files: `data_2025.parquet` (year-based)

**Volume:**
- Multiple nodes per region
- ~24 rows per node per day (hourly data)
- Currently: 2025 data only

## Mapping to Lakehouse Architecture

### Zone Mapping

| Current Location | Lakehouse Zone | Purpose |
|-----------------|----------------|---------|
| `raw/cenace/` | `raw/` | Immutable source data (JSON/XML files) |
| `consolidated/` | `bronze/` | Minimally transformed Parquet (ready for Iceberg) |
| `staged/` | *(temporary)* | Intermediate processing - not persisted |

### Table Contracts

Based on the data analysis, here are the recommended table contracts for `configs/lakehouse.yaml`:

```yaml
tables:
  bronze.pend:
    domain: "cenace"
    zone: "bronze"
    schema: "pend_bronze"
    partition_by: ["market", "region", "zone", "year"]
  
  bronze.pml:
    domain: "cenace"
    zone: "bronze"
    schema: "pml_bronze"
    partition_by: ["market", "region", "node", "year"]
```

### GCS Path Mapping

**Current (local):**
```
consolidated/pend/market=MDA/region=SIN/zone=ACAPULCO/data_2025.parquet
```

**Lakehouse (GCS):**
```
gs://lakehouse_phoenix/
  bronze/
    cenace/
      pend/
        market=MDA/
          region=SIN/
            zone=ACAPULCO/
              year=2025/
                data-{snapshot}.parquet  # Iceberg-managed
```

## Migration Strategy

### Phase 1: Define Contracts
1. Add table contracts to `configs/lakehouse.yaml`
2. Define PyIceberg schemas for PEND and PML in consuming repo (data-pipeline)
3. Map current schema to Iceberg schema

### Phase 2: Migrate Consolidated Data
1. Read existing `consolidated/` Parquet files
2. Create Iceberg tables using `lakehouse_core` API
3. Write data to `bronze/` zone in GCS
4. Register tables in Iceberg catalog

### Phase 3: Migrate Raw Data
1. Upload `raw/cenace/` files to GCS `raw/` zone
2. Preserve original structure for replay/debug
3. No Iceberg tables needed (raw files only)

### Phase 4: Update Pipeline
1. Modify data-pipeline to write directly to Iceberg tables
2. Use `lakehouse_core` for paths and catalog
3. Remove local `consolidated/` writes

## Schema Definitions Needed

### PEND Bronze Schema (PyIceberg)
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

### PML Bronze Schema (PyIceberg)
```python
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

## Partitioning Strategy

**Current:** Hive-style partitioning (`market=MDA/region=SIN/zone=ACAPULCO/`)

**Iceberg:** Use Iceberg's partition spec:
- PEND: `["market", "region", "zone", "year"]` (extract year from timestamp)
- PML: `["market", "region", "node", "year"]` (extract year from timestamp)

**Benefits:**
- Iceberg manages partitioning automatically
- Better query performance
- Time travel and versioning support
- Schema evolution support

## Next Steps

1. **Update `configs/lakehouse.yaml`** with table contracts (see above)
2. **Create migration script** in data-pipeline repo to:
   - Read consolidated Parquet files
   - Create Iceberg tables using `lakehouse_core`
   - Write data to GCS bronze zone
3. **Define schemas** in data-pipeline repo (not in lakehouse-core)
4. **Test migration** with a small subset first
5. **Update ingestion pipeline** to write directly to Iceberg

## Notes

- **Manifests:** The sync manifests in `manifests/` are not needed with Iceberg (Iceberg tracks metadata automatically)
- **Staged data:** Can be removed after migration (temporary processing)
- **Raw data:** Should be preserved in `raw/` zone for replay/debugging
- **Year extraction:** Need to extract `year` partition from `timestamp` column during migration

