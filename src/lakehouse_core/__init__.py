"""
Lakehouse Core - Platform definitions for Iceberg + GCS lakehouse.

This package provides:
- GCS storage layout definitions (raw/bronze/silver/gold zones)
- Iceberg catalog configuration (SQL/SQLite catalog for metadata)
- Table contracts: schemas, table names, namespaces, partitioning
- Minimal Python API for consuming repositories

Usage:
    from lakehouse_core import get_lakehouse_config
    from lakehouse_core.catalogs import get_iceberg_catalog
    from lakehouse_core.tables import get_table_identifier
    from lakehouse_core.paths import zone_prefix, table_prefix
    
    # Load configuration
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
"""

__version__ = "0.1.0"

from . import config
from . import catalogs
from . import paths
from . import tables
from . import schemas

# Expose main API functions
from .config import get_lakehouse_config
from .catalogs import get_iceberg_catalog
from .tables import (
    get_table_identifier,
    get_table_contract,
    create_partition_spec,
    create_bronze_table,
)

__all__ = [
    "config",
    "catalogs",
    "paths",
    "tables",
    "schemas",
    "get_lakehouse_config",
    "get_iceberg_catalog",
    "get_table_identifier",
    "get_table_contract",
    "create_partition_spec",
    "create_bronze_table",
    "__version__",
]
