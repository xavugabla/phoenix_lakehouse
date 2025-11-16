"""
Example: Querying Iceberg tables using DuckDB.

DuckDB can query Iceberg tables directly from GCS, providing
excellent performance for analytical queries.
"""
import sys
from pathlib import Path

# Add 'src' to the Python path
src_path = Path(__file__).resolve().parent.parent / "src"
if str(src_path) not in sys.path:
    sys.path.insert(0, str(src_path))

try:
    import duckdb
except ImportError:
    print("DuckDB not installed. Install with: pip install duckdb duckdb-iceberg")
    sys.exit(1)

from pipeline_tasks.io.iceberg_catalog import get_table_path


def example_duckdb_query():
    """Example: Query Iceberg table with DuckDB."""
    print("=" * 70)
    print("Example: Querying Iceberg with DuckDB")
    print("=" * 70)
    
    # Get metadata location
    metadata_location = get_table_path("pend")
    
    if not metadata_location:
        print("Table 'pend' not found in catalog")
        return
    
    print(f"\nMetadata location: {metadata_location}")
    
    # Connect to DuckDB
    conn = duckdb.connect()
    
    try:
        # Query Iceberg table
        # Note: DuckDB Iceberg extension syntax may vary
        # This is a conceptual example - actual syntax depends on DuckDB version
        query = f"""
        SELECT 
            timestamp,
            zone,
            price,
            region,
            market
        FROM read_iceberg('{metadata_location}')
        WHERE region = 'SIN' AND market = 'MDA'
        ORDER BY timestamp DESC
        LIMIT 10
        """
        
        result = conn.execute(query).fetchdf()
        
        print(f"\nFound {len(result)} rows")
        print(result)
        
    except Exception as e:
        print(f"Error querying with DuckDB: {e}")
        print("\nNote: DuckDB Iceberg extension may need to be loaded:")
        print("  conn.execute(\"INSTALL iceberg; LOAD iceberg;\")")
    finally:
        conn.close()


def example_duckdb_aggregations():
    """Example: Complex aggregations with DuckDB."""
    print("\n" + "=" * 70)
    print("Example: Complex aggregations with DuckDB")
    print("=" * 70)
    
    metadata_location = get_table_path("pend")
    
    if not metadata_location:
        print("Table 'pend' not found in catalog")
        return
    
    conn = duckdb.connect()
    
    try:
        # Aggregation query
        query = f"""
        SELECT 
            region,
            market,
            COUNT(*) as row_count,
            MIN(timestamp) as earliest,
            MAX(timestamp) as latest,
            AVG(price) as avg_price
        FROM read_iceberg('{metadata_location}')
        GROUP BY region, market
        ORDER BY region, market
        """
        
        result = conn.execute(query).fetchdf()
        
        print(f"\nAggregation results:")
        print(result)
        
    except Exception as e:
        print(f"Error: {e}")
    finally:
        conn.close()


if __name__ == "__main__":
    print("DuckDB Iceberg Query Examples")
    print("=" * 70)
    
    example_duckdb_query()
    example_duckdb_aggregations()
    
    print("\n" + "=" * 70)
    print("Examples complete!")
    print("\nNote: DuckDB Iceberg extension support may vary.")
    print("For production use, consider using PyIceberg for reliability.")

