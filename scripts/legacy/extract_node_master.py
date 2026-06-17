#!/usr/bin/env python3
"""
Example legacy script for extracting node master data.

This script demonstrates how legacy scripts can be wrapped by the
contracts_core governance framework. Legacy scripts receive parameters
via command-line arguments and write to paths specified by the framework.
"""
import argparse
import json
from pathlib import Path
from datetime import datetime
import sys


def extract_node_master(region, active_only, output_path, run_id):
    """
    Extract node master data (simulated).
    
    In a real scenario, this would:
    - Connect to a database or API
    - Extract node master data
    - Filter by region and active status
    - Write to the specified output path
    """
    print(f"[Legacy Script] Extracting node master data")
    print(f"[Legacy Script] Region: {region}")
    print(f"[Legacy Script] Active only: {active_only}")
    print(f"[Legacy Script] Output path: {output_path}")
    print(f"[Legacy Script] Run ID: {run_id}")
    
    # Simulate data extraction
    nodes = [
        {
            "node_id": "NODE_001",
            "node_name": "Substation A",
            "region": region or "BCA",
            "zone": "ZONE_1",
            "voltage_level": 230.0,
            "node_type": "transmission",
            "is_active": True,
            "created_at": "2024-01-01T00:00:00Z",
            "updated_at": datetime.utcnow().isoformat() + "Z"
        },
        {
            "node_id": "NODE_002",
            "node_name": "Substation B",
            "region": region or "BCA",
            "zone": "ZONE_2",
            "voltage_level": 115.0,
            "node_type": "distribution",
            "is_active": True,
            "created_at": "2024-01-15T00:00:00Z",
            "updated_at": datetime.utcnow().isoformat() + "Z"
        },
        {
            "node_id": "NODE_003",
            "node_name": "Substation C (Inactive)",
            "region": region or "BCA",
            "zone": "ZONE_1",
            "voltage_level": 230.0,
            "node_type": "transmission",
            "is_active": False,
            "created_at": "2023-01-01T00:00:00Z",
            "updated_at": "2023-12-31T00:00:00Z"
        }
    ]
    
    # Filter by active status if requested
    if active_only:
        nodes = [n for n in nodes if n["is_active"]]
    
    # Create output directory
    output_dir = Path(output_path)
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Write data as JSON (in real scenario, would be Parquet)
    output_file = output_dir / f"nodes_{run_id}.json"
    with open(output_file, 'w') as f:
        json.dump(nodes, f, indent=2)
    
    print(f"[Legacy Script] Extracted {len(nodes)} nodes")
    print(f"[Legacy Script] Output written to: {output_file}")
    print(f"[Legacy Script] Extraction complete")
    
    return 0


def main():
    parser = argparse.ArgumentParser(
        description="Legacy script: Extract node master data"
    )
    parser.add_argument("--region", type=str, help="Region filter")
    parser.add_argument("--active_only", type=str, help="Filter for active nodes only")
    parser.add_argument("--output", type=str, required=True, help="Output path")
    parser.add_argument("--run-id", type=str, required=True, help="Run ID")
    
    args = parser.parse_args()
    
    # Convert active_only to boolean
    active_only = args.active_only and args.active_only.lower() in ("true", "yes", "1")
    
    try:
        exit_code = extract_node_master(
            args.region,
            active_only,
            args.output,
            args.run_id
        )
        return exit_code
    except Exception as e:
        print(f"[Legacy Script] ERROR: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
