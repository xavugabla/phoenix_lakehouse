"""
Table contract helpers for the lakehouse platform.

This module provides functions to access table identifiers and contracts,
and utilities for creating Bronze tables.
"""
from typing import Tuple, Optional
try:
    # PyIceberg >= 0.10.0: Identifier is a type alias in pyiceberg.table
    from pyiceberg.table import Identifier
except ImportError:
    # PyIceberg < 0.10.0: Identifier was in pyiceberg.table.identifier
    from pyiceberg.table.identifier import Identifier

try:
    from pyiceberg.partitioning import PartitionSpec, PartitionField
    from pyiceberg.transforms import IdentityTransform
    from pyiceberg.schema import Schema
except ImportError:
    # Fallback for older PyIceberg versions
    PartitionSpec = None
    PartitionField = None
    IdentityTransform = None
    Schema = None

from .config import get_lakehouse_config, LakehouseConfig
from .paths import get_full_gcs_path


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


def create_partition_spec(partition_keys: list, schema: Schema) -> PartitionSpec:
    """
    Create Iceberg partition spec from partition keys.
    
    Args:
        partition_keys: List of field names to partition by
        schema: PyIceberg Schema instance
    
    Returns:
        PartitionSpec instance
    
    Raises:
        ValueError: If a partition key is not found in the schema
        ImportError: If PyIceberg partitioning modules are not available
    """
    if PartitionSpec is None or PartitionField is None or IdentityTransform is None:
        raise ImportError(
            "PyIceberg partitioning modules not available. "
            "Please ensure pyiceberg>=0.10.0 is installed."
        )
    
    fields = []
    for idx, key in enumerate(partition_keys):
        # Find field ID in schema
        field = next((f for f in schema.fields if f.name == key), None)
        if not field:
            raise ValueError(f"Partition key '{key}' not found in schema")
        fields.append(
            PartitionField(
                source_id=field.field_id,
                field_id=1000 + idx,  # Partition field IDs start at 1000
                name=key,
                transform=IdentityTransform(),
            )
        )
    return PartitionSpec(*fields)


def create_bronze_table(
    table_name: str,
    schema: Schema,
    overwrite: bool = False
):
    """
    Create a Bronze Iceberg table from a table contract.
    
    This function creates an Iceberg table in the catalog using the table contract
    configuration. The table will be partitioned according to the contract's
    partition_by specification.
    
    Args:
        table_name: Full table identifier (e.g., "bronze.pend")
        schema: PyIceberg Schema instance for the table
        overwrite: If True, drop existing table before creating (default: False)
    
    Returns:
        Created Iceberg Table instance
    
    Raises:
        ValueError: If table contract not found or invalid
        ImportError: If required PyIceberg modules are not available
    """
    from .catalogs import get_iceberg_catalog

    # Load config inside the function to ensure caching works correctly
    # The lru_cache on get_iceberg_catalog expects hashable arguments
    config = get_lakehouse_config()

    # Get table contract
    contract = get_table_contract(table_name, config)
    if not contract:
        raise ValueError(f"Table contract not found for '{table_name}'")
    
    # Validate contract has required fields
    if "partition_by" not in contract:
        raise ValueError(f"Table contract for '{table_name}' missing 'partition_by' field")
    
    partition_keys = contract.get("partition_by", [])
    if not isinstance(partition_keys, list):
        raise ValueError(f"Table contract 'partition_by' must be a list, got {type(partition_keys)}")
    
    # Get catalog and table identifier
    catalog = get_iceberg_catalog() # Pass no arguments to leverage cache
    identifier = get_table_identifier(table_name, config)
    
    # Check if table exists
    try:
        existing_table = catalog.load_table(identifier)
        if overwrite:
            catalog.drop_table(identifier)
        else:
            return existing_table
    except Exception:
        # Table doesn't exist, proceed with creation
        pass
    
    # Create partition spec
    partition_spec = create_partition_spec(partition_keys, schema)
    
    # Get table location
    table_location = get_full_gcs_path(table_name, config)
    
    # Create table
    table = catalog.create_table(
        identifier=identifier,
        schema=schema,
        partition_spec=partition_spec,
        location=table_location,
    )
    
    return table
