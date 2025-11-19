"""
GCS path helpers for the lakehouse platform.

This module provides functions to build standardized GCS paths
for zones and tables, ensuring no hardcoded paths in consuming repos.
"""
from typing import Optional
from .config import get_lakehouse_config, LakehouseConfig


def zone_prefix(zone: str, config: Optional[LakehouseConfig] = None) -> str:
    """
    Get the GCS prefix for a zone.
    
    Args:
        zone: Zone name (e.g., "raw", "bronze", "silver", "gold")
        config: Optional lakehouse config (loads if not provided)
    
    Returns:
        Zone prefix: "{prefix}{zone}/" or "{zone}/"
    """
    if config is None:
        config = get_lakehouse_config()
    
    zone_path = config.zones.get(zone, zone)
    prefix = config.prefix.rstrip("/") if config.prefix else ""
    
    if prefix:
        return f"{prefix}/{zone_path}/"
    return f"{zone_path}/"


def table_prefix(table_name: str, config: Optional[LakehouseConfig] = None) -> str:
    """
    Get the GCS prefix for a table based on its contract.
    
    Args:
        table_name: Full table identifier (e.g., "bronze.example_table")
        config: Optional lakehouse config (loads if not provided)
    
    Returns:
        Table prefix: "{zone_prefix}{domain}/{table}/"
    """
    if config is None:
        config = get_lakehouse_config()
    
    # Parse table identifier (e.g., "bronze.example_table")
    if "." not in table_name:
        raise ValueError(f"Table name must be in format 'zone.table_name', got '{table_name}'")
    
    zone, table_base = table_name.split(".", 1)
    
    # Get table contract
    table_contract = config.tables.get(table_name, {})
    domain = table_contract.get("domain", "default")
    
    # Build path
    zone_pref = zone_prefix(zone, config)
    return f"{zone_pref}{domain}/{table_base}/"


def get_full_gcs_path(table_name: str, config: Optional[LakehouseConfig] = None) -> str:
    """
    Get the full GCS path for a table.
    
    This returns the base path where Iceberg will store the table.
    Iceberg manages the actual data/metadata structure under this path.
    
    Args:
        table_name: Full table identifier (e.g., "bronze.example_table")
        config: Optional lakehouse config (loads if not provided)
    
    Returns:
        Full GCS path: "gs://{bucket}/{table_prefix}"
        Example: "gs://lakehouse_phoenix/bronze/cenace/pend/"
    """
    if config is None:
        config = get_lakehouse_config()
    
    table_pref = table_prefix(table_name, config)
    return f"gs://{config.bucket}/{table_pref}"
