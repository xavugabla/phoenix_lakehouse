"""
Backfill Prefect flow for historical data collection.

This flow is designed to run against the new Iceberg Lakehouse architecture.
It automatically determines the last ingested date from the target Iceberg table
and fetches new data from that point forward.
"""
from datetime import datetime, timedelta
from typing import Optional
from prefect import flow, task
import structlog

from lakehouse_core.extraction import cenace_pml, cenace_pend, cenace_psc
from lakehouse_core.transform import (
    cenace_pml as transform_pml, 
    cenace_pend as transform_pend, 
    cenace_psc as transform_psc
)
from lakehouse_core.consolidate import (
    cenace_pend as consolidate_pend, 
    cenace_psc as consolidate_psc, 
    cenace_pml as consolidate_pml
)
from lakehouse_core.extraction.helpers import chunk_date_range
from lakehouse_core.utils.git_pull import pull_latest_code
from lakehouse_core.config import load_config
from orchestration.tasks.iceberg_tasks import get_latest_iceberg_timestamp

logger = structlog.get_logger()


@flow(name="cenace-backfill-lakehouse", log_prints=True)
def backfill_flow(
    dataset: str,
    region: str,
    market: str,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    config_path: Optional[str] = None,
    chunk_days: int = 7,
    zones_limit: Optional[int] = None,
    nodes_limit: Optional[int] = None,
):
    """
    Backfill flow for ingesting data into the Iceberg Lakehouse.

    If a start_date is not provided, the flow will query the target Iceberg
    table to find the most recent timestamp and start the backfill from there.

    Args:
        dataset: Dataset name ('pml', 'pend', or 'psc')
        region: Region (SIN, BCA, BCS)
        market: Market (MDA, MTR)
        start_date: Optional start date. If None, auto-detects from Iceberg.
        end_date: Optional end date. Defaults to yesterday.
        config_path: Optional path to config file
        chunk_days: Number of days per chunk (default: 7)
        zones_limit: Optional limit on number of zones to extract (for PEND/PSC)
        nodes_limit: Optional limit on number of nodes to extract (for PML)
    """
    load_config(config_path) # Load config once at the beginning
    
    # --- Determine Date Range ---
    if end_date is None:
        end_date = datetime.utcnow() - timedelta(days=1)
    
    if start_date is None:
        # Auto-detect start date from Iceberg table
        latest_ts = get_latest_iceberg_timestamp(dataset=dataset, region=region, market=market)
        start_date = latest_ts + timedelta(days=1)
    
    if start_date >= end_date:
        logger.info(f"Data is already up to date for {dataset} {region} {market}. No backfill needed.")
        return {"total_rows_appended": 0, "chunks_processed": 0}

    logger.info(
        "Starting Lakehouse backfill...",
        dataset=dataset,
        region=region,
        market=market,
        start=start_date.isoformat(),
        end=end_date.isoformat(),
    )

    date_chunks = chunk_date_range(start_date, end_date, max_days=chunk_days)
    logger.info(f"Processing data in {len(date_chunks)} chunk(s).")
    
    total_rows_appended = 0
    
    for chunk_start, chunk_end in date_chunks:
        try:
            logger.info(f"Processing chunk: {chunk_start.date()} to {chunk_end.date()}")

            staged_partitions = []
            if dataset == 'pend':
                raw_batch = cenace_pend.extract_cenace_pend(
                    region=region, market=market, start_date=chunk_start,
                    end_date=chunk_end, zones_limit=zones_limit
                )
                staged_paths = transform_pend.transform_cenace_pend(raw_batch_path=raw_batch.raw_path)
                staged_partitions = [p.staged_path for p in staged_paths]
                result = consolidate_pend.consolidate_cenace_pend(staged_partitions=staged_partitions)

            elif dataset == 'psc':
                raw_batch = cenace_psc.extract_cenace_psc(
                    region=region, market=market, start_date=chunk_start, end_date=chunk_end
                )
                staged_paths = transform_psc.transform_cenace_psc(raw_batch_path=raw_batch.raw_path)
                staged_partitions = [p.staged_path for p in staged_paths]
                result = consolidate_psc.consolidate_cenace_psc(staged_partitions=staged_partitions)

            elif dataset == 'pml':
                raw_batch = cenace_pml.extract_cenace_pml(
                    region=region, market=market, start_date=chunk_start,
                    end_date=chunk_end, nodes_limit=nodes_limit
                )
                staged_paths = transform_pml.transform_cenace_pml(raw_batch_path=raw_batch.raw_path)
                staged_partitions = [p.staged_path for p in staged_paths]
                result = consolidate_pml.consolidate_cenace_pml(staged_partitions=staged_partitions)
            
            rows_appended = result.get("rows_appended", 0)
            total_rows_appended += rows_appended
            logger.info(f"Chunk completed. Appended {rows_appended} rows to Iceberg.")

        except Exception as e:
            logger.error(f"Failed to process chunk {chunk_start.date()} to {chunk_end.date()}", exc_info=e)
            continue
    
    logger.info(
        "Lakehouse backfill complete!",
        total_rows_appended=total_rows_appended,
        chunks_processed=len(date_chunks)
    )
    
    return {
        "total_rows_appended": total_rows_appended,
        "chunks_processed": len(date_chunks)
    }

if __name__ == "__main__":
    backfill_flow(
        dataset='pend',
        region='SIN',
        market='MDA',
        # Let the flow auto-detect the start date
        end_date=datetime.utcnow() - timedelta(days=1)
    )

