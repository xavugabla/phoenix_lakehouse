"""
Storage path generation strictly from dataset contracts.

This module generates bronze/silver/gold storage paths based on contract
definitions, ensuring paths are never hardcoded.
"""
from pathlib import Path
from typing import Dict, Any, Optional
from .loader import DatasetContract


class PathError(Exception):
    """Path generation error."""
    pass


def get_storage_path(
    contract: DatasetContract,
    zone: str,
    base_path: Optional[str] = None,
    params: Optional[Dict[str, Any]] = None
) -> str:
    """
    Generate storage path for a dataset in a specific zone.
    
    Args:
        contract: Dataset contract
        zone: Storage zone ("bronze", "silver", or "gold")
        base_path: Optional base path (e.g., "gs://bucket" or "/data")
        params: Optional runtime parameters for path templating
    
    Returns:
        Full storage path for the dataset
    
    Raises:
        PathError: If zone is invalid or path generation fails
    """
    # Get zone path template from contract
    zone = zone.lower()
    if zone == "bronze":
        zone_path = contract.storage.bronze
    elif zone == "silver":
        zone_path = contract.storage.silver
    elif zone == "gold":
        zone_path = contract.storage.gold
    else:
        raise PathError(
            f"Invalid zone '{zone}'. Must be one of: bronze, silver, gold"
        )
    
    # Apply parameter templating if needed
    if params:
        try:
            zone_path = zone_path.format(**params)
        except KeyError as e:
            raise PathError(
                f"Path template requires parameter that wasn't provided: {e}"
            )
    
    # Combine with base path if provided
    if base_path:
        base_path = base_path.rstrip("/")
        zone_path = zone_path.lstrip("/")
        return f"{base_path}/{zone_path}"
    
    return zone_path


def get_all_storage_paths(
    contract: DatasetContract,
    base_path: Optional[str] = None,
    params: Optional[Dict[str, Any]] = None
) -> Dict[str, str]:
    """
    Generate all storage paths (bronze, silver, gold) for a dataset.
    
    Args:
        contract: Dataset contract
        base_path: Optional base path (e.g., "gs://bucket" or "/data")
        params: Optional runtime parameters for path templating
    
    Returns:
        Dictionary with keys "bronze", "silver", "gold" and their paths
    """
    return {
        "bronze": get_storage_path(contract, "bronze", base_path, params),
        "silver": get_storage_path(contract, "silver", base_path, params),
        "gold": get_storage_path(contract, "gold", base_path, params),
    }


def get_partitioned_path(
    contract: DatasetContract,
    zone: str,
    params: Dict[str, Any],
    base_path: Optional[str] = None
) -> str:
    """
    Generate a partitioned storage path based on contract partitioning keys.
    
    This creates a Hive-style partitioned path using the partitioning keys
    defined in the contract.
    
    Args:
        contract: Dataset contract
        zone: Storage zone ("bronze", "silver", or "gold")
        params: Runtime parameters containing partition key values
        base_path: Optional base path (e.g., "gs://bucket" or "/data")
    
    Returns:
        Full partitioned path (e.g., ".../market=MDA/region=BCA/year=2024")
    
    Raises:
        PathError: If required partition keys are missing from params
    """
    # Get base storage path
    storage_path = get_storage_path(contract, zone, base_path, params)
    
    # Build partition path segments
    partition_segments = []
    missing_keys = []
    
    for key in contract.partitioning.keys:
        if key not in params:
            missing_keys.append(key)
        else:
            partition_segments.append(f"{key}={params[key]}")
    
    if missing_keys:
        raise PathError(
            f"Cannot generate partitioned path: missing partition keys: "
            f"{', '.join(missing_keys)}"
        )
    
    # Combine base path with partition segments
    if partition_segments:
        partition_path = "/".join(partition_segments)
        return f"{storage_path}/{partition_path}"
    
    return storage_path


def get_output_filename(
    dataset_id: str,
    run_id: str,
    extension: str = "parquet"
) -> str:
    """
    Generate a standardized output filename.
    
    Args:
        dataset_id: Dataset identifier
        run_id: Unique run identifier
        extension: File extension (default: "parquet")
    
    Returns:
        Filename string (e.g., "cenace_pml_20240115_123456.parquet")
    """
    return f"{dataset_id}_{run_id}.{extension}"


def validate_partition_keys(
    contract: DatasetContract,
    params: Dict[str, Any]
) -> bool:
    """
    Validate that all partition keys are present in params.
    
    Args:
        contract: Dataset contract
        params: Runtime parameters
    
    Returns:
        True if all partition keys are present, False otherwise
    """
    for key in contract.partitioning.keys:
        if key not in params:
            return False
    return True


def get_missing_partition_keys(
    contract: DatasetContract,
    params: Dict[str, Any]
) -> list:
    """
    Get list of missing partition keys.
    
    Args:
        contract: Dataset contract
        params: Runtime parameters
    
    Returns:
        List of missing partition key names
    """
    missing = []
    for key in contract.partitioning.keys:
        if key not in params:
            missing.append(key)
    return missing
