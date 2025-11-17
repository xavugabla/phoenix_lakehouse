"""
Manifest tracking for file uploads and sync operations.
"""
import json
import hashlib
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field


class FileManifest(BaseModel):
    """Manifest entry for a single file."""
    path: str
    size: int
    checksum: str  # MD5 hash
    mtime: float  # Modification time
    uploaded_at: Optional[datetime] = None
    gcs_path: Optional[str] = None
    gcs_checksum: Optional[str] = None


class SyncManifest(BaseModel):
    """Manifest for a sync operation."""
    dataset: str
    sync_id: str  # Unique identifier for this sync
    started_at: datetime
    completed_at: Optional[datetime] = None
    files: List[FileManifest] = Field(default_factory=list)
    stats: Dict[str, int] = Field(default_factory=dict)  # uploaded, skipped, failed, etc.


def save_manifest(manifest: SyncManifest, path: str | Path) -> Path:
    """
    Save a sync manifest to disk.
    
    Args:
        manifest: Manifest to save
        path: Path to save manifest
    
    Returns:
        Path to saved manifest
    """
    path_obj = Path(path)
    path_obj.parent.mkdir(parents=True, exist_ok=True)
    
    with open(path_obj, 'w', encoding='utf-8') as f:
        # Convert to dict and handle datetime serialization
        manifest_dict = manifest.model_dump(mode='json')
        json.dump(manifest_dict, f, indent=2, default=str)
    
    return path_obj


def load_manifest(path: str | Path) -> SyncManifest:
    """
    Load a sync manifest from disk.
    
    Args:
        path: Path to manifest file
    
    Returns:
        SyncManifest instance
    """
    path_obj = Path(path)
    
    if not path_obj.exists():
        raise FileNotFoundError(f"Manifest not found: {path}")
    
    with open(path_obj, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    return SyncManifest(**data)


def create_manifest_id(dataset: str, partition: Dict[str, Any]) -> str:
    """
    Create a unique manifest ID from dataset and partition.
    
    Args:
        dataset: Dataset name
        partition: Partition dictionary
    
    Returns:
        Manifest ID string
    """
    # Create deterministic ID from partition keys
    partition_str = '-'.join(f"{k}={v}" for k, v in sorted(partition.items()))
    manifest_str = f"{dataset}/{partition_str}"
    
    # Hash to create shorter ID
    manifest_id = hashlib.md5(manifest_str.encode()).hexdigest()[:16]
    
    return f"{dataset}_{manifest_id}"

