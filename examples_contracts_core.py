#!/usr/bin/env python3
"""
Example: Using contracts_core for dataset governance

This script demonstrates how to use contracts_core to run datasets
under governance with contract validation, path generation, and manifests.
"""
import sys
from pathlib import Path

# Add src to path for local development
sys.path.insert(0, str(Path(__file__).parent / "src"))

from contracts_core import run_dataset, list_available_contracts, load_contract


def example_1_list_contracts():
    """Example 1: List all available dataset contracts."""
    print("\n" + "="*60)
    print("Example 1: List Available Contracts")
    print("="*60)
    
    contracts = list_available_contracts()
    print(f"\nAvailable datasets: {len(contracts)}")
    for contract_id in contracts:
        print(f"  - {contract_id}")


def example_2_inspect_contract():
    """Example 2: Load and inspect a contract."""
    print("\n" + "="*60)
    print("Example 2: Inspect a Contract")
    print("="*60)
    
    contract = load_contract("node_master")
    
    print(f"\nDataset: {contract.dataset_id}")
    print(f"Version: {contract.version}")
    print(f"Source Type: {contract.source.type}")
    
    print(f"\nParameters:")
    for param in contract.params:
        required = "REQUIRED" if param.required else "optional"
        print(f"  - {param.name} ({param.type}, {required})")
        if param.allowed_values:
            print(f"    Allowed: {param.allowed_values}")
    
    print(f"\nPartitioning:")
    print(f"  Keys: {contract.partitioning.keys}")
    
    print(f"\nStorage:")
    print(f"  Bronze: {contract.storage.bronze}")
    print(f"  Silver: {contract.storage.silver}")
    print(f"  Gold: {contract.storage.gold}")


def example_3_run_dataset():
    """Example 3: Run a dataset with legacy script."""
    print("\n" + "="*60)
    print("Example 3: Run Dataset with Legacy Script")
    print("="*60)
    
    # Run node_master dataset
    result = run_dataset(
        dataset_id="node_master",
        params={
            "region": "BCA",
            "active_only": True
        },
        base_path="/tmp/example_data",
        manifest_path="/tmp/example_manifests"
    )
    
    print(f"\nRun completed!")
    print(f"  Run ID: {result['run_id']}")
    print(f"  Status: {result['status']}")
    print(f"\nGenerated Paths:")
    for zone, path in result['output_paths'].items():
        print(f"  {zone}: {path}")
    print(f"\nManifest: {result['manifest_location']}")
    
    if result['status'] == 'success':
        print("\n✅ Dataset run successful!")
    else:
        print(f"\n❌ Dataset run failed: {result.get('error')}")


def example_4_run_api_dataset():
    """Example 4: Run a dataset with API source (simulation)."""
    print("\n" + "="*60)
    print("Example 4: Run Dataset with API Source")
    print("="*60)
    
    # Run cenace_pml dataset (API type)
    result = run_dataset(
        dataset_id="cenace_pml",
        params={
            "market": "MDA",
            "region": "BCA",
            "start_date": "2024-01-01",
            "end_date": "2024-01-31",
            "node": "NODE_123",
            "year": 2024
        },
        base_path="/tmp/example_data",
        manifest_path="/tmp/example_manifests"
    )
    
    print(f"\nRun completed!")
    print(f"  Run ID: {result['run_id']}")
    print(f"  Status: {result['status']}")
    print(f"\nGenerated Paths:")
    for zone, path in result['output_paths'].items():
        print(f"  {zone}: {path}")
    print(f"\nManifest: {result['manifest_location']}")
    
    print("\nNote: API source types don't execute automatically.")
    print("Implement API calls in your consuming application.")


def example_5_parameter_validation():
    """Example 5: Demonstrate parameter validation."""
    print("\n" + "="*60)
    print("Example 5: Parameter Validation")
    print("="*60)
    
    print("\nAttempting to run with invalid parameters...")
    
    try:
        result = run_dataset(
            dataset_id="cenace_pml",
            params={
                "market": "INVALID_MARKET",  # Not in allowed_values
                "region": "BCA"
                # Missing required: start_date, end_date
            }
        )
        print("ERROR: Should have failed validation!")
    except Exception as e:
        print(f"\nValidation correctly rejected invalid parameters:")
        print(f"  {e}")


def main():
    """Run all examples."""
    print("\n" + "="*60)
    print("CONTRACTS CORE EXAMPLES")
    print("="*60)
    
    example_1_list_contracts()
    example_2_inspect_contract()
    example_3_run_dataset()
    example_4_run_api_dataset()
    example_5_parameter_validation()
    
    print("\n" + "="*60)
    print("Examples completed!")
    print("="*60)
    print("\nCheck the following directories:")
    print("  - /tmp/example_data/       (dataset outputs)")
    print("  - /tmp/example_manifests/  (run manifests)")
    print()


if __name__ == "__main__":
    main()
