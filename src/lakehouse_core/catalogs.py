"""
Iceberg catalog configuration and initialization.

This module provides functions to obtain and configure the unified
file-based Iceberg catalog (Hadoop-style) on GCS for table metadata management.
"""
import os
from functools import lru_cache
from typing import Optional

from pyiceberg.catalog import Catalog, load_catalog

from .config import get_lakehouse_config, LakehouseConfig


@lru_cache(maxsize=1)
def get_iceberg_catalog(config: Optional[LakehouseConfig] = None) -> Catalog:
    """
    Get the configured Iceberg catalog (file-based/Hadoop-style on GCS).
    
    This function initializes and returns the unified file-based catalog
    for managing Iceberg table metadata. All metadata is stored in GCS
    under the warehouse path.
    
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

    catalog_type = config.catalog.get("type", "hadoop")
    if catalog_type != "hadoop":
        raise ValueError(
            f"Catalog type must be 'hadoop' (file-based), got '{catalog_type}'. "
            "This platform uses a file-based catalog on GCS as the single source of truth."
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
            "type": "hadoop",
            "warehouse": warehouse,
        }
    )

    return catalog
