"""
Script to download the master catalog for gap detection (READ ONLY).

This script downloads the existing master catalog from GCS (novogrid-workqueue/catalogs/master_catalog.json)
for local use in determining what date ranges need to be extracted.

NOTE: 
- The master catalog in GCS is READ ONLY - we don't modify it
- We READ it to determine gaps/date ranges for extraction
- The extraction flows then UPLOAD DATA to GCS (that's the core functionality)
- The catalog is only used to know what dates to extract, not to track uploads
"""
from pipeline_tasks.catalog.master_catalogue import load_master_catalogue
from pathlib import Path

if __name__ == "__main__":
    print("📥 Downloading master catalog from GCS (READ ONLY)...")
    print("=" * 70)
    print("📦 GCS Location: novogrid-workqueue/catalogs/master_catalog.json")
    print("⚠️  READ ONLY - GCS file will NOT be modified")
    print("=" * 70)
    
    catalogue_path_local = Path("catalogues/cenace_catalogues/master_catalog.json")
    
    # Download existing catalog from GCS (read-only)
    print("\n⬇️  Downloading master catalog from GCS...")
    try:
        catalogue = load_master_catalogue(
            catalogue_path=catalogue_path_local
        )
        print(f"   ✅ Downloaded successfully")
        print(f"   📊 Total entries: {len(catalogue.coverage)}")
        print(f"   📁 Local copy saved to: {catalogue_path_local}")
        print(f"\n💡 The master catalog is now available locally for gap detection.")
        print("   Run backfill flows with use_catalogue=True to automatically detect gaps!")
    except FileNotFoundError as e:
        print(f"   ❌ Error: {e}")
        print("   The master catalog must exist in GCS before running this script.")
        exit(1)

