"""
Main daily Prefect flow for CENACE data pipeline.

Orchestrates extraction → transformation → consolidation → Iceberg write.

ARCHITECTURE:
- Extraction: Reads from JSON catalogues (for entity lists)
- Transformation: Stages data locally
- Consolidation: Writes directly to Iceberg tables in the Lakehouse
- No GCS sync needed - consolidation tasks handle Iceberg writes directly
"""
from datetime import datetime, timedelta
from typing import Optional
from prefect import flow
import structlog

from pipeline_tasks.extraction import cenace_pml, cenace_pend, cenace_psc
from pipeline_tasks.transform import cenace_pml as transform_pml, cenace_pend as transform_pend, cenace_psc as transform_psc
from pipeline_tasks.consolidate import cenace_pend as consolidate_pend, cenace_psc as consolidate_psc, cenace_pml as consolidate_pml
from pipeline_tasks.utils.git_pull import pull_latest_code

logger = structlog.get_logger()


@flow(name="cenace-daily", log_prints=True)
def cenace_daily_flow(
    run_date: Optional[datetime] = None,
    regions: Optional[list[str]] = None,
    markets: Optional[list[str]] = None,
    datasets: Optional[list[str]] = None,
    config_path: Optional[str] = None
):
    """
    Daily CENACE data pipeline flow.
    
    This flow extracts, transforms, and consolidates data directly into Iceberg tables.
    Consolidation tasks handle Iceberg writes automatically - no separate GCS sync needed.
    
    Args:
        run_date: Date to run for (defaults to yesterday)
        regions: List of regions to process (defaults to ['SIN'])
        markets: List of markets to process (defaults to ['MDA', 'MTR'])
        datasets: List of datasets to process (defaults to ['pend', 'psc'])
        config_path: Optional path to config file
    
    Returns:
        Dictionary with total rows appended to Iceberg and run date
    """
    if run_date is None:
        run_date = datetime.utcnow() - timedelta(days=1)
    
    if regions is None:
        regions = ['SIN']
    
    if markets is None:
        markets = ['MDA', 'MTR']
    
    if datasets is None:
        datasets = ['pend', 'psc']  # Start with PEND and PSC, add PML later
    
    # Date range: single day
    start_date = run_date.replace(hour=0, minute=0, second=0, microsecond=0)
    end_date = start_date + timedelta(days=1)
    
    logger.info(
        "flow_started",
        run_date=run_date.isoformat(),
        regions=regions,
        markets=markets,
        datasets=datasets
    )
    
    # Pull latest code from git repository
    git_result = pull_latest_code()
    if git_result['success']:
        logger.info("git_pull_success", output=git_result.get('output', ''))
    else:
        logger.warning("git_pull_failed", error=git_result.get('error', ''), continue_anyway=True)
    
    total_rows_appended = 0
    datasets_processed = 0
    
    # Process each dataset
    for dataset in datasets:
        for region in regions:
            for market in markets:
                try:
                    if dataset == 'pend':
                        # Extract PEND
                        raw_batch = cenace_pend.extract_cenace_pend(
                            region=region,
                            market=market,
                            start_date=start_date,
                            end_date=end_date,
                            config_path=config_path
                        )
                        
                        # Transform PEND
                        staged_partitions = transform_pend.transform_cenace_pend(
                            raw_batch_path=raw_batch.raw_path,
                            config_path=config_path
                        )
                        
                        # Consolidate PEND (writes directly to Iceberg)
                        if staged_partitions:
                            partition_paths = [p.staged_path for p in staged_partitions]
                            result = consolidate_pend.consolidate_cenace_pend(
                                staged_partitions=partition_paths,
                                config_path=config_path
                            )
                            rows_appended = result.get("rows_appended", 0)
                            total_rows_appended += rows_appended
                            datasets_processed += 1
                            logger.info(
                                "pend_consolidated",
                                region=region,
                                market=market,
                                rows_appended=rows_appended
                            )
                    
                    elif dataset == 'psc':
                        # Extract PSC
                        raw_batch = cenace_psc.extract_cenace_psc(
                            region=region,
                            market=market,
                            start_date=start_date,
                            end_date=end_date,
                            config_path=config_path
                        )
                        
                        # Transform PSC
                        staged_partitions = transform_psc.transform_cenace_psc(
                            raw_batch_path=raw_batch.raw_path,
                            config_path=config_path
                        )
                        
                        # Consolidate PSC (writes directly to Iceberg)
                        if staged_partitions:
                            partition_paths = [p.staged_path for p in staged_partitions]
                            result = consolidate_psc.consolidate_cenace_psc(
                                staged_partitions=partition_paths,
                                config_path=config_path
                            )
                            rows_appended = result.get("rows_appended", 0)
                            total_rows_appended += rows_appended
                            datasets_processed += 1
                            logger.info(
                                "psc_consolidated",
                                region=region,
                                market=market,
                                rows_appended=rows_appended
                            )
                    
                    elif dataset == 'pml':
                        # Extract PML
                        raw_batch = cenace_pml.extract_cenace_pml(
                            region=region,
                            market=market,
                            start_date=start_date,
                            end_date=end_date,
                            config_path=config_path
                        )
                        
                        # Transform PML
                        staged_partitions = transform_pml.transform_cenace_pml(
                            raw_batch_path=raw_batch.raw_path,
                            config_path=config_path
                        )
                        
                        # Consolidate PML (writes directly to Iceberg)
                        if staged_partitions:
                            partition_paths = [p.staged_path for p in staged_partitions]
                            result = consolidate_pml.consolidate_cenace_pml(
                                staged_partitions=partition_paths,
                                config_path=config_path
                            )
                            rows_appended = result.get("rows_appended", 0)
                            total_rows_appended += rows_appended
                            datasets_processed += 1
                            logger.info(
                                "pml_consolidated",
                                region=region,
                                market=market,
                                rows_appended=rows_appended
                            )
                
                except Exception as e:
                    logger.error(
                        "flow_error",
                        dataset=dataset,
                        region=region,
                        market=market,
                        error=str(e)
                    )
                    continue
    
    # Log completion - data is already in Iceberg tables
    logger.info(
        "flow_complete",
        total_rows_appended=total_rows_appended,
        datasets_processed=datasets_processed,
        run_date=run_date.isoformat()
    )
    
    return {
        'total_rows_appended': total_rows_appended,
        'datasets_processed': datasets_processed,
        'run_date': run_date.isoformat()
    }


if __name__ == "__main__":
    # Run flow for yesterday
    result = cenace_daily_flow()
    print(f"Flow completed: {result}")

