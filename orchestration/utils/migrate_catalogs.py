"""
Utility script to perform a one-time migration of the JSON entity catalogues
into the new Iceberg Lakehouse metastore.
"""
import json
import sys
from pathlib import Path

import pandas as pd
import pyarrow as pa

# Fix Windows console encoding for emoji/unicode
if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

# Add 'src' to the Python path to find pipeline_tasks
src_path = Path(__file__).resolve().parent.parent.parent / "src"
if str(src_path) not in sys.path:
    sys.path.insert(0, str(src_path))

from pyiceberg.exceptions import TableAlreadyExistsError
from pipeline_tasks.config import load_config
from pipeline_tasks.io.catalog_sync import publish_table_metadata
from pipeline_tasks.io.iceberg import load_iceberg_catalog
from pipeline_tasks.schemas.master_schemas import MASTER_SCHEMAS

def create_table_if_not_exists(catalog, table_identifier, schema, location):
    """Helper to create an Iceberg table safely."""
    try:
        catalog.create_table(identifier=table_identifier, schema=schema, location=location)
        print(f"✅ Table '{table_identifier}' created at {location}")
    except TableAlreadyExistsError:
        print(f"✅ Table '{table_identifier}' already exists.")
        # For BigQuery catalog, we need to drop and recreate to overwrite
        try:
            catalog.drop_table(identifier=table_identifier)
            catalog.create_table(identifier=table_identifier, schema=schema, location=location)
            print(f"✅ Table '{table_identifier}' recreated.")
        except Exception as e:
            print(f"⚠️  Could not recreate table '{table_identifier}': {e}")
            print("   Will attempt to append data instead.")

def delete_old_tables(config, namespace, old_prefix="data"):
    """Delete old tables from the data/ prefix location."""
    from google.cloud import bigquery
    from google.cloud import storage
    
    print(f"\n--- Cleaning Up Old Tables (from {old_prefix}/ prefix) ---")
    
    entity_tables = [
        "cenace_node_catalog",
        "cenace_load_zones", "cenace_load_zone_nodes",
        "cenace_reserve_zones", "cenace_reserve_zone_nodes"
    ]
    
    # Delete from BigQuery
    bq_client = bigquery.Client(project=config.lakehouse.catalog.project)
    for table_name in entity_tables:
        table_id = f"{config.lakehouse.catalog.project}.{namespace}.{table_name}"
        try:
            bq_client.delete_table(table_id, not_found_ok=True)
            print(f"✅ Deleted BigQuery table: {table_id}")
        except Exception as e:
            print(f"⚠️  Could not delete BigQuery table {table_id}: {e}")
    
    # Delete from GCS (old data/ prefix location)
    gcs_client = storage.Client(project=config.lakehouse.catalog.project)
    bucket = gcs_client.bucket(config.lakehouse.gcs_bucket)
    old_prefix_path = f"{old_prefix}/"
    
    for table_name in entity_tables:
        table_prefix = f"{old_prefix_path}{table_name}/"
        blobs = list(bucket.list_blobs(prefix=table_prefix))
        if blobs:
            print(f"Deleting {len(blobs)} files from gs://{config.lakehouse.gcs_bucket}/{table_prefix}")
            for blob in blobs:
                blob.delete()
            print(f"✅ Deleted GCS data: {table_prefix}")
        else:
            print(f"✅ No old data found at: {table_prefix}")

