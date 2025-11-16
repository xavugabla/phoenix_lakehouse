"""
Consolidation task for CENACE PEND data.

Merges staged partitions and appends them to the Iceberg Lakehouse table.
"""
from typing import List, Optional, Dict
import pandas as pd
from prefect import task
import structlog

from pipeline_tasks.config import load_config
from pipeline_tasks.io.local import read_parquet
from pipeline_tasks.io.catalog_sync import publish_table_metadata
from pyiceberg.catalog import load_catalog
import pyarrow as pa

logger = structlog.get_logger()


@task(name="consolidate_cenace_pend", retries=2, log_prints=True)
def consolidate_cenace_pend(
    staged_partitions: List[str],
    config_path: Optional[str] = None
) -> Dict[str, int]:
    """
    Consolidates staged PEND data and appends it to the 'pend' Iceberg table.

    Args:
        staged_partitions: A list of paths to staged Parquet files.
        config_path: An optional path to the configuration file.

    Returns:
        A dictionary containing the count of rows appended to the table.
    """
    if not staged_partitions:
        logger.warning("No staged partitions provided for consolidation.")
        return {"rows_appended": 0}

    logger.info(f"Consolidating {len(staged_partitions)} staged PEND partitions.")

    try:
        # Load all staged data into a single DataFrame
        dfs = [read_parquet(path) for path in staged_partitions]
        if not dfs:
            logger.warning("No data found in staged partitions.")
            return {"rows_appended": 0}
        
        combined_df = pd.concat(dfs, ignore_index=True)

        # --- Data Cleaning and Schema Alignment ---
        # Ensure timestamp is in the correct format (timezone-aware UTC)
        if 'timestamp' in combined_df.columns:
            combined_df['timestamp'] = pd.to_datetime(combined_df['timestamp'], utc=True)
        
        # Add 'system' column if it's missing (required by Iceberg schema)
        # This can be inferred or defaulted based on your system's logic
        if 'system' not in combined_df.columns and 'region' in combined_df.columns:
             # A simple logic to map region to system, can be improved
            combined_df['system'] = combined_df['region'].apply(
                lambda r: 'BCS' if r == 'BCS' else ('BCA' if r == 'BCA' else 'SIN')
            )
        
        # Ensure all required columns from the master schema exist
        # PyIceberg will handle type casting, but column presence is important
        # This step is simplified as PyIceberg's schema enforcement is strict

        logger.info(f"Consolidated into a DataFrame with {len(combined_df)} rows.")

        # --- Load Iceberg Table and Append Data ---
        config = load_config(config_path)
        if not config.lakehouse:
            raise ValueError("Lakehouse configuration not found in settings.")

        # Use in-memory catalog for writes (BigQuery catalog doesn't support writes)
        namespace = config.lakehouse.catalog.dataset
        prefix = config.lakehouse.gcs_prefix.rstrip("/") if config.lakehouse.gcs_prefix else ""
        base_location = f"gs://{config.lakehouse.gcs_bucket}/{prefix}" if prefix else f"gs://{config.lakehouse.gcs_bucket}"
        table_identifier = f"{namespace}.pend"
        
        write_catalog = load_catalog(
            "consolidation_write_catalog",
            **{
                "type": "in-memory",
                "warehouse": base_location,
            }
        )
        
        # Create namespace if needed
        try:
            write_catalog.create_namespace(namespace)
        except Exception:
            pass  # Namespace already exists
        
        # Create table if it doesn't exist
        from pipeline_tasks.schemas.master_schemas import MASTER_SCHEMAS
        from pyiceberg.exceptions import NoSuchTableError
        
        schema = MASTER_SCHEMAS["pend"]
        table_location = f"{base_location}/pend"
        
        # Ensure table exists - create if needed
        try:
            table = write_catalog.load_table(table_identifier)
            logger.debug(f"Iceberg table '{table_identifier}' already exists")
        except NoSuchTableError:
            # Table doesn't exist, create it
            try:
                write_catalog.create_table(
                    identifier=table_identifier,
                    schema=schema,
                    location=table_location
                )
                logger.info(f"Created Iceberg table '{table_identifier}' at {table_location}")
                table = write_catalog.load_table(table_identifier)
            except Exception as create_error:
                logger.error(
                    f"Failed to create Iceberg table '{table_identifier}'",
                    error=str(create_error),
                    location=table_location
                )
                raise ValueError(
                    f"Cannot proceed without Iceberg table. "
                    f"Failed to create '{table_identifier}': {create_error}"
                ) from create_error
        
        # Convert to PyArrow and fix nullable issues
        combined_pa = pa.Table.from_pandas(combined_df)
        schema_pa = combined_pa.schema
        fields = []
        for field in schema_pa:
            # Check if required in Iceberg schema
            iceberg_field = next((f for f in schema.fields if f.name == field.name), None)
            if iceberg_field and iceberg_field.required:
                fields.append(pa.field(field.name, field.type, nullable=False))
            else:
                fields.append(field)
        schema_pa = pa.schema(fields)
        combined_pa = combined_pa.cast(schema_pa)

        logger.info(f"Appending {len(combined_df)} rows to the Iceberg table...")
        table.append(combined_pa)
        
        logger.info("Successfully appended data to the Iceberg table.")
        
        publish_table_metadata("pend", table_location)

        return {"rows_appended": len(combined_df)}

    except Exception as e:
        logger.error("Failed during PEND consolidation and Iceberg append", exc_info=e)
        raise

