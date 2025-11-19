"""
Table contract helpers for the lakehouse platform.

This module provides functions to access table identifiers and contracts.
"""
from typing import Tuple, Optional
from pyiceberg.table.identifier import Identifier

from .config import get_lakehouse_config, LakehouseConfig


def get_table_identifier(name: str, config: Optional[LakehouseConfig] = None) -> Identifier:
    """
    Get the table identifier tuple from a full table name.
    
    Args:
        name: Full table name (e.g., "bronze.energy_prices")
        config: Optional lakehouse config (loads if not provided)
    
    Returns:
        Identifier tuple: (namespace, table_name)
        e.g., "bronze.energy_prices" -> ("bronze", "energy_prices")
    """
    if "." not in name:
        raise ValueError(f"Table name must be in format 'namespace.table_name', got '{name}'")
    
    namespace, table = name.split(".", 1)
    return (namespace, table)


def get_table_contract(table_name: str, config: Optional[LakehouseConfig] = None) -> Optional[dict]:
    """
    Get the table contract for a given table name.
    
    Args:
        table_name: Full table identifier (e.g., "bronze.example_table")
        config: Optional lakehouse config (loads if not provided)
    
    Returns:
        Table contract dict if found, None otherwise
    """
    if config is None:
        config = get_lakehouse_config()
    
    return config.tables.get(table_name)