def migrate_catalogs():
    """
    Main migration function. Reads JSON catalogs, transforms the data,
    and loads it into new Iceberg entity tables.
    """
    print("🚀 Starting migration of JSON catalogues to Iceberg...")
    print("=" * 70)

    config = load_config()
    if not config.lakehouse:
        raise ValueError("Lakehouse configuration not found in settings.")
    
    namespace = config.lakehouse.catalog.dataset
    
    # Delete old tables from data/ prefix if they exist
    delete_old_tables(config, namespace, old_prefix="data")
    
    # --- 0. Ensure BigQuery Dataset Exists ---
    from google.cloud import bigquery
    bq_client = bigquery.Client(project=config.lakehouse.catalog.project)
    dataset_id = config.lakehouse.catalog.dataset
    dataset_ref = bigquery.DatasetReference(config.lakehouse.catalog.project, dataset_id)
    
    try:
        bq_client.get_dataset(dataset_ref)
        print(f"✅ BigQuery dataset '{dataset_id}' exists.")
    except Exception:
        print(f"⚠️  BigQuery dataset '{dataset_id}' not found. Creating it...")
        dataset = bigquery.Dataset(dataset_ref)
        dataset.location = "US"  # Match the catalog location
        dataset = bq_client.create_dataset(dataset, exists_ok=True)
        print(f"✅ BigQuery dataset '{dataset_id}' created.")
    
    # --- 1. Setup Connections ---
    # IMPORTANT: BigQuery catalog doesn't support writes (commit_table not implemented)
    # We'll use an in-memory catalog for the migration, then the data will be queryable
    # via BigQuery catalog once the files are written to GCS
    from pyiceberg.catalog import load_catalog
    
    # Use in-memory catalog for writes (it supports transactions)
    write_catalog = load_catalog(
        "migration_write_catalog",
        **{
            "type": "in-memory",
            "warehouse": f"gs://{config.lakehouse.gcs_bucket}/{config.lakehouse.gcs_prefix}",
        }
    )
    
    # Also load BigQuery catalog to ensure table structures exist
    read_catalog = load_iceberg_catalog()  # BigQuery catalog for metadata registration
    try:
        read_catalog.create_namespace(namespace)
        print(f"✅ Ensured namespace '{namespace}' exists in BigQuery catalog.")
    except Exception:
        print(f"✅ Namespace '{namespace}' already exists in BigQuery catalog.")
    catalog = write_catalog  # Use in-memory catalog for writes
    namespace = config.lakehouse.catalog.dataset
    # Handle empty prefix - tables go directly in bucket root
    prefix = config.lakehouse.gcs_prefix.rstrip("/") if config.lakehouse.gcs_prefix else ""
    base_location = f"gs://{config.lakehouse.gcs_bucket}/{prefix}" if prefix else f"gs://{config.lakehouse.gcs_bucket}"
    
    # Create namespace in the write catalog
    try:
        catalog.create_namespace(namespace)
        print(f"✅ Created namespace '{namespace}' in write catalog.")
    except Exception:
        print(f"✅ Namespace '{namespace}' already exists in write catalog.")
    
    # Source data paths
    source_path = Path("catalogues/cenace_catalogues")

    # --- 2. Initialize All Entity Tables ---
    print("\n--- Initializing Entity Tables ---")
    entity_tables = [
        "cenace_node_catalog",
        "cenace_load_zones", "cenace_load_zone_nodes",
        "cenace_reserve_zones", "cenace_reserve_zone_nodes"
    ]
    for table_name in entity_tables:
        # Table location: bucket root if no prefix, otherwise prefix/table_name
        table_location = f"{base_location}/{table_name}"
        create_table_if_not_exists(
            catalog=catalog,
            table_identifier=f"{namespace}.{table_name}",
            schema=MASTER_SCHEMAS[table_name],
            location=table_location
        )

    # --- 3. Migrate Node Catalog ---
    print("\n--- Migrating `cenace_node_catalog.json` ---")
    node_catalog_path = source_path / "cenace_node_catalog.json"
    with open(node_catalog_path, 'r', encoding='utf-8') as f:
        node_data = json.load(f)["nodes"]
    
    # Flatten the nested geospatial data for simplicity
    flat_nodes = []
    for node in node_data:
        flat_node = node.copy()
        if 'geospatial' in flat_node and flat_node['geospatial']:
            flat_node.update(flat_node['geospatial'])
        del flat_node['geospatial']
        # Remove complex nested fields that don't fit the schema
        flat_node.pop('pml_data_status', None)
        flat_node.pop('sources', None)
        flat_nodes.append(flat_node)
    
    # Create DataFrame and select only columns that match the schema
    node_df = pd.DataFrame(flat_nodes)
    schema_columns = [
        "node_id", "name", "system", "voltage_kv", "load_zone", "transmission_zone",
        "state", "municipality", "latitude", "longitude", "altitude_m",
        "cvegeo", "locality", "population"
    ]
    # Select only columns that exist in both the DataFrame and schema
    available_columns = [col for col in schema_columns if col in node_df.columns]
    node_df_filtered = node_df[available_columns].copy()
    
    # Ensure node_id is not null (required field)
    node_df_filtered = node_df_filtered[node_df_filtered['node_id'].notna()].copy()
    
    # Convert data types to match schema
    # Float columns should be float32 (not float64/double)
    float_columns = ["voltage_kv", "latitude", "longitude", "altitude_m"]
    for col in float_columns:
        if col in node_df_filtered.columns:
            node_df_filtered[col] = pd.to_numeric(node_df_filtered[col], errors='coerce').astype('float32')
    
    # Convert cvegeo to string (it might be numeric in the data)
    if "cvegeo" in node_df_filtered.columns:
        node_df_filtered["cvegeo"] = node_df_filtered["cvegeo"].astype(str).replace('nan', None)
    
    # Convert population to int32 (not int64/long)
    if "population" in node_df_filtered.columns:
        node_df_filtered["population"] = pd.to_numeric(node_df_filtered["population"], errors='coerce').astype('Int32')  # Nullable int32
    
    # Use the write catalog (in-memory) which supports transactions
    node_table = catalog.load_table(f"{namespace}.cenace_node_catalog")
    
    # Convert pandas DataFrame to PyArrow table with explicit schema to ensure types match
    node_table_pa = pa.Table.from_pandas(node_df_filtered)
    
    # Fix nullable issues: ensure node_id is non-nullable (required field)
    schema = node_table_pa.schema
    node_id_field = schema.field('node_id')
    if node_id_field.nullable:
        # Create a new schema with node_id as non-nullable
        fields = []
        for field in schema:
            if field.name == 'node_id':
                fields.append(pa.field('node_id', field.type, nullable=False))
            else:
                fields.append(field)
        schema = pa.schema(fields)
        node_table_pa = node_table_pa.cast(schema)
    
    # Use overwrite with the in-memory catalog (which supports transactions)
    node_table.overwrite(node_table_pa)
    print(f"✅ Migrated {len(node_df_filtered)} nodes into `cenace_node_catalog` table.")
    
    # Update file-based catalog with metadata location
    publish_table_metadata("cenace_node_catalog", table_location)
    print("✅ Updated catalog metadata for `cenace_node_catalog`.")
    
    # --- 4. Migrate Zone Files (Load and Reserve) ---
    for zone_type in ["load", "reserve"]:
        print(f"\n--- Migrating `cenace_{zone_type}_zones.json` ---")
        zone_file = source_path / f"cenace_{zone_type}_zones.json"
        with open(zone_file, 'r', encoding='utf-8') as f:
            zone_data = json.load(f)
            
        # Migrate the list of zones
        zones_df = pd.DataFrame(zone_data["zones"], columns=["zone_name"])
        # Ensure zone_name is not null (required field)
        zones_df = zones_df[zones_df['zone_name'].notna()].copy()
        zones_table = catalog.load_table(f"{namespace}.cenace_{zone_type}_zones")
        zones_table_pa = pa.Table.from_pandas(zones_df)
        
        # Fix nullable: ensure zone_name is non-nullable (required field)
        schema = zones_table_pa.schema
        zone_name_field = schema.field('zone_name')
        if zone_name_field.nullable:
            fields = [pa.field('zone_name', zone_name_field.type, nullable=False)]
            schema = pa.schema(fields)
            zones_table_pa = zones_table_pa.cast(schema)
        
        zones_table.overwrite(zones_table_pa)
        print(f"✅ Migrated {len(zones_df)} zones into `cenace_{zone_type}_zones` table.")
        
        # Update file-based catalog
        zone_table_location = f"{base_location}/cenace_{zone_type}_zones"
        publish_table_metadata(f"cenace_{zone_type}_zones", zone_table_location)

        # Migrate the zone-to-node mapping (bridge table)
        mapping_data = []
        for zone_name, node_ids in zone_data["zone_to_nodes_mapping"].items():
            for node_id in node_ids:
                mapping_data.append({"zone_name": zone_name, "node_id": node_id})
        
        mapping_df = pd.DataFrame(mapping_data)
        # Ensure required fields are not null
        mapping_df = mapping_df[mapping_df['zone_name'].notna() & mapping_df['node_id'].notna()].copy()
        bridge_table = catalog.load_table(f"{namespace}.cenace_{zone_type}_zone_nodes")
        mapping_table_pa = pa.Table.from_pandas(mapping_df)
        
        # Fix nullable: ensure zone_name and node_id are non-nullable (required fields)
        schema = mapping_table_pa.schema
        fields = []
        for field in schema:
            if field.name in ['zone_name', 'node_id']:
                fields.append(pa.field(field.name, field.type, nullable=False))
            else:
                fields.append(field)
        schema = pa.schema(fields)
        mapping_table_pa = mapping_table_pa.cast(schema)
        
        bridge_table.overwrite(mapping_table_pa)
        print(f"✅ Migrated {len(mapping_df)} zone-to-node mappings into `cenace_{zone_type}_zone_nodes` table.")
        
        # Update file-based catalog
        bridge_table_location = f"{base_location}/cenace_{zone_type}_zone_nodes"
        publish_table_metadata(f"cenace_{zone_type}_zone_nodes", bridge_table_location)

    print("\n--- Registering Core Data Tables (pend/pml/psc) ---")
    for table_name in ["pend", "psc", "pml"]:
        table_location = f"{base_location}/{table_name}"
        published = publish_table_metadata(table_name, table_location)
        if not published:
            print(f"⚠️  No metadata found for '{table_name}' at {table_location}. Skipping.")

    print("\n" + "=" * 70)
    print("🎉 Catalogue migration complete!")

if __name__ == "__main__":
    migrate_catalogs()
