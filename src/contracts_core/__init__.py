"""
Contracts Core - Contract-governed control layer for datasets.

This package provides a Python-first approach to dataset governance with:
- Dataset contracts in YAML
- Runtime parameter validation
- Contract-defined storage paths
- Legacy script wrapper execution
- Run manifests for tracking

Public Interface:
    run_dataset(dataset_id, params) -> (run_id, output_paths, manifest_location)

Usage:
    from contracts_core import run_dataset
    
    result = run_dataset(
        dataset_id="cenace_pml",
        params={
            "market": "MDA",
            "region": "BCA",
            "start_date": "2024-01-01",
            "end_date": "2024-01-31"
        }
    )
    
    print(f"Run ID: {result['run_id']}")
    print(f"Paths: {result['output_paths']}")
    print(f"Manifest: {result['manifest_location']}")
"""
import subprocess
import uuid
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional, Tuple
import os
import sys

from .loader import load_contract, list_available_contracts, ContractError
from .params import validate_params, ParamValidationError
from .paths import get_all_storage_paths, get_partitioned_path, PathError
from .manifest import create_manifest, write_manifest, get_manifest_path, ManifestError


__version__ = "1.0.0"

__all__ = [
    "run_dataset",
    "load_contract",
    "validate_params",
    "list_available_contracts",
]


class DatasetRunError(Exception):
    """Dataset run execution error."""
    pass


def _generate_run_id() -> str:
    """
    Generate a unique run identifier.
    
    Returns:
        Unique run ID string
    """
    timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    unique_id = str(uuid.uuid4())[:8]
    return f"{timestamp}_{unique_id}"


def _get_default_base_path() -> str:
    """
    Get default base path for storage.
    
    Returns:
        Default base path (from env var or fallback)
    """
    # Try environment variable first
    base_path = os.environ.get("CONTRACTS_CORE_BASE_PATH")
    if base_path:
        return base_path
    
    # Fallback to data directory
    return str(Path.cwd() / "data")


def _get_default_manifest_path() -> str:
    """
    Get default path for manifests.
    
    Returns:
        Default manifest path (from env var or fallback)
    """
    # Try environment variable first
    manifest_path = os.environ.get("CONTRACTS_CORE_MANIFEST_PATH")
    if manifest_path:
        return manifest_path
    
    # Fallback to manifests directory
    return str(Path.cwd() / "manifests")


def _execute_legacy_script(
    script_path: str,
    params: Dict[str, Any],
    output_path: str,
    run_id: str
) -> Tuple[int, str, str]:
    """
    Execute a legacy script using subprocess.
    
    Args:
        script_path: Path to the legacy script
        params: Runtime parameters to pass to script
        output_path: Where script should write output
        run_id: Unique run identifier
    
    Returns:
        Tuple of (return_code, stdout, stderr)
    
    Raises:
        DatasetRunError: If script execution fails
    """
    # Check if script exists
    script = Path(script_path)
    if not script.exists():
        raise DatasetRunError(f"Legacy script not found: {script_path}")
    
    # Build command
    if script.suffix == ".py":
        # Explicitly invoke Python interpreter for Python scripts
        cmd = [sys.executable, str(script)]
    else:
        # Fallback to executing the script directly (for non-Python executables)
        cmd = [str(script)]
    
    # Add parameters as command-line arguments
    for key, value in params.items():
        cmd.extend([f"--{key}", str(value)])
    
    # Add output path and run_id
    cmd.extend(["--output", output_path])
    cmd.extend(["--run-id", run_id])
    
    # Execute script
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=3600  # 1 hour timeout
        )
        return result.returncode, result.stdout, result.stderr
    except subprocess.TimeoutExpired as e:
        raise DatasetRunError(f"Script execution timed out after 1 hour: {e}")
    except Exception as e:
        raise DatasetRunError(f"Failed to execute legacy script: {e}")


