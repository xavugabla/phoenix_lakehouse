"""
Iceberg catalog configuration and initialization.

This module provides functions to obtain and configure the Iceberg catalog
(SQL-based with SQLite) for table metadata management. Table data is stored
in GCS under the warehouse path.
"""
import os
from functools import lru_cache
from typing import Optional

from pyiceberg.catalog import Catalog, load_catalog

from .config import get_lakehouse_config, LakehouseConfig


@lru_cache(maxsize=1)
def get_iceberg_catalog(config: Optional[LakehouseConfig] = None) -> Catalog:
    """
    Get the configured Iceberg catalog (SQL-based with SQLite).
    
    This function initializes and returns the SQL catalog for managing
    Iceberg table metadata. Catalog metadata is stored in SQLite, while
    table data is stored in GCS under the warehouse path.
    
    Args:
        config: Optional lakehouse config (loads if not provided)
    
    Returns:
        Configured Iceberg Catalog instance
    
    Raises:
        ValueError: If catalog configuration is invalid
    """
    os.environ.setdefault("PYICEBERG_LEGACY_CURRENT_SNAPSHOT_ID", "true")

    if config is None:
        config = get_lakehouse_config()

    catalog_type = config.catalog.get("type", "sql")
    
    if catalog_type == "sql":
        # SQL catalog (SQLite)
        uri = config.catalog.get("uri")
        if not uri:
            raise ValueError(
                "Catalog URI not configured. Please set catalog.uri "
                "in configs/lakehouse.yaml (e.g., 'sqlite:///iceberg_catalog.db')"
            )
        
        warehouse = config.catalog.get("warehouse")
        if not warehouse:
            raise ValueError(
                "Catalog warehouse not configured. Please set catalog.warehouse "
                "in configs/lakehouse.yaml (e.g., 'gs://lakehouse_phoenix/iceberg/')"
            )
        
        # Ensure warehouse path ends with /
        if not warehouse.endswith("/"):
            warehouse = f"{warehouse}/"
        
        catalog = load_catalog(
            "phoenix",
            **{
                "type": "sql",
                "uri": uri,
                "warehouse": warehouse,
            }
        )
    else:
        raise ValueError(
            f"Unsupported catalog type '{catalog_type}'. "
            "Supported types: 'sql' (SQLite)"
        )

    return catalog
