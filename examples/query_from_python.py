"""
Example: Querying Iceberg tables from Python using PyIceberg.

This example shows how to query Iceberg tables directly from GCS
without requiring BigQuery or any catalog service.
"""
import sys
from pathlib import Path

# Add 'src' to the Python path
src_path = Path(__file__).resolve().parent.parent / "src"
if str(src_path) not in sys.path:
    sys.path.insert(0, str(src_path))

from pipeline_tasks.io.iceberg import load_table_by_name, load_table_from_gcs_path
from pipeline_tasks.io.iceberg_catalog import get_table_path, find_latest_metadata_location
import pandas as pd


def example_query_by_name():
    """Example: Query table by name using file-based catalog."""
    print("=" * 70)
    print("Example 1: Query table by name")
    print("=" * 70)
    
    try:
        # Load table using file-based catalog
        table = load_table_by_name("pend")
        
        # Query with filters
        df = table.scan(
            row_filter="region = 'SIN' AND market = 'MDA'",
            selected_fields=("timestamp", "zone", "price"),
            limit=10
        ).to_pandas()
        
        print(f"\nFound {len(df)} rows")
        print(df.head())
        
    except Exception as e:
        print(f"Error: {e}")


def example_query_by_path():
    """Example: Query table using direct GCS path."""
    print("\n" + "=" * 70)
    print("Example 2: Query table using direct GCS path")
    print("=" * 70)
    
    # Get metadata location from catalog
    metadata_location = get_table_path("pend")
    
    if metadata_location:
        print(f"\nMetadata location: {metadata_location}")
        
        # Load table directly from GCS
        table = load_table_from_gcs_path(metadata_location)
        
        # Query table
        df = table.scan(limit=5).to_pandas()
        print(f"\nFound {len(df)} rows")
        print(df.head())
    else:
        print("Table 'pend' not found in catalog")


def example_find_latest_timestamp():
    """Example: Find latest timestamp in a table."""
    print("\n" + "=" * 70)
    print("Example 3: Find latest timestamp")
    print("=" * 70)
    
    try:
        table = load_table_by_name("pend")
        
        # Get latest timestamp for a specific region/market
        df = table.scan(
            row_filter="region = 'SIN' AND market = 'MDA'",
            selected_fields=("timestamp",)
        ).to_pandas()
        
        if not df.empty:
            latest_ts = df['timestamp'].max()
            print(f"\nLatest timestamp: {latest_ts}")
        else:
            print("\nNo data found")
            
    except Exception as e:
        print(f"Error: {e}")


def example_discover_metadata():
    """Example: Discover metadata location for a table."""
    print("\n" + "=" * 70)
    print("Example 4: Discover metadata location")
    print("=" * 70)
    
    table_base_path = "gs://lakehouse_phoenix/pend"
    metadata_location = find_latest_metadata_location(table_base_path)
    
    if metadata_location:
        print(f"\nFound metadata: {metadata_location}")
    else:
        print(f"\nNo metadata found at {table_base_path}")


if __name__ == "__main__":
    print("Iceberg Query Examples")
    print("=" * 70)
    
    # Run examples
    example_query_by_name()
    example_query_by_path()
    example_find_latest_timestamp()
    example_discover_metadata()
    
    print("\n" + "=" * 70)
    print("Examples complete!")

