"""
Helper functions for extraction tasks.
"""
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Union

import pandas as pd
import structlog

from lakehouse_core.config import load_config
from lakehouse_core.io.iceberg import load_table_by_name

logger = structlog.get_logger()


def resolve_catalog_path(catalog_path: str) -> Path:
    """
    Resolve catalog path relative to project root.
    
    Tries multiple strategies:
    1. Use path as-is if absolute
    2. Try relative to current working directory
    3. Try relative to project root (where configs/ and catalogues/ are)
    
    Args:
        catalog_path: Catalog file path (relative or absolute)
    
    Returns:
        Resolved Path object
    
    Raises:
        FileNotFoundError: If catalog file cannot be found
    """
    catalog_file = Path(catalog_path)
    
    # If absolute path and exists, use it
    if catalog_file.is_absolute() and catalog_file.exists():
        return catalog_file
    
    # Try relative to current working directory
    if catalog_file.exists():
        return catalog_file.resolve()
    
    # Try relative to project root (where this file is: src/lakehouse_core/extraction/)
    # Project root is 3 levels up: src/lakehouse_core/extraction -> src -> project root
    project_root = Path(__file__).parent.parent.parent
    project_catalog = project_root / catalog_path
    
    if project_catalog.exists():
        return project_catalog.resolve()
    
    # Try common alternative locations
    candidates = [
        project_root / catalog_path,
        Path.cwd() / catalog_path,
        Path.cwd().parent / catalog_path,
    ]
    
    for candidate in candidates:
        if candidate.exists():
            return candidate.resolve()
    
    # If still not found, provide helpful error
    raise FileNotFoundError(
        f"Catalog file not found: {catalog_path}\n"
        f"Tried:\n"
        f"  - {catalog_file.resolve()}\n"
        f"  - {project_catalog}\n"
        f"  - {Path.cwd() / catalog_path}\n"
        f"Current working directory: {Path.cwd()}\n"
        f"Project root (estimated): {project_root}"
    )


def chunk_date_range(start_date: datetime, end_date: datetime, max_days: int = 7) -> List[Tuple[datetime, datetime]]:
    """
    Split a date range into chunks of max_days.
    
    Args:
        start_date: Start date
        end_date: End date
        max_days: Maximum days per chunk
    
    Returns:
        List of (start, end) tuples
    """
    chunks = []
    current = start_date
    
    while current < end_date:
        chunk_end = min(current + timedelta(days=max_days - 1), end_date)
        chunks.append((current, chunk_end))
        current = chunk_end + timedelta(days=1)
    
    return chunks


def fetch_catalog_dataframe(
    table_name: str,
    columns: List[str],
    filters: Optional[Dict[str, Union[str, List[str]]]] = None,
) -> Optional[pd.DataFrame]:
    """
    Load entity metadata from the BigQuery-backed Iceberg catalog.

    Returns a pandas DataFrame or None if the catalog isn't configured.
    """
    config = load_config()
    lakehouse = getattr(config, "lakehouse", None)
    if not lakehouse or getattr(lakehouse, "catalog_type", "file") != "bigquery":
        return None

    try:
        table = load_table_by_name(table_name)
    except Exception as exc:
        logger.warning("catalog_table_load_failed", table=table_name, error=str(exc))
        return None

    scan = table.scan(selected_fields=tuple(columns))
    df = scan.to_pandas()

    if filters:
        for column, value in filters.items():
            if column not in df.columns:
                continue
            if isinstance(value, list):
                df = df[df[column].isin(value)]
            else:
                df = df[df[column] == value]

    return df.reset_index(drop=True)

