# Graph Report - .  (2026-04-26)

## Corpus Check
- Corpus is ~13,895 words - fits in a single context window. You may not need a graph.

## Summary
- 141 nodes · 190 edges · 14 communities detected
- Extraction: 94% EXTRACTED · 6% INFERRED · 0% AMBIGUOUS · INFERRED: 11 edges (avg confidence: 0.5)
- Token cost: 0 input · 0 output

## Community Hubs (Navigation)
- [[_COMMUNITY_Platform & Dependencies|Platform & Dependencies]]
- [[_COMMUNITY_Bootstrap & Validation Scripts|Bootstrap & Validation Scripts]]
- [[_COMMUNITY_Paths & Tables Core|Paths & Tables Core]]
- [[_COMMUNITY_Core API Functions|Core API Functions]]
- [[_COMMUNITY_Config & Catalog Modules|Config & Catalog Modules]]
- [[_COMMUNITY_Package Architecture|Package Architecture]]
- [[_COMMUNITY_Domain & Config Patterns|Domain & Config Patterns]]
- [[_COMMUNITY_GCS Buckets & Consumers|GCS Buckets & Consumers]]
- [[_COMMUNITY_Schema Distribution|Schema Distribution]]
- [[_COMMUNITY_Catalog Type Decisions|Catalog Type Decisions]]
- [[_COMMUNITY_Master Schemas|Master Schemas]]
- [[_COMMUNITY_Raw Zone Preservation|Raw Zone Preservation]]
- [[_COMMUNITY_Setup Script|Setup Script]]
- [[_COMMUNITY_Error Handling|Error Handling]]

## God Nodes (most connected - your core abstractions)
1. `LakehouseConfig` - 15 edges
2. `phoenix_lakehouse` - 14 edges
3. `get_lakehouse_config()` - 7 edges
4. `create_bronze_table()` - 6 edges
5. `lakehouse_core.paths` - 6 edges
6. `bootstrap_table()` - 5 edges
7. `get_lakehouse_config()` - 5 edges
8. `create_bronze_table()` - 5 edges
9. `get_iceberg_catalog()` - 5 edges
10. `get_table_contract()` - 5 edges

## Surprising Connections (you probably didn't know these)
- `lakehouse_core` ----> `Pure Library Constraint`  [EXTRACTED]
  src/lakehouse_core/__init__.py → DESIGN_CONSTRAINTS.md
- `get_iceberg_catalog()` ----> `File-Based Catalog Constraint`  [EXTRACTED]
  src/lakehouse_core/catalogs.py → DESIGN_CONSTRAINTS.md
- `zone_prefix()` ----> `Medallion Zone Architecture`  [EXTRACTED]
  src/lakehouse_core/paths.py → ARCHITECTURE.md
- `get_full_gcs_path()` ----> `GCS Storage Layout`  [EXTRACTED]
  src/lakehouse_core/paths.py → ARCHITECTURE.md
- `lakehouse_core.schemas` ----> `Consuming Repositories`  [EXTRACTED]
  src/lakehouse_core/schemas/__init__.py → ARCHITECTURE.md

## Hyperedges (group relationships)
- **Bronze Table Creation Flow** —  [INFERRED 1.00]
- **Design Constraint Enforcement Pattern** —  [INFERRED 1.00]
- **CENACE Data Migration Pipeline** —  [INFERRED 1.00]
- **Medallion Architecture (Raw/Bronze/Silver/Gold)** — zone_raw, zone_bronze, zone_silver, zone_gold [INFERRED 1.00]
- **Lakehouse Consumer Ecosystem** — data_pipeline_repo, data_manager_repo, revenue_models_repo, phoenix_lakehouse [INFERRED 1.00]
- **GCS Bucket Lifecycle (Active + Legacy)** — novagrid_lakehouse_bucket, lakehouse_phoenix_bucket, novogrid_workqueue_bucket, unification_plan [INFERRED 1.00]

## Communities

### Community 0 - "Platform & Dependencies"
Cohesion: 0.12
Nodes (22): Apache Iceberg, BigQuery, bronze.pend, bronze.pml, configs/tables/cenace.yaml, data-manager, data-pipeline, Pure Library Boundary (+14 more)

### Community 1 - "Bootstrap & Validation Scripts"
Cohesion: 0.12
Nodes (17): _arrow_type_to_iceberg(), bootstrap_table(), find_parquet_files(), main(), parquet_to_iceberg_schema(), Bootstrap Bronze tables from consolidated parquet data.  This script migrates ex, Find all parquet files for a given table.          Args:         data_dir: Root, Bootstrap a single Bronze table from consolidated parquet data.          Args: (+9 more)

