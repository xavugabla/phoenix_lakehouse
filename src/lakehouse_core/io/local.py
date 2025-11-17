"""
Local filesystem utilities for pipeline tasks.
"""
import hashlib
import json
from pathlib import Path
from typing import Optional, Dict, Any
import pandas as pd
import pyarrow.parquet as pq


def ensure_directory(path: str | Path) -> Path:
    """
    Ensure a directory exists, creating it if necessary.
    
    Args:
        path: Directory path
    
    Returns:
        Path object
    """
    path_obj = Path(path)
    path_obj.mkdir(parents=True, exist_ok=True)
    return path_obj


def write_parquet(
    df: pd.DataFrame,
    path: str | Path,
    compression: str = "snappy",
    schema: Optional[Any] = None,
    partition_cols: Optional[list[str]] = None,
    **kwargs
) -> Path:
    """
    Write DataFrame to parquet file.
    
    Args:
        df: DataFrame to write
        path: Output path
        compression: Compression algorithm
        schema: PyArrow schema (optional)
        partition_cols: Columns to partition by (optional)
        **kwargs: Additional arguments to to_parquet
    
    Returns:
        Path to written file
    """
    path_obj = Path(path)
    ensure_directory(path_obj.parent)
    
    write_kwargs = {
        'engine': 'pyarrow',
        'compression': compression,
        'index': False,
        **kwargs
    }
    
    if schema:
        write_kwargs['schema'] = schema
    
    if partition_cols:
        # Partitioned write
        path_obj.parent.mkdir(parents=True, exist_ok=True)
        df.to_parquet(
            str(path_obj.parent),
            partition_cols=partition_cols,
            **write_kwargs
        )
        return path_obj.parent
    else:
        # Single file write
        df.to_parquet(str(path_obj), **write_kwargs)
        return path_obj


def read_parquet(path: str | Path, **kwargs) -> pd.DataFrame:
    """
    Read parquet file(s) into DataFrame.
    
    Args:
        path: Path to parquet file or directory
        **kwargs: Additional arguments to read_parquet
    
    Returns:
        DataFrame
    """
    path_obj = Path(path)
    
    if path_obj.is_dir():
        # Read partitioned dataset
        return pd.read_parquet(str(path_obj), **kwargs)
    else:
        # Read single file
        return pd.read_parquet(str(path_obj), **kwargs)


def calculate_checksum(path: str | Path, algorithm: str = "md5") -> str:
    """
    Calculate checksum of a file.
    
    Args:
        path: File path
        algorithm: Hash algorithm (md5, sha256, etc.)
    
    Returns:
        Hex digest of checksum
    """
    path_obj = Path(path)
    if not path_obj.exists():
        raise FileNotFoundError(f"File not found: {path}")
    
    hash_obj = hashlib.new(algorithm)
    
    with open(path_obj, 'rb') as f:
        for chunk in iter(lambda: f.read(4096), b''):
            hash_obj.update(chunk)
    
    return hash_obj.hexdigest()


def write_metadata(path: str | Path, metadata: Dict[str, Any]) -> Path:
    """
    Write metadata JSON file alongside a data file.
    
    Args:
        path: Path to data file
        metadata: Metadata dictionary
    
    Returns:
        Path to metadata file
    """
    path_obj = Path(path)
    meta_path = path_obj.with_suffix(path_obj.suffix + '.meta.json')
    
    with open(meta_path, 'w', encoding='utf-8') as f:
        json.dump(metadata, f, indent=2, default=str)
    
    return meta_path


def read_metadata(path: str | Path) -> Optional[Dict[str, Any]]:
    """
    Read metadata JSON file.
    
    Args:
        path: Path to data file
    
    Returns:
        Metadata dictionary or None if not found
    """
    path_obj = Path(path)
    meta_path = path_obj.with_suffix(path_obj.suffix + '.meta.json')
    
    if not meta_path.exists():
        return None
    
    with open(meta_path, 'r', encoding='utf-8') as f:
        return json.load(f)


def get_file_info(path: str | Path) -> Dict[str, Any]:
    """
    Get file information (size, mtime, checksum).
    
    Args:
        path: File path
    
    Returns:
        Dictionary with file info
    """
    path_obj = Path(path)
    
    if not path_obj.exists():
        raise FileNotFoundError(f"File not found: {path}")
    
    stat = path_obj.stat()
    
    return {
        'path': str(path_obj),
        'size': stat.st_size,
        'mtime': stat.st_mtime,
        'checksum': calculate_checksum(path_obj),
    }


def list_parquet_files(directory: str | Path, recursive: bool = True) -> list[Path]:
    """
    List all parquet files in a directory.
    
    Args:
        directory: Directory path
        recursive: Search recursively
    
    Returns:
        List of parquet file paths
    """
    dir_path = Path(directory)
    
    if not dir_path.exists():
        return []
    
    if recursive:
        return list(dir_path.rglob('*.parquet'))
    else:
        return list(dir_path.glob('*.parquet'))

