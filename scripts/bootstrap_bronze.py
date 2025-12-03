"""
Bootstrap Bronze tables from consolidated parquet data.

This script migrates existing consolidated Parquet files into Bronze Iceberg tables.
It reads parquet files, creates Iceberg tables if needed, and loads the data.

Usage:
    python scripts/bootstrap_bronze.py [--table bronze.pend] [--data-dir data/consolidated]
    python scripts/bootstrap_bronze.py --all  # Bootstrap all Bronze tables

Note: Requires phoenix_lakehouse to be installed (pip install -e .)
      Requires pyarrow and pandas for reading parquet files
"""
import sys
import argparse
from pathlib import Path
from typing import Optional, List

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

try:
    import pandas as pd
    import pyarrow as pa
    import pyarrow.parquet as pq
except ImportError as e:
    print(f"❌ Failed to import required libraries: {e}")
    print("   Please install: pip install pandas pyarrow")
    sys.exit(1)

try:
    from pyiceberg.schema import Schema
    from pyiceberg.catalog import Catalog
    from pyiceberg.table import Table
except ImportError as e:
    print(f"❌ Failed to import PyIceberg: {e}")
    print("   Please install: pip install pyiceberg[gcp]>=0.10.0")
    sys.exit(1)

try:
    from lakehouse_core import get_lakehouse_config
    from lakehouse_core.catalogs import get_iceberg_catalog
    from lakehouse_core.tables import (
        get_table_contract,
        get_table_identifier,
        create_bronze_table,
    )
    from lakehouse_core.paths import get_full_gcs_path
except ImportError as e:
    print(f"❌ Failed to import lakehouse_core: {e}")
    print("   Please install phoenix_lakehouse: pip install -e .")
    sys.exit(1)


def parquet_to_iceberg_schema(parquet_path: Path) -> Schema:
    """
    Convert Parquet file schema to PyIceberg Schema.
    
    Args:
        parquet_path: Path to parquet file
    
    Returns:
        PyIceberg Schema instance
    """
    # Read parquet file to get schema
    parquet_file = pq.ParquetFile(parquet_path)
    arrow_schema = parquet_file.schema_arrow
    
    # Convert Arrow schema to PyIceberg schema
    from pyiceberg.types import NestedField
    
    # Use manual conversion - PyIceberg schema conversion APIs vary by version
    fields = []
    for i, field in enumerate(arrow_schema):
        iceberg_type = _arrow_type_to_iceberg(field.type)
        fields.append(
            NestedField(
                field_id=i + 1,
                name=field.name,
                field_type=iceberg_type,
                required=not field.nullable,
            )
        )
    return Schema(*fields)


def _arrow_type_to_iceberg(arrow_type):
    """Convert PyArrow type to PyIceberg type (simplified)."""
    from pyiceberg.types import (
        StringType, LongType, DoubleType, BooleanType,
        DateType, TimestampType, DecimalType
    )
    
    import pyarrow as pa
    
    if pa.types.is_string(arrow_type) or pa.types.is_large_string(arrow_type):
        return StringType()
    elif pa.types.is_integer(arrow_type):
        return LongType()
    elif pa.types.is_floating(arrow_type):
        return DoubleType()
    elif pa.types.is_boolean(arrow_type):
        return BooleanType()
    elif pa.types.is_date(arrow_type):
        return DateType()
    elif pa.types.is_timestamp(arrow_type):
        return TimestampType()
    elif pa.types.is_decimal(arrow_type):
        return DecimalType(arrow_type.precision, arrow_type.scale)
    else:
        # Default to string for unknown types
        return StringType()


def find_parquet_files(data_dir: Path, table_name: str) -> List[Path]:
    """
    Find all parquet files for a given table.
    
    Args:
        data_dir: Root directory containing consolidated data
        table_name: Table name (e.g., "pend" or "pml")
    
    Returns:
        List of parquet file paths
    """
    # Look for parquet files in table-specific directories
    table_dir = data_dir / table_name
    if not table_dir.exists():
        return []
    
    # Recursively find all parquet files
    parquet_files = list(table_dir.rglob("*.parquet"))
    return sorted(parquet_files)