### Community 2 - "Paths & Tables Core"
Cohesion: 0.16
Nodes (19): BaseModel, LakehouseConfig, Configuration for the Data Lakehouse platform., get_full_gcs_path(), GCS path helpers for the lakehouse platform.  This module provides functions to, Get the GCS prefix for a zone.          Args:         zone: Zone name (e.g., "ra, Get the GCS prefix for a table based on its contract.          Args:         tab, Get the full GCS path for a table.          This returns the base path where Ice (+11 more)

### Community 3 - "Core API Functions"
Cohesion: 0.19
Nodes (14): create_bronze_table(), GCS Storage Layout, get_full_gcs_path(), get_iceberg_catalog(), get_lakehouse_config(), get_table_contract(), get_table_identifier(), File-Based Catalog Constraint (+6 more)

### Community 4 - "Config & Catalog Modules"
Cohesion: 0.17
Nodes (12): get_iceberg_catalog(), Iceberg catalog configuration and initialization.  This module provides function, Get the configured Iceberg catalog (SQL-based with SQLite).          This functi, ConfigError, get_lakehouse_config(), _load_table_contracts(), Configuration loading and validation for the lakehouse platform.  This module pr, Load table contracts from modular YAML files.          Looks for files in config (+4 more)

### Community 5 - "Package Architecture"
Cohesion: 0.18
Nodes (13): No Hardcoded Paths, get_iceberg_catalog(), get_lakehouse_config(), LakehouseConfig, configs/lakehouse.yaml, lakehouse_core.catalogs, lakehouse_core.config, lakehouse_core (+5 more)

### Community 6 - "Domain & Config Patterns"
Cohesion: 0.32
Nodes (8): LakehouseConfig, CENACE Domain, Modular Config Pattern, Naming Conventions, PEND (Precios de Energia en Nodos Distribuidos), PML (Precios Marginales Locales), Why Modular Config Layout, Table Contract

### Community 7 - "GCS Buckets & Consumers"
Cohesion: 0.25
Nodes (8): cenace_workers, Pinned Contract Authority, gs://lakehouse_phoenix, novafront, gs://novagrid-lakehouse, novagrid, gs://novogrid-workqueue, Lakehouse Unification Plan

### Community 8 - "Schema Distribution"
Cohesion: 0.5
Nodes (4): Consuming Repositories, lakehouse_core.schemas.master_schemas, Why Schemas Belong in Consuming Repos, lakehouse_core.schemas

### Community 9 - "Catalog Type Decisions"
Cohesion: 0.67
Nodes (3): BigQuery Not Used as Catalog, Hadoop/File-based Catalog, SQL Catalog (SQLite)

### Community 10 - "Master Schemas"
Cohesion: 1.0
Nodes (1): Schema helper utilities for Iceberg tables.  This module provides helper functio

### Community 11 - "Raw Zone Preservation"
Cohesion: 1.0
Nodes (2): Raw Data Preservation, Raw Zone

### Community 12 - "Setup Script"
Cohesion: 1.0
Nodes (0): 

### Community 13 - "Error Handling"
Cohesion: 1.0
Nodes (1): ConfigError

## Knowledge Gaps
- **41 isolated node(s):** `Bootstrap Bronze tables from consolidated parquet data.  This script migrates ex`, `Convert Parquet file schema to PyIceberg Schema.          Args:         parquet_`, `Convert PyArrow type to PyIceberg type (simplified).`, `Find all parquet files for a given table.          Args:         data_dir: Root`, `Bootstrap a single Bronze table from consolidated parquet data.          Args:` (+36 more)
  These have ≤1 connection - possible missing edges or undocumented components.
- **Thin community `Master Schemas`** (2 nodes): `Schema helper utilities for Iceberg tables.  This module provides helper functio`, `master_schemas.py`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Raw Zone Preservation`** (2 nodes): `Raw Data Preservation`, `Raw Zone`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Setup Script`** (1 nodes): `setup.ps1`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Error Handling`** (1 nodes): `ConfigError`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `phoenix_lakehouse` connect `Platform & Dependencies` to `Config & Catalog Modules`, `Package Architecture`?**
  _High betweenness centrality (0.372) - this node is a cross-community bridge._
- **Why does `pydantic` connect `Config & Catalog Modules` to `Platform & Dependencies`?**
  _High betweenness centrality (0.240) - this node is a cross-community bridge._
- **Why does `lakehouse_core` connect `Package Architecture` to `Platform & Dependencies`, `Bootstrap & Validation Scripts`?**
  _High betweenness centrality (0.239) - this node is a cross-community bridge._
- **Are the 11 inferred relationships involving `LakehouseConfig` (e.g. with `GCS path helpers for the lakehouse platform.  This module provides functions to` and `Get the GCS prefix for a zone.          Args:         zone: Zone name (e.g., "ra`) actually correct?**
  _`LakehouseConfig` has 11 INFERRED edges - model-reasoned connections that need verification._
- **What connects `Bootstrap Bronze tables from consolidated parquet data.  This script migrates ex`, `Convert Parquet file schema to PyIceberg Schema.          Args:         parquet_`, `Convert PyArrow type to PyIceberg type (simplified).` to the rest of the system?**
  _41 weakly-connected nodes found - possible documentation gaps or missing edges._
- **Should `Platform & Dependencies` be split into smaller, more focused modules?**
  _Cohesion score 0.12 - nodes in this community are weakly interconnected._
- **Should `Bootstrap & Validation Scripts` be split into smaller, more focused modules?**
  _Cohesion score 0.12 - nodes in this community are weakly interconnected._