1. Bottom-line objective of this repo

This repo is the “data contract + layout” library for your whole ecosystem.

In one sentence:

phoenix_lakehouse defines where data lives, what the tables look like, and how to talk to the Iceberg catalog — nothing more.

Every other repo (pipelines, managers, models) should be forced to play by the rules defined here.

If this repo disappeared, you’d lose:

A single source of truth for table names, schemas, and partitions

A single config for bucket/zones/catalog

The clean programmatic API to get an Iceberg catalog and table definitions

You would not lose any ETL flows, business logic, or Monte Carlos. That’s the point.

2. Responsibilities vs. Non-responsibilities
✅ This repo DOES:

Define storage layout

GCS bucket name(s)

Zones: raw, bronze, silver, gold

Conventions for paths (e.g. domain/table/year/month/day)

Define the Iceberg catalog

Type (BigQuery / Nessie / whatever)

Catalog name, project, dataset, connection params

Helper to initialize the catalog from code

Define table contracts

Namespaces (e.g. bronze.energy, silver.energy, gold.revenue)

Table names

Schemas (columns + types)

Partition specs

Expose a tiny Python API

get_lakehouse_config()

get_iceberg_catalog()

get_table_identifier("bronze.energy_prices")

Access to the schema objects for each table

That’s it. It’s a library, not a system.

❌ This repo DOES NOT:

Run Prefect

Fetch data from APIs

Write data to GCS/Iceberg (beyond maybe creating empty tables)

Run migrations, backfills, or syncs

Contain CENACE-specific pipeline logic

Serve web endpoints

Contain notebooks, dashboards, Monte Carlo models, etc.

All of that lives in:

data-pipeline

data-manager

revenue-models

Those repos import phoenix_lakehouse to know where and how to read/write.

3. Target structure (what this repo should look like)

Something like:

phoenix_lakehouse/
  pyproject.toml
  configs/
    lakehouse.yaml

  src/
    lakehouse_core/
      __init__.py
      config.py        # load/validate lakehouse.yaml
      catalogs.py      # build Iceberg catalog client
      paths.py         # build GCS paths for zones/tables
      tables.py        # table identifiers + utilities
      schemas/
        __init__.py
        energy_prices.py
        weather.py
        metadata.py
        revenue.py

  docs/
    architecture.md
    tables.md


If you have more than ~15–20 “real” files in this repo, it’s probably creeping out of scope again.

4. What each core module should do
configs/lakehouse.yaml

Human-readable, version-controlled config. For example:

bucket: "lakehouse_phoenix"
prefix: ""  # or "prod/"

zones:
  raw: "raw"
  bronze: "bronze"
  silver: "silver"
  gold: "gold"

catalog:
  type: "bigquery"
  project: "novagrid-476915"
  dataset: "novagrid_lakehouse"

tables:
  bronze.energy_prices:
    domain: "energy"
    zone: "bronze"
    schema: "energy_prices_bronze"
    partition_by: ["system", "market", "region", "date"]
  silver.energy_prices:
    domain: "energy"
    zone: "silver"
    schema: "energy_prices_silver"
    partition_by: ["system", "market", "region", "date"]
  gold.revenue_simulations:
    domain: "revenue"
    zone: "gold"
    schema: "revenue_simulations"
    partition_by: ["scenario_date"]

config.py

Load and validate lakehouse.yaml.

Expose something like:

from pydantic import BaseModel

class LakehouseConfig(BaseModel):
    bucket: str
    prefix: str
    zones: dict
    catalog: dict
    tables: dict

_config: LakehouseConfig = ...

def get_lakehouse_config() -> LakehouseConfig:
    return _config

catalogs.py

Use get_lakehouse_config() and return a pyiceberg catalog:

from pyiceberg.catalog import load_catalog

def get_iceberg_catalog():
    cfg = get_lakehouse_config()
    # build kwargs for load_catalog based on cfg.catalog
    return load_catalog("phoenix", **kwargs)


No ETL, no queries, just “here’s a catalog object”.

paths.py

Helper functions so no other repo ever hardcodes GCS paths:

def zone_prefix(zone: str) -> str:
    cfg = get_lakehouse_config()
    return f"{cfg.prefix}{cfg.zones[zone]}/"

def table_prefix(table_name: str) -> str:
    cfg = get_lakehouse_config()
    table = cfg.tables[table_name]
    return f"{zone_prefix(table['zone'])}{table['domain']}/{table_name.split('.')[-1]}/"


Your pipeline can call this instead of inventing its own folder logic.

schemas/…

Each file defines a Schema object (pyiceberg) and maybe a pydantic model for strictness.

Example schemas/energy_prices.py:

from pyiceberg.schema import Schema
from pyiceberg.types import StringType, TimestampType, DoubleType

ENERGY_PRICES_BRONZE = Schema(
    # id, name, type
    ("system", StringType()),
    ("market", StringType()),
    ("region", StringType()),
    ("ts_utc", TimestampType()),
    ("price", DoubleType()),
    ("raw_payload", StringType()),
)


Nothing fetches data here. It just defines shapes.

tables.py

Small convenience layer:

from pyiceberg.table.identifier import Identifier
from .config import get_lakehouse_config

def get_table_identifier(name: str) -> Identifier:
    # e.g., "bronze.energy_prices" -> ("bronze", "energy_prices")
    namespace, table = name.split(".")
    return (namespace, table)


Your other repos can do:

from lakehouse_core.catalogs import get_iceberg_catalog
from lakehouse_core.tables import get_table_identifier

catalog = get_iceberg_catalog()
table = catalog.load_table(get_table_identifier("bronze.energy_prices"))

5. “Done” definition for this repo

You’ll know this repo is done enough when:

✅ There are no Prefect imports anywhere.

✅ There are no HTTP clients, no external API calls.

✅ There are no flows, backfill, migrate, or sync functions.

✅ You can, from another repo, do:

from lakehouse_core import get_lakehouse_config
from lakehouse_core.catalogs import get_iceberg_catalog
from lakehouse_core.schemas.energy_prices import ENERGY_PRICES_BRONZE


and that’s all you need to:

know where to write

know what schema to use

get a catalog to operate on

✅ If you asked, “What does phoenix_lakehouse do?” the honest answer is:

“It defines our lakehouse layout, catalog, and table contracts. That’s it.”