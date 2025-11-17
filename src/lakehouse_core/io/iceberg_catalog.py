"""
File-based catalog for Iceberg tables.

This catalog maps table names to GCS metadata locations, allowing direct
querying of Iceberg tables without requiring BigQuery or other catalog services.
"""
import json
from pathlib import Path
from typing import Optional, Dict
import structlog

from ..config import load_config

logger = structlog.get_logger()

# Default catalog file location
CATALOG_FILE = Path("catalogues/iceberg_catalog.json")


def get_catalog_path() -> Path:
    """Get the path to the catalog file."""
    config = load_config()
    if hasattr(config, 'lakehouse') and hasattr(config.lakehouse, 'catalog_file'):
        return Path(config.lakehouse.catalog_file)
    return CATALOG_FILE


def load_catalog() -> Dict[str, str]:
    """
    Load the file-based catalog.
    
    Returns:
        Dictionary mapping table names to GCS metadata locations
        Format: {"table_name": "gs://bucket/table_path/metadata/metadata.json"}
    """
    catalog_path = get_catalog_path()
    
    if not catalog_path.exists():
        logger.warning(f"Catalog file not found at {catalog_path}, returning empty catalog")
        return {}
    
    try:
        with open(catalog_path, 'r', encoding='utf-8') as f:
            catalog = json.load(f)
        logger.debug(f"Loaded catalog with {len(catalog)} tables from {catalog_path}")
        return catalog
    except Exception as e:
        logger.error(f"Failed to load catalog from {catalog_path}: {e}")
        return {}


def save_catalog(catalog: Dict[str, str]) -> None:
    """
    Save the catalog to disk.
    
    Args:
        catalog: Dictionary mapping table names to GCS metadata locations
    """
    catalog_path = get_catalog_path()
    catalog_path.parent.mkdir(parents=True, exist_ok=True)
    
    try:
        with open(catalog_path, 'w', encoding='utf-8') as f:
            json.dump(catalog, f, indent=2, sort_keys=True)
        logger.info(f"Saved catalog with {len(catalog)} tables to {catalog_path}")
    except Exception as e:
        logger.error(f"Failed to save catalog to {catalog_path}: {e}")
        raise


def get_table_path(table_name: str) -> Optional[str]:
    """
    Get the GCS metadata location for a table.
    
    Args:
        table_name: Name of the table (e.g., "pend", "nodes")
    
    Returns:
        GCS path to metadata.json file, or None if not found
    """
    catalog = load_catalog()
    return catalog.get(table_name)


def update_table_path(table_name: str, metadata_location: str) -> None:
    """
    Update the catalog with a table's metadata location.
    
    Args:
        table_name: Name of the table
        metadata_location: GCS path to the metadata.json file
    """
    catalog = load_catalog()
    catalog[table_name] = metadata_location
    save_catalog(catalog)
    logger.info(f"Updated catalog: {table_name} -> {metadata_location}")


def find_latest_metadata_location(table_base_path: str) -> Optional[str]:
    """
    Find the latest metadata.json file for a table in GCS.
    
    Args:
        table_base_path: Base GCS path to the table (e.g., "gs://bucket/table_name")
    
    Returns:
        Full path to the latest metadata.json file, or None if not found
    """
    from google.cloud import storage
    
    # Parse GCS path
    if not table_base_path.startswith("gs://"):
        logger.error(f"Invalid GCS path: {table_base_path}")
        return None
    
    parts = table_base_path.replace("gs://", "").split("/", 1)
    bucket_name = parts[0]
    prefix = f"{parts[1]}/metadata/" if len(parts) > 1 else "metadata/"
    
    try:
        client = storage.Client()
        bucket = client.bucket(bucket_name)
        
        # List all metadata files
        blobs = list(bucket.list_blobs(prefix=prefix))
        metadata_files = [b for b in blobs if b.name.endswith('.metadata.json')]
        
        if not metadata_files:
            logger.warning(f"No metadata files found at {table_base_path}/metadata/")
            return None
        
        # Get the latest (highest version number)
        latest = sorted(metadata_files, key=lambda x: x.name, reverse=True)[0]
        metadata_location = f"gs://{bucket_name}/{latest.name}"
        
        logger.debug(f"Found latest metadata: {metadata_location}")
        return metadata_location
        
    except Exception as e:
        logger.error(f"Failed to find metadata location for {table_base_path}: {e}")
        return None

