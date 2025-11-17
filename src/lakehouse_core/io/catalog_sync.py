"""
Helpers to keep file-based and BigQuery catalogs synchronized after writes.
"""

from __future__ import annotations

from typing import Optional

import structlog

from ..config import load_config
from .iceberg import load_iceberg_catalog
from .iceberg_catalog import find_latest_metadata_location, update_table_path

logger = structlog.get_logger()


def register_with_bigquery(table_name: str, metadata_location: str) -> None:
    """
    Register an Iceberg table in the configured BigQuery catalog.
    """
    config = load_config()
    lh_config = getattr(config, "lakehouse", None)
    if not lh_config:
        return

    if getattr(lh_config, "catalog_type", "file") != "bigquery":
        return

    if not lh_config.catalog:
        logger.warning("bigquery_catalog_missing", table=table_name)
        return

    catalog = load_iceberg_catalog()
    identifier = f"{lh_config.catalog.dataset}.{table_name}"

    try:
        catalog.register_table(identifier=identifier, metadata_location=metadata_location)
        logger.info("bigquery_catalog_registered", table=identifier)
    except Exception as exc:
        logger.warning("bigquery_catalog_register_failed", table=identifier, error=str(exc))


def publish_table_metadata(table_name: str, table_location: str) -> Optional[str]:
    """
    Discover the latest metadata.json for a table and update all catalogs.
    """
    metadata_location = find_latest_metadata_location(table_location)
    if not metadata_location:
        logger.warning("metadata_not_found", table=table_name, location=table_location)
        return None

    update_table_path(table_name, metadata_location)
    register_with_bigquery(table_name, metadata_location)
    return metadata_location


