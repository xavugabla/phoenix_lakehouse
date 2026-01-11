"""
Run manifest generation for dataset executions.

This module creates and writes manifests that track dataset runs,
including parameters, paths, and timestamps.
"""
import json
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional
from .loader import DatasetContract


class ManifestError(Exception):
    """Manifest generation or writing error."""
    pass


class RunManifest:
    """
    Manifest for a dataset run.
    
    Tracks all metadata about a dataset execution including parameters,
    paths, timestamps, and status.
    """
    
    def __init__(
        self,
        run_id: str,
        dataset_id: str,
        contract_version: str,
        params: Dict[str, Any],
        paths: Dict[str, str],
        start_time: Optional[datetime] = None
    ):
        """
        Initialize a run manifest.
        
        Args:
            run_id: Unique identifier for this run
            dataset_id: Dataset identifier
            contract_version: Version of contract used
            params: Runtime parameters used
            paths: Storage paths for this run
            start_time: Run start time (defaults to now)
        """
        self.run_id = run_id
        self.dataset_id = dataset_id
        self.contract_version = contract_version
        self.params = params
        self.paths = paths
        self.start_time = start_time or datetime.utcnow()
        self.end_time: Optional[datetime] = None
        self.status = "running"
        self.error: Optional[str] = None
        self.metadata: Dict[str, Any] = {}
    
    def mark_success(self, metadata: Optional[Dict[str, Any]] = None):
        """Mark the run as successful."""
        self.end_time = datetime.utcnow()
        self.status = "success"
        if metadata:
            self.metadata.update(metadata)
    
    def mark_failure(self, error: str, metadata: Optional[Dict[str, Any]] = None):
        """Mark the run as failed."""
        self.end_time = datetime.utcnow()
        self.status = "failed"
        self.error = error
        if metadata:
            self.metadata.update(metadata)
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Convert manifest to dictionary.
        
        Returns:
            Dictionary representation of manifest
        """
        return {
            "run_id": self.run_id,
            "dataset_id": self.dataset_id,
            "contract_version": self.contract_version,
            "params": self.params,
            "paths": self.paths,
            "start_time": self.start_time.isoformat() if self.start_time else None,
            "end_time": self.end_time.isoformat() if self.end_time else None,
            "status": self.status,
            "error": self.error,
            "metadata": self.metadata,
        }
    
    def to_json(self, indent: int = 2) -> str:
        """
        Convert manifest to JSON string.
        
        Args:
            indent: JSON indentation level
        
        Returns:
            JSON string representation
        """
        return json.dumps(self.to_dict(), indent=indent)


def create_manifest(
    run_id: str,
    contract: DatasetContract,
    params: Dict[str, Any],
    paths: Dict[str, str]
) -> RunManifest:
    """
    Create a new run manifest from a contract and parameters.
    
    Args:
        run_id: Unique identifier for this run
        contract: Dataset contract
        params: Validated runtime parameters
        paths: Generated storage paths
    
    Returns:
        RunManifest instance
    """
    return RunManifest(
        run_id=run_id,
        dataset_id=contract.dataset_id,
        contract_version=contract.version,
        params=params,
        paths=paths
    )


def write_manifest(
    manifest: RunManifest,
    output_path: str,
    create_dirs: bool = True
) -> str:
    """
    Write manifest to a JSON file.
    
    Args:
        manifest: Run manifest to write
        output_path: Path where manifest should be written
        create_dirs: If True, create parent directories if they don't exist
    
    Returns:
        Full path to written manifest file
    
    Raises:
        ManifestError: If writing fails
    """
    path = Path(output_path)
    
    # Create parent directories if needed
    if create_dirs and not path.parent.exists():
        try:
            path.parent.mkdir(parents=True, exist_ok=True)
        except Exception as e:
            raise ManifestError(f"Failed to create manifest directory: {e}")
    
    # Write manifest
    try:
        with open(path, 'w', encoding='utf-8') as f:
            f.write(manifest.to_json())
    except Exception as e:
        raise ManifestError(f"Failed to write manifest to {path}: {e}")
    
    return str(path.absolute())


def get_manifest_path(
    base_path: str,
    dataset_id: str,
    run_id: str
) -> str:
    """
    Generate a standardized manifest file path.
    
    Args:
        base_path: Base directory for manifests
        dataset_id: Dataset identifier
        run_id: Run identifier
    
    Returns:
        Full path to manifest file
    """
    return str(Path(base_path) / dataset_id / f"{run_id}_manifest.json")


def load_manifest(manifest_path: str) -> RunManifest:
    """
    Load a manifest from a JSON file.
    
    Args:
        manifest_path: Path to manifest file
    
    Returns:
        RunManifest instance
    
    Raises:
        ManifestError: If loading fails
    """
    path = Path(manifest_path)
    
    if not path.exists():
        raise ManifestError(f"Manifest file not found: {manifest_path}")
    
    try:
        with open(path, 'r', encoding='utf-8') as f:
            data = json.load(f)
    except json.JSONDecodeError as e:
        raise ManifestError(f"Invalid JSON in manifest file: {e}")
    except Exception as e:
        raise ManifestError(f"Failed to read manifest file: {e}")
    
    # Reconstruct manifest
    manifest = RunManifest(
        run_id=data["run_id"],
        dataset_id=data["dataset_id"],
        contract_version=data["contract_version"],
        params=data["params"],
        paths=data["paths"],
        start_time=datetime.fromisoformat(data["start_time"]) if data.get("start_time") else None
    )
    
    manifest.status = data.get("status", "unknown")
    manifest.error = data.get("error")
    manifest.metadata = data.get("metadata", {})
    
    if data.get("end_time"):
        manifest.end_time = datetime.fromisoformat(data["end_time"])
    
    return manifest