def run_dataset(
    dataset_id: str,
    params: Dict[str, Any],
    base_path: Optional[str] = None,
    manifest_path: Optional[str] = None,
    zone: str = "bronze"
) -> Dict[str, Any]:
    """
    Run a dataset with contract-governed execution.
    
    This is the main entry point for executing datasets under governance.
    It performs the following steps:
    1. Load and validate the dataset contract
    2. Validate runtime parameters against the contract
    3. Generate storage paths from the contract
    4. Execute the dataset source (legacy script or API call)
    5. Write output to contract-defined paths
    6. Emit a run manifest
    
    Args:
        dataset_id: Unique identifier for the dataset (e.g., "cenace_pml")
        params: Runtime parameters for the dataset
        base_path: Optional base path for storage (defaults to env var or ./data)
        manifest_path: Optional path for manifests (defaults to env var or ./manifests)
        zone: Target zone for output (default: "bronze")
    
    Returns:
        Dictionary with:
            - run_id: Unique run identifier
            - output_paths: Dictionary of storage paths (bronze, silver, gold)
            - manifest_location: Path to the written manifest
            - status: Run status ("success" or "failed")
            - error: Error message if failed (optional)
    
    Raises:
        DatasetRunError: If run execution fails
        ContractError: If contract loading fails
        ParamValidationError: If parameter validation fails
    """
    run_id = _generate_run_id()
    base_path = base_path or _get_default_base_path()
    manifest_path = manifest_path or _get_default_manifest_path()
    
    print(f"[{run_id}] Starting dataset run: {dataset_id}")
    print(f"[{run_id}] Parameters: {params}")
    
    # Step 1: Load contract
    try:
        contract = load_contract(dataset_id)
        print(f"[{run_id}] Contract loaded: v{contract.version}")
    except ContractError as e:
        raise DatasetRunError(f"Failed to load contract: {e}")
    
    # Step 2: Validate parameters
    try:
        validated_params = validate_params(params, contract)
        print(f"[{run_id}] Parameters validated")
    except ParamValidationError as e:
        raise DatasetRunError(f"Parameter validation failed: {e}")
    
    # Step 3: Generate paths
    try:
        all_paths = get_all_storage_paths(contract, base_path, validated_params)
        output_path = get_partitioned_path(
            contract, zone, validated_params, base_path
        )
        print(f"[{run_id}] Output path: {output_path}")
    except PathError as e:
        raise DatasetRunError(f"Path generation failed: {e}")
    
    # Step 4: Create manifest
    try:
        manifest = create_manifest(run_id, contract, validated_params, all_paths)
    except Exception as e:
        raise DatasetRunError(f"Manifest creation failed: {e}")
    
    # Step 5: Execute dataset source
    error = None
    try:
        source_type = contract.source.type.lower()
        
        if source_type == "legacy_script":
            # Execute legacy script
            if not contract.source.script_path:
                raise DatasetRunError(
                    f"Contract source type is 'legacy_script' but script_path is not defined"
                )
            
            print(f"[{run_id}] Executing legacy script: {contract.source.script_path}")
            return_code, stdout, stderr = _execute_legacy_script(
                contract.source.script_path,
                validated_params,
                output_path,
                run_id
            )
            
            if return_code != 0:
                error = f"Legacy script failed with exit code {return_code}: {stderr}"
                print(f"[{run_id}] ERROR: {error}")
                manifest.mark_failure(error, {"stdout": stdout, "stderr": stderr})
            else:
                print(f"[{run_id}] Legacy script completed successfully")
                manifest.mark_success({"stdout": stdout})
        
        elif source_type == "cenace_api":
            # For API-based sources, this would call the API
            # For now, we'll just mark as success with a note
            print(f"[{run_id}] Note: cenace_api source type - implement API call here")
            manifest.mark_success({
                "note": "API execution should be implemented by the consuming application"
            })
        
        else:
            error = f"Unknown source type: {source_type}"
            print(f"[{run_id}] ERROR: {error}")
            manifest.mark_failure(error)
    
    except Exception as e:
        error = str(e)
        print(f"[{run_id}] ERROR: {error}")
        manifest.mark_failure(error)
    
    # Step 6: Write manifest
    try:
        manifest_file = get_manifest_path(manifest_path, dataset_id, run_id)
        manifest_location = write_manifest(manifest, manifest_file)
        print(f"[{run_id}] Manifest written: {manifest_location}")
    except ManifestError as e:
        print(f"[{run_id}] WARNING: Failed to write manifest: {e}")
        manifest_location = None
    
    # Return results
    result = {
        "run_id": run_id,
        "output_paths": all_paths,
        "manifest_location": manifest_location,
        "status": manifest.status,
    }
    
    if error:
        result["error"] = error
    
    return result
