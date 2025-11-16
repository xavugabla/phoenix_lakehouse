"""
Example script demonstrating how to query the Iceberg Lakehouse using DuckDB.

This script serves as a blueprint for a potential backend API that would
power a web application. It shows how to:
1. Connect to an in-memory DuckDB instance.
2. Load the necessary extensions (iceberg).
3. Configure the Iceberg catalog to connect to your BigQuery catalog.
4. Run an analytical SQL query directly on the GCS data.
5. Fetch the results as a Pandas DataFrame.
"""
import os
import duckdb
import pandas as pd

from pipeline_tasks.config import load_config

def query_lakehouse_with_duckdb():
    """
    Connects to the Lakehouse and runs a sample analytical query.
    """
    print("🚀 Querying the Lakehouse with DuckDB...")
    print("=" * 70)

    try:
        # --- 1. Load Configuration ---
        # This is needed to get the BigQuery project and dataset for the catalog
        config = load_config()
        if not config.lakehouse:
            raise ValueError("Lakehouse configuration not found in settings.")
        
        lh_config = config.lakehouse
        bq_project = lh_config.catalog.project
        bq_dataset = lh_config.catalog.dataset
        
        # --- 2. Initialize DuckDB and Load Iceberg Extension ---
        # Using an in-memory database is perfect for a stateless backend API
        con = duckdb.connect(database=':memory:')
        
        print("Installing and loading Iceberg extension...")
        con.execute("INSTALL iceberg;")
        con.execute("LOAD iceberg;")
        
        # --- 3. Configure the Iceberg Catalog ---
        # This tells DuckDB how to find and read your Iceberg tables
        print(f"Configuring BigQuery catalog for project '{bq_project}'...")
        con.execute(f"""
            CALL iceberg_scan_set_project_id('{bq_project}');
            CREATE SECRET (
                TYPE GCS,
                PROVIDER CREDENTIAL_CHAIN
            );
        """)

        # --- 4. Run an Analytical SQL Query ---
        # This is a sample query. You can run any standard SQL here.
        # We are querying the 'pend' table for a specific zone and time range.
        table_identifier = f"iceberg_scan('{bq_dataset}.pend')"
        
        sql_query = f"""
            SELECT
                CAST(timestamp AS DATE) AS day,
                zone,
                AVG(pz) AS average_price,
                MAX(pz) AS max_price,
                MIN(pz) AS min_price
            FROM {table_identifier}
            WHERE
                zone = 'ACAPULCO'
                AND timestamp >= '2025-10-15 00:00:00'
                AND timestamp <= '2025-11-15 23:59:59'
            GROUP BY
                day, zone
            ORDER BY
                day;
        """
        
        print("\nExecuting analytical query:")
        print(sql_query)
        
        # --- 5. Fetch Results as a Pandas DataFrame ---
        results_df = con.execute(sql_query).fetchdf()
        
        print("\n" + "=" * 70)
        print("✅ Query successful! Results:")
        print(results_df)

        return results_df

    except Exception as e:
        print(f"\n❌ An error occurred during the query: {e}")
        raise
    finally:
        if 'con' in locals():
            con.close()

if __name__ == "__main__":
    # To run this, you need to have DuckDB installed (`pip install duckdb`)
    # and be authenticated with Google Cloud (`gcloud auth application-default login`)
    try:
        query_lakehouse_with_duckdb()
    except ImportError:
        print("\n[ERROR] DuckDB is not installed.")
        print("Please run: pip install duckdb")
