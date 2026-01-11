#!/usr/bin/env python3
"""
Simple test script for contracts_core functionality.

This demonstrates the complete flow of running a dataset under governance.
"""
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from contracts_core import run_dataset, list_available_contracts


def test_list_contracts():
    """Test listing available contracts."""
    print("\n" + "="*60)
    print("TEST: List Available Contracts")
    print("="*60)
    
    contracts = list_available_contracts()
    print(f"Available contracts: {contracts}")
    assert len(contracts) >= 2, "Should have at least 2 contracts"
    print("✅ PASSED: Listed contracts successfully\n")


def test_node_master_dataset():
    """Test running node_master dataset with legacy script."""
    print("\n" + "="*60)
    print("TEST: Run node_master Dataset (Legacy Script)")
    print("="*60)
    
    # Run the dataset
    result = run_dataset(
        dataset_id="node_master",
        params={
            "region": "BCA",
            "active_only": True
        },
        base_path="/tmp/test_data",
        manifest_path="/tmp/test_manifests"
    )
    
    print("\nResult:")
    print(f"  Run ID: {result['run_id']}")
    print(f"  Status: {result['status']}")
    print(f"  Output Paths:")
    for zone, path in result['output_paths'].items():
        print(f"    {zone}: {path}")
    print(f"  Manifest: {result['manifest_location']}")
    
    # Verify results
    assert result['run_id'] is not None, "Run ID should be set"
    assert result['status'] == 'success', f"Run should succeed, got: {result.get('error')}"
    assert result['manifest_location'] is not None, "Manifest location should be set"
    
    # Check if manifest file exists
    manifest_file = Path(result['manifest_location'])
    assert manifest_file.exists(), "Manifest file should exist"
    
    print("\n✅ PASSED: node_master dataset executed successfully\n")


def test_cenace_pml_dataset():
    """Test running cenace_pml dataset (API type, no actual execution)."""
    print("\n" + "="*60)
    print("TEST: Run cenace_pml Dataset (API type)")
    print("="*60)
    
    # Run the dataset
    result = run_dataset(
        dataset_id="cenace_pml",
        params={
            "market": "MDA",
            "region": "BCA",
            "start_date": "2024-01-01",
            "end_date": "2024-01-31",
            "node": "NODE_123",  # Required for partitioning
            "year": 2024  # Required for partitioning
        },
        base_path="/tmp/test_data",
        manifest_path="/tmp/test_manifests"
    )
    
    print("\nResult:")
    print(f"  Run ID: {result['run_id']}")
    print(f"  Status: {result['status']}")
    print(f"  Output Paths:")
    for zone, path in result['output_paths'].items():
        print(f"    {zone}: {path}")
    print(f"  Manifest: {result['manifest_location']}")
    
    # Verify results
    assert result['run_id'] is not None, "Run ID should be set"
    assert result['status'] == 'success', f"Run should succeed, got: {result.get('error')}"
    assert result['manifest_location'] is not None, "Manifest location should be set"
    
    print("\n✅ PASSED: cenace_pml dataset validated successfully\n")


def test_invalid_params():
    """Test parameter validation with invalid params."""
    print("\n" + "="*60)
    print("TEST: Parameter Validation (Invalid Params)")
    print("="*60)
    
    try:
        result = run_dataset(
            dataset_id="cenace_pml",
            params={
                "market": "INVALID",  # Not in allowed_values
                "region": "BCA",
                "start_date": "2024-01-01",
                "end_date": "2024-01-31"
            }
        )
        print("❌ FAILED: Should have raised an error for invalid params")
        sys.exit(1)
    except Exception as e:
        print(f"Expected error caught: {e}")
        print("✅ PASSED: Invalid params correctly rejected\n")


def main():
    """Run all tests."""
    print("\n" + "="*60)
    print("CONTRACTS CORE TEST SUITE")
    print("="*60)
    
    try:
        test_list_contracts()
        test_node_master_dataset()
        test_cenace_pml_dataset()
        test_invalid_params()
        
        print("\n" + "="*60)
        print("ALL TESTS PASSED ✅")
        print("="*60 + "\n")
        return 0
        
    except AssertionError as e:
        print(f"\n❌ TEST FAILED: {e}\n")
        return 1
    except Exception as e:
        print(f"\n❌ UNEXPECTED ERROR: {e}\n")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
