import sys
from pathlib import Path

# Add the 'src' directory to the Python path
# This allows the script to find and import modules from 'pipeline_tasks'
src_path = Path(__file__).parent / "src"
if str(src_path) not in sys.path:
    sys.path.insert(0, str(src_path))

"""
Local execution script for the CENACE data pipeline.

This script allows you to run a flow directly to generate data on your local machine.
This is useful for testing, debugging, or performing a small-scale data backfill.

With the master catalogue system, you can now run backfills without specifying dates!
The flow will automatically detect gaps and only fetch missing data.
"""
from datetime import datetime, timedelta
from orchestration.flows.backfill import backfill_flow

if __name__ == "__main__":
    print("🚀 Starting a local run of the backfill flow...")
    print("=" * 70)
    
    # --- Option 1: Automatic gap detection (recommended) ---
    # The flow will automatically detect what data is missing and only fetch that.
    # We'll set the date range to the last 30 days.
    print("\n📋 Mode: Automatic gap detection (using master catalogue)")
    print("   The flow will scan for missing data in the last 30 days and backfill only the gaps.")
    
    end_date = datetime.utcnow() - timedelta(days=1)
    start_date = end_date - timedelta(days=30)
    
    params = {
        "dataset": "pend",
        "region": "SIN",
        "market": "MDA",
        "start_date": start_date,
        "end_date": end_date,
        "use_catalogue": True,  # Enable automatic gap detection
        "zones_limit": None,  # Process all zones within the date range
    }
    
    # --- Option 2: Manual date specification (if you want to override) ---
    # Uncomment these lines if you want to specify exact dates:
    # params["start_date"] = datetime(2025, 11, 10)
    # params["end_date"] = datetime(2025, 11, 11)
    # params["use_catalogue"] = False  # Disable catalogue to use manual dates
    
    print(f"\n🔧 Parameters:")
    print(f"   - Dataset: {params['dataset']}")
    print(f"   - Region: {params['region']}")
    print(f"   - Market: {params['market']}")
    print(f"   - Date Range: {start_date.date()} to {end_date.date()}")
    
    print("\n💡 Tip: Run 'python populate_catalogue.py' first to download the master catalog!")
    print("   The master catalog is stored in GCS (read-only) and will be downloaded automatically.")
    print("=" * 70)
    
    # --- Execute the flow ---
    # Since flows are just Python functions, we can call them directly.
    result = backfill_flow(**params)
    
    print("\n✅ Flow run complete.")
    print("📊 Results:")
    print(result)
    print("\n📦 Data has been generated in the 'data/' directory.")
    if result.get('gaps_found', 0) > 0:
        print(f"🔍 Found {result['gaps_found']} gaps that were backfilled.")
    else:
        print("✨ No gaps found - all data already exists!")
