"""
Utilities for interacting with Apache Iceberg.
"""
import os
from functools import lru_cache
from typing import Optional

import structlog
from google.auth import default as default_auth
from pyiceberg.catalog import Catalog, load_catalog
from pyiceberg.table import Table

from ..config import LakehouseConfig, load_config
from .iceberg_catalog import get_table_path, load_catalog as load_file_catalog

logger = structlog.get_logger()


def _base_warehouse_path(lh_config: LakehouseConfig) -> str:
    prefix = lh_config.gcs_prefix.rstrip("/") if lh_config.gcs_prefix else ""
    return f"gs://{lh_config.gcs_bucket}/{prefix}" if prefix else f"gs://{lh_config.gcs_bucket}"


@lru_cache(maxsize=1)
def load_iceberg_catalog() -> Catalog:
    """
    Loads the configured Iceberg catalog (BigQuery in production deployments).
    """
    os.environ.setdefault("PYICEBERG_LEGACY_CURRENT_SNAPSHOT_ID", "true")

    config = load_config()
    if not config.lakehouse:
        raise ValueError("Lakehouse configuration is missing from datasets.yaml")

    lh_config = config.lakehouse

    catalog_type = getattr(lh_config, "catalog_type", "file")
    if catalog_type != "bigquery":
        raise ValueError(
            "BigQuery catalog requested but lakehouse.catalog_type is not set to 'bigquery'. "
            "Switch to file-based helpers instead."
        )

    if not lh_config.catalog:
        raise ValueError("BigQuery catalog not configured. Please set lakehouse.catalog.* fields.")

    # Authenticate with Google Cloud using default credentials
    default_auth()

    warehouse = _base_warehouse_path(lh_config)
    location = os.getenv("BIGQUERY_CATALOG_LOCATION", "US")

    catalog_props = {
        "type": "bigquery",
        "warehouse": warehouse,
        "gcp.bigquery.project-id": lh_config.catalog.project,
        "gcp.bigquery.dataset-id": lh_config.catalog.dataset,
        "gcp.bigquery.location": location,
    }

    catalog_name = lh_config.catalog.name
    return load_catalog(catalog_name, **catalog_props)


def load_table_from_gcs_path(metadata_location: str) -> Table:
    """
    Load an Iceberg table directly from a GCS metadata location.
    
    This bypasses the catalog system and loads the table directly from its
    metadata files in GCS. This is the recommended approach for file-based catalogs.
    
    Args:
        metadata_location: Full GCS path to the metadata.json file
            (e.g., "gs://bucket/table_name/metadata/00000-abc123.metadata.json")
    
    Returns:
        Iceberg Table object
    """
    from pyiceberg.table import load_table
    
    logger.debug(f"Loading table from GCS path: {metadata_location}")
    table = load_table(metadata_location)
    return table


def load_table_by_name(table_name: str, namespace: Optional[str] = None) -> Table:
    """
    Load an Iceberg table by name using the configured catalog.
    """
    config = load_config()
    if not config.lakehouse:
        raise ValueError("Lakehouse configuration is missing from datasets.yaml")

    catalog_type = getattr(config.lakehouse, "catalog_type", "file")

    if catalog_type == "bigquery":
        catalog = load_iceberg_catalog()
        resolved_namespace = namespace or config.lakehouse.catalog.dataset
        identifier = f"{resolved_namespace}.{table_name}"
        try:
            return catalog.load_table(identifier)
        except Exception as exc:
            raise ValueError(f"Failed to load '{identifier}' from BigQuery catalog: {exc}") from exc

    # Fallback: file-based catalog lookup
    metadata_location = get_table_path(table_name)

    if not metadata_location:
        lh_config = config.lakehouse
        base_location = _base_warehouse_path(lh_config)
        table_base_path = f"{base_location}/{table_name}"

        from .iceberg_catalog import find_latest_metadata_location, update_table_path

        metadata_location = find_latest_metadata_location(table_base_path)

        if metadata_location:
            update_table_path(table_name, metadata_location)
        else:
            raise ValueError(
                f"Table '{table_name}' not found in catalog and could not be discovered in GCS. "
                f"Expected location: {table_base_path}"
            )

    return load_table_from_gcs_path(metadata_location)


def load_file_based_catalog() -> dict:
    """
    Load the file-based catalog.
    
    Returns:
        Dictionary mapping table names to GCS metadata locations
    """
    return load_file_catalog()
