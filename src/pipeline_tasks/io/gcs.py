"""
Google Cloud Storage utilities for pipeline tasks.
"""
import hashlib
import json
from pathlib import Path
from typing import Optional, Dict, Any, List
from google.cloud import storage
from google.cloud.exceptions import NotFound, GoogleCloudError
import structlog

logger = structlog.get_logger()


class GCSClient:
    """Wrapper for Google Cloud Storage operations."""
    
    def __init__(self, bucket_name: str, prefix: str = ""):
        """
        Initialize GCS client.
        
        Args:
            bucket_name: GCS bucket name
            prefix: Prefix for all operations (e.g., "data/cenace")
        """
        self.bucket_name = bucket_name
        self.prefix = prefix.rstrip('/')
        self.client = storage.Client()
        self.bucket = self.client.bucket(bucket_name)
    
    def _get_blob_path(self, path: str) -> str:
        """Get full blob path with prefix."""
        if self.prefix:
            return f"{self.prefix}/{path.lstrip('/')}"
        return path.lstrip('/')
    
    def upload_file(
        self,
        local_path: str | Path,
        blob_path: Optional[str] = None,
        checksum: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
        resumable: bool = True
    ) -> str:
        """
        Upload a file to GCS.
        
        Args:
            local_path: Local file path
            blob_path: GCS blob path (defaults to local filename)
            checksum: Expected checksum (for verification)
            metadata: Custom metadata to attach
            resumable: Use resumable upload
        
        Returns:
            GCS blob path
        """
        local_path_obj = Path(local_path)
        if not local_path_obj.exists():
            raise FileNotFoundError(f"Local file not found: {local_path}")
        
        if blob_path is None:
            blob_path = local_path_obj.name
        
        full_blob_path = self._get_blob_path(blob_path)
        blob = self.bucket.blob(full_blob_path)
        
        # Set metadata
        if metadata:
            blob.metadata = metadata
        
        # Upload with resumable option
        try:
            if resumable:
                blob.upload_from_filename(
                    str(local_path_obj),
                    if_generation_match=None  # Allow overwrites
                )
            else:
                blob.upload_from_filename(str(local_path_obj))
            
            logger.info(
                "uploaded_file",
                local_path=str(local_path),
                blob_path=full_blob_path,
                size=local_path_obj.stat().st_size
            )
            
            # Verify checksum if provided
            if checksum:
                # Handle md5_hash - it might be bytes or string
                if blob.md5_hash:
                    if isinstance(blob.md5_hash, bytes):
                        blob_checksum = blob.md5_hash.hex()
                    else:
                        blob_checksum = blob.md5_hash
                else:
                    blob_checksum = None
                    
                if blob_checksum and blob_checksum != checksum:
                    logger.warning(
                        "checksum_mismatch",
                        blob_path=full_blob_path,
                        expected=checksum,
                        actual=blob_checksum
                    )
            
            return full_blob_path
        
        except GoogleCloudError as e:
            logger.error(
                "upload_failed",
                local_path=str(local_path),
                blob_path=full_blob_path,
                error=str(e)
            )
            raise
    
    def download_file(
        self,
        blob_path: str,
        local_path: str | Path,
        checksum: Optional[str] = None
    ) -> Path:
        """
        Download a file from GCS.
        
        Args:
            blob_path: GCS blob path
            local_path: Local destination path
            checksum: Expected checksum (for verification)
        
        Returns:
            Local file path
        """
        full_blob_path = self._get_blob_path(blob_path)
        blob = self.bucket.blob(full_blob_path)
        
        if not blob.exists():
            raise NotFound(f"Blob not found: {full_blob_path}")
        
        local_path_obj = Path(local_path)
        local_path_obj.parent.mkdir(parents=True, exist_ok=True)
        
        blob.download_to_filename(str(local_path_obj))
        
        logger.info(
            "downloaded_file",
            blob_path=full_blob_path,
            local_path=str(local_path_obj),
            size=local_path_obj.stat().st_size
        )
        
        # Verify checksum if provided
        if checksum:
            from pipeline_tasks.io.local import calculate_checksum
            local_checksum = calculate_checksum(local_path_obj)
            if local_checksum != checksum:
                logger.warning(
                    "checksum_mismatch",
                    blob_path=full_blob_path,
                    expected=checksum,
                    actual=local_checksum
                )
        
        return local_path_obj
    
    def blob_exists(self, blob_path: str) -> bool:
        """
        Check if a blob exists.
        
        Args:
            blob_path: GCS blob path
        
        Returns:
            True if blob exists
        """
        full_blob_path = self._get_blob_path(blob_path)
        blob = self.bucket.blob(full_blob_path)
        return blob.exists()
    
    def get_blob_info(self, blob_path: str) -> Optional[Dict[str, Any]]:
        """
        Get blob information.
        
        Args:
            blob_path: GCS blob path
        
        Returns:
            Dictionary with blob info or None if not found
        """
        full_blob_path = self._get_blob_path(blob_path)
        blob = self.bucket.blob(full_blob_path)
        
        if not blob.exists():
            return None
        
        # Handle md5_hash - it might be bytes or string
        md5_checksum = None
        if blob.md5_hash:
            if isinstance(blob.md5_hash, bytes):
                md5_checksum = blob.md5_hash.hex()
            else:
                md5_checksum = blob.md5_hash
        
        return {
            'path': full_blob_path,
            'size': blob.size,
            'updated': blob.updated.isoformat() if blob.updated else None,
            'md5': md5_checksum,
            'metadata': blob.metadata or {},
        }
    
    def list_blobs(self, prefix: str = "", recursive: bool = True) -> List[str]:
        """
        List blobs with given prefix.
        
        Args:
            prefix: Prefix to filter by
            recursive: Include subdirectories
        
        Returns:
            List of blob paths
        """
        full_prefix = self._get_blob_path(prefix)
        
        if recursive:
            blobs = self.bucket.list_blobs(prefix=full_prefix)
        else:
            # Non-recursive: only immediate children
            delimiter = '/'
            blobs = self.bucket.list_blobs(prefix=full_prefix, delimiter=delimiter)
        
        return [blob.name for blob in blobs]
    
    def delete_blob(self, blob_path: str) -> bool:
        """
        Delete a blob.
        
        Args:
            blob_path: GCS blob path
        
        Returns:
            True if deleted, False if not found
        """
        full_blob_path = self._get_blob_path(blob_path)
        blob = self.bucket.blob(full_blob_path)
        
        try:
            blob.delete()
            logger.info("deleted_blob", blob_path=full_blob_path)
            return True
        except NotFound:
            logger.warning("blob_not_found", blob_path=full_blob_path)
            return False
    
    def sync_directory(
        self,
        local_dir: str | Path,
        blob_prefix: str = "",
        dry_run: bool = False
    ) -> Dict[str, int]:
        """
        Sync a local directory to GCS.
        
        Args:
            local_dir: Local directory path
            blob_prefix: Prefix for blob paths
            dry_run: If True, don't actually upload
        
        Returns:
            Dictionary with sync statistics
        """
        from pipeline_tasks.io.local import list_parquet_files, get_file_info, calculate_checksum
        
        local_dir_obj = Path(local_dir)
        if not local_dir_obj.exists():
            raise FileNotFoundError(f"Local directory not found: {local_dir}")
        
        stats = {
            'uploaded': 0,
            'skipped': 0,
            'failed': 0
        }
        
        parquet_files = list_parquet_files(local_dir_obj, recursive=True)
        
        for local_file in parquet_files:
            # Get relative path
            rel_path = local_file.relative_to(local_dir_obj)
            blob_path = f"{blob_prefix}/{rel_path}".replace('\\', '/') if blob_prefix else str(rel_path).replace('\\', '/')
            
            # Check if blob exists and is same size
            blob_info = self.get_blob_info(blob_path)
            
            if blob_info:
                local_info = get_file_info(local_file)
                if blob_info['size'] == local_info['size']:
                    # Same size, check checksum
                    if blob_info['md5']:
                        local_checksum = calculate_checksum(local_file)
                        if blob_info['md5'] == local_checksum:
                            stats['skipped'] += 1
                            continue
            
            # Upload file
            if not dry_run:
                try:
                    self.upload_file(local_file, blob_path)
                    stats['uploaded'] += 1
                except Exception as e:
                    logger.error("sync_upload_failed", local_file=str(local_file), error=str(e))
                    stats['failed'] += 1
            else:
                stats['uploaded'] += 1
        
        return stats

