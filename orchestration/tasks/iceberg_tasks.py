from datetime import datetime
from prefect import task
import structlog
import pandas as pd

from pipeline_tasks.io.iceberg import load_table_by_name
from pipeline_tasks.config import load_config
from pyiceberg.exceptions import NoSuchTableError

logger = structlog.get_logger()

@task(name="get_latest_iceberg_timestamp")
def get_latest_iceberg_timestamp(dataset: str, region: str, market: str) -> datetime:
    """
    Queries an Iceberg table to find the latest timestamp for a given
    region and market, which is used to determine the start date for a new
    backfill run.

    Uses file-based catalog by default, falling back to BigQuery catalog if configured.

    Args:
        dataset: The dataset name (e.g., 'pend') which corresponds to the table name.
        region: The specific region to filter by (e.g., 'SIN').
        market: The specific market to filter by (e.g., 'MDA').

    Returns:
        The latest timestamp found in the table for the given filters.
        If table doesn't exist or no data is found, returns a default start date (30 days ago).
    """
    logger.info(f"Querying Iceberg table '{dataset}' for latest timestamp...", dataset=dataset, region=region, market=market)
    
    config = load_config()
    if not config.lakehouse:
        raise ValueError("Lakehouse configuration not found in settings.")
    
    try:
        table = load_table_by_name(dataset)
        
        # Scan the table to find the max timestamp for the specified slice
        # Using to_pandas for simplicity, but for very large tables,
        # a more direct query engine (like DuckDB) would be more performant.
        df = table.scan(
            row_filter=f"region = '{region}' AND market = '{market}'",
            selected_fields=("timestamp",)
        ).to_pandas()

        if df.empty:
            logger.warning("No existing data found for this region/market. Starting from 30 days ago.")
            return datetime.utcnow() - pd.Timedelta(days=30)

        latest_ts = df['timestamp'].max()
        logger.info(f"Latest timestamp found: {latest_ts}")
        return latest_ts

    except (NoSuchTableError, ValueError) as e:
        logger.info(f"Table '{dataset}' does not exist yet or not found: {e}. Starting from 30 days ago.")
        return datetime.utcnow() - pd.Timedelta(days=30)
    except Exception as e:
        logger.error("Failed to query latest timestamp from Iceberg", exc_info=e)
        logger.warning("Defaulting to a start date of 30 days ago due to error.")
        return datetime.utcnow() - pd.Timedelta(days=30)