def bootstrap_table(
    table_name: str,
    data_dir: Path,
    catalog: Catalog,
    config,
    overwrite: bool = False
) -> bool:
    """
    Bootstrap a single Bronze table from consolidated parquet data.
    
    Args:
        table_name: Full table name (e.g., "bronze.pend")
        data_dir: Directory containing consolidated parquet files
        catalog: Iceberg catalog instance
        config: Lakehouse config
        overwrite: If True, drop existing table before creating
    
    Returns:
        True if successful, False otherwise
    """
    print(f"\n{'='*60}")
    print(f"Bootstrapping: {table_name}")
    print(f"{'='*60}")
    
    # Get table contract
    contract = get_table_contract(table_name, config)
    if not contract:
        print(f"❌ Table contract not found: {table_name}")
        return False
    
    # Extract base table name (e.g., "pend" from "bronze.pend")
    _, base_name = table_name.split(".", 1)
    
    # Find parquet files
    parquet_files = find_parquet_files(data_dir, base_name)
    if not parquet_files:
        print(f"⚠️  No parquet files found in {data_dir / base_name}")
        return False
    
    print(f"📁 Found {len(parquet_files)} parquet file(s)")
    
    # Read first parquet file to get schema
    print(f"📖 Reading schema from {parquet_files[0].name}...")
    try:
        schema = parquet_to_iceberg_schema(parquet_files[0])
        print(f"✅ Schema loaded: {len(schema.fields)} fields")
    except Exception as e:
        print(f"❌ Failed to read schema: {e}")
        return False
    
    # Create table if it doesn't exist
    identifier = get_table_identifier(table_name, config)
    try:
        existing_table = catalog.load_table(identifier)
        print(f"ℹ️  Table already exists: {table_name}")
        if overwrite:
            print("🗑️  Dropping existing table...")
            catalog.drop_table(identifier)
            table = create_bronze_table(table_name, schema, config, overwrite=False)
            print(f"✅ Table recreated: {table_name}")
        else:
            table = existing_table
    except Exception:
        # Table doesn't exist, create it
        print(f"🔨 Creating table: {table_name}...")
        try:
            table = create_bronze_table(table_name, schema, config, overwrite=False)
            print(f"✅ Table created: {table_name}")
        except Exception as e:
            print(f"❌ Failed to create table: {e}")
            return False
    
    # Load data from parquet files
    print(f"📥 Loading data from {len(parquet_files)} file(s)...")
    total_rows = 0
    
    for parquet_file in parquet_files:
        try:
            # Read parquet file
            df = pd.read_parquet(parquet_file)
            rows = len(df)
            total_rows += rows
            
            # Append to Iceberg table
            # Note: This requires PyIceberg's append functionality
            # For now, we'll use a simple approach - may need adjustment
            print(f"   Loading {parquet_file.name}: {rows:,} rows...")
            
            # Convert DataFrame to PyArrow table
            arrow_table = pa.Table.from_pandas(df)
            
            # Append to Iceberg table
            # PyIceberg 0.10+ API for appending data
            try:
                # Try PyIceberg 0.10+ append API
                if hasattr(table, 'append'):
                    table.append(arrow_table)
                elif hasattr(table, 'write'):
                    # Alternative API
                    table.write(arrow_table)
                else:
                    # Use transaction API if available
                    from pyiceberg.table.metadata import INITIAL_SEQUENCE_NUMBER
                    with table.transaction() as txn:
                        txn.append(arrow_table)
            except Exception as e:
                print(f"   ⚠️  Append failed: {e}")
                print(f"   Trying alternative method...")
                # Fallback: create new snapshot manually
                # This is a simplified approach - may need adjustment
                raise NotImplementedError(
                    f"Table append failed. PyIceberg API may have changed. "
                    f"Error: {e}. Please check PyIceberg version and documentation."
                )
            
        except Exception as e:
            print(f"   ❌ Failed to load {parquet_file.name}: {e}")
            return False
    
    print(f"✅ Successfully loaded {total_rows:,} rows into {table_name}")
    return True


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Bootstrap Bronze tables from consolidated parquet data"
    )
    parser.add_argument(
        "--table",
        type=str,
        help="Specific table to bootstrap (e.g., bronze.pend)",
    )
    parser.add_argument(
        "--all",
        action="store_true",
        help="Bootstrap all Bronze tables",
    )
    parser.add_argument(
        "--data-dir",
        type=str,
        default="data/consolidated",
        help="Directory containing consolidated parquet files (default: data/consolidated)",
    )
    parser.add_argument(
        "--overwrite",
        action="store_true",
        help="Overwrite existing tables",
    )
    
    args = parser.parse_args()
    
    # Load configuration
    try:
        config = get_lakehouse_config()
        catalog = get_iceberg_catalog()
    except Exception as e:
        print(f"❌ Failed to initialize catalog: {e}")
        sys.exit(1)
    
    # Determine which tables to bootstrap
    data_dir = Path(args.data_dir)
    if not data_dir.exists():
        print(f"❌ Data directory not found: {data_dir}")
        sys.exit(1)
    
    if args.all:
        # Find all Bronze tables
        bronze_tables = [
            name for name in config.tables.keys()
            if name.startswith("bronze.")
        ]
        if not bronze_tables:
            print("❌ No Bronze tables found in configuration")
            sys.exit(1)
        tables_to_bootstrap = bronze_tables
    elif args.table:
        tables_to_bootstrap = [args.table]
    else:
        print("❌ Please specify --table or --all")
        parser.print_help()
        sys.exit(1)
    
    # Bootstrap each table
    success_count = 0
    for table_name in tables_to_bootstrap:
        if bootstrap_table(table_name, data_dir, catalog, config, args.overwrite):
            success_count += 1
    
    # Summary
    print(f"\n{'='*60}")
    print(f"Bootstrap complete: {success_count}/{len(tables_to_bootstrap)} tables succeeded")
    print(f"{'='*60}")
    
    if success_count < len(tables_to_bootstrap):
        sys.exit(1)


if __name__ == "__main__":
    main()

