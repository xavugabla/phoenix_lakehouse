"""
Prefect flow for migrating local consolidated data into the Iceberg Lakehouse.

This is a one-time migration script designed to:
1. Scan the local `data/consolidated` directory for a given dataset.
2. Read all existing Parquet files.
3. Rigorously conform the data to the official master schema.
4. Append the cleaned data to the corresponding Iceberg table.
"""
import sys
from pathlib import Path
import pandas as pd
from prefect import flow, task, get_run_logger

# Add 'src' to the Python path to find pipeline_tasks
src_path = Path(__file__).resolve().parent.parent.parent / "src"
if str(src_path) not in sys.path:
    sys.path.insert(0, str(src_path))

from pipeline_tasks.config import load_config
from pipeline_tasks.io.iceberg import load_iceberg_catalog
from pipeline_tasks.schemas.master_schemas import MASTER_SCHEMAS
from pyiceberg.catalog import load_catalog
from pyiceberg.exceptions import TableAlreadyExistsError
import pyarrow as pa

@task
def conform_df_to_schema(df: pd.DataFrame, schema_name: str) -> pd.DataFrame:
    """
    Conforms a DataFrame to the specified master Iceberg schema.

    This involves selecting the correct columns, ensuring they are in the
    right order, and casting them to the appropriate data types.

    Args:
        df: The input DataFrame.
        schema_name: The name of the master schema to conform to (e.g., 'pend').

    Returns:
        A new DataFrame that matches the target schema.
    """
    logger = get_run_logger()
    logger.info(f"Conforming DataFrame to master schema: '{schema_name}'")
    
    iceberg_schema = MASTER_SCHEMAS.get(schema_name)
    if not iceberg_schema:
        raise ValueError(f"Master schema '{schema_name}' not found.")
        
    # Create a mapping from Iceberg field name to pandas dtype
    # This is a simplified mapping; more complex types may need specific handling.
    dtype_map = {
        'string': 'object',
        'timestamp': 'datetime64[ns, UTC]',
        'float': 'float64',
        'double': 'float64',
        'int': 'Int64', # Use nullable integer type
        'long': 'Int64',
    }
    
    target_columns = {field.name: dtype_map.get(str(field.type)) for field in iceberg_schema.fields}
    
    # Select only the columns that are in the target schema
    conformed_df = df[[col for col in target_columns if col in df.columns]].copy()

    # Add any missing columns with None
    for col in target_columns:
        if col not in conformed_df.columns:
            logger.warning(f"Column '{col}' not found in source data. Adding as empty column.")
            conformed_df[col] = None

    # Cast columns to the correct types
    for col, dtype in target_columns.items():
        if dtype:
            try:
                if 'datetime' in dtype:
                    conformed_df[col] = pd.to_datetime(conformed_df[col], utc=True)
                else:
                    conformed_df[col] = conformed_df[col].astype(dtype)
            except Exception as e:
                logger.error(f"Failed to cast column '{col}' to type '{dtype}'.", exc_info=e)
                raise
                
    # Ensure column order matches the schema
    conformed_df = conformed_df[list(target_columns.keys())]
    
    logger.info("DataFrame successfully conformed to schema.")
    return conformed_df


@flow(name="migrate-local-to-lakehouse", log_prints=True)
def migrate_local_to_lakehouse_flow(dataset: str):
    """
    Scans, conforms, and loads local data for one dataset into the Lakehouse.

    Args:
        dataset: The dataset to migrate (e.g., 'pend', 'pml', 'psc').
    """
    logger = get_run_logger()
    logger.info(f"🚀 Starting local data migration for dataset: '{dataset}'")
    
    config = load_config()
    consolidated_root = Path(config.consolidated_root)
    dataset_path = consolidated_root / dataset

    if not dataset_path.exists():
        logger.warning(f"Local data directory not found for dataset '{dataset}'. Skipping.")
        return {"rows_migrated": 0}

    # 1. Scan for local Parquet files
    local_files = list(dataset_path.rglob("*.parquet"))
    if not local_files:
        logger.info(f"No local .parquet files found for '{dataset}'. Nothing to migrate.")
        return {"rows_migrated": 0}
        
    logger.info(f"Found {len(local_files)} local Parquet files to migrate.")

    # 2. Read and concatenate
    df = pd.concat([pd.read_parquet(f) for f in local_files], ignore_index=True)
    logger.info(f"Loaded a total of {len(df)} rows from local files.")

    # 3. Conform to master schema
    conformed_df = conform_df_to_schema(df=df, schema_name=dataset)

    # 4. Load into Iceberg
    if not config.lakehouse:
        raise ValueError("Lakehouse configuration not found in settings.")

    # IMPORTANT: BigQuery catalog doesn't support writes, so we use in-memory catalog
    # The metadata files written to GCS will be discoverable by BigQuery
    namespace = config.lakehouse.catalog.dataset
    # Handle empty prefix - tables go directly in bucket root
    prefix = config.lakehouse.gcs_prefix.rstrip("/") if config.lakehouse.gcs_prefix else ""
    base_location = f"gs://{config.lakehouse.gcs_bucket}/{prefix}" if prefix else f"gs://{config.lakehouse.gcs_bucket}"
    table_identifier = f"{namespace}.{dataset}"
    
    # Use in-memory catalog for writes (supports transactions)
    write_catalog = load_catalog(
        "migration_write_catalog",
        **{
            "type": "in-memory",
            "warehouse": base_location,
        }
    )
    
    # Create namespace if it doesn't exist
    try:
        write_catalog.create_namespace(namespace)
        logger.info(f"Created namespace '{namespace}' in write catalog.")
    except Exception:
        logger.info(f"Namespace '{namespace}' already exists in write catalog.")
    
    # Create table if it doesn't exist
    schema = MASTER_SCHEMAS[dataset]
    table_location = f"{base_location}/{dataset}"
    
    try:
        write_catalog.create_table(
            identifier=table_identifier,
            schema=schema,
            location=table_location
        )
        logger.info(f"✅ Created Iceberg table '{table_identifier}' at {table_location}")
    except TableAlreadyExistsError:
        logger.info(f"✅ Table '{table_identifier}' already exists.")
    
    # Load the table
    table = write_catalog.load_table(table_identifier)
    
    # Convert DataFrame to PyArrow table
    conformed_pa = pa.Table.from_pandas(conformed_df)
    
    # Fix nullable issues for required fields
    schema_pa = conformed_pa.schema
    fields = []
    for field in schema_pa:
        # Check if this field is required in the Iceberg schema
        iceberg_field = next((f for f in schema.fields if f.name == field.name), None)
        if iceberg_field and iceberg_field.required:
            fields.append(pa.field(field.name, field.type, nullable=False))
        else:
            fields.append(field)
    schema_pa = pa.schema(fields)
    conformed_pa = conformed_pa.cast(schema_pa)
    
    logger.info(f"Appending {len(conformed_df)} conformed rows to the Iceberg table...")
    table.overwrite(conformed_pa)  # Use overwrite for migration (replaces existing data)
    
    logger.info("✅ Successfully migrated local data to the Iceberg table.")
    logger.info(f"   Data location: {table_location}")
    logger.info(f"   Table will be queryable via BigQuery catalog: {table_identifier}")
    
    return {"rows_migrated": len(conformed_df)}

if __name__ == "__main__":
    # --- IMPORTANT ---
    # Run this flow once for each dataset you have local data for.
    # For example:
    migrate_local_to_lakehouse_flow(dataset="pend")
    # migrate_local_to_lakehouse_flow(dataset="pml")
    # migrate_local_to_lakehouse_flow(dataset="psc")
