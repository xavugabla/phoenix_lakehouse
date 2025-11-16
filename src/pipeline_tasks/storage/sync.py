"""
Storage sync task for uploading consolidated files to GCS.

Uses manifest-driven sync with checksum verification.
"""
from datetime import datetime
from pathlib import Path
from typing import List, Optional, Dict
from prefect import task
import structlog

from pipeline_tasks.config import load_config
from pipeline_tasks.schemas.catalog_node import ConsolidatedPartition
from pipeline_tasks.io.gcs import GCSClient
from pipeline_tasks.io.local import get_file_info, calculate_checksum
from pipeline_tasks.storage.manifest import SyncManifest, FileManifest, save_manifest

logger = structlog.get_logger()


@task(name="sync_to_gcs", retries=2)
def sync_to_gcs(
    consolidated_partitions: List[ConsolidatedPartition],
    config_path: Optional[str] = None,
    dry_run: bool = False
) -> SyncManifest:
    """
    Sync consolidated partitions to GCS with manifest tracking.
    
    Args:
        consolidated_partitions: List of consolidated partition metadata
        config_path: Optional path to config file
        dry_run: If True, don't actually upload
    
    Returns:
        SyncManifest with sync results
    """
    config = load_config(config_path)
    
    # Initialize GCS client
    gcs_client = GCSClient(
        bucket_name=config.gcs_bucket,
        prefix=config.gcs_prefix
    )
    
    # Create sync manifest
    sync_id = f"sync_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}"
    manifest = SyncManifest(
        dataset="cenace",
        sync_id=sync_id,
        started_at=datetime.utcnow(),
        stats={
            'uploaded': 0,
            'skipped': 0,
            'failed': 0
        }
    )
    
    for partition in consolidated_partitions:
        try:
            local_path = Path(partition.output_path_local)
            
            if not local_path.exists():
                logger.warning("file_not_found", path=str(local_path))
                manifest.stats['failed'] += 1
                continue
            
            # Get file info
            file_info = get_file_info(local_path)
            
            # Construct GCS path
            # e.g., data/cenace/pend/market=MDA/region=SIN/zone=ACAPULCO/data_2024.parquet
            rel_path = local_path.relative_to(Path(config.consolidated_root))
            gcs_path = str(rel_path).replace('\\', '/')
            
            # Check if blob already exists and matches
            blob_info = gcs_client.get_blob_info(gcs_path)
            
            if blob_info and blob_info['md5']:
                # Compare checksums
                local_checksum = file_info['checksum']
                if blob_info['md5'] == local_checksum:
                    logger.info("skipped_existing", path=gcs_path)
                    manifest.stats['skipped'] += 1
                    
                    # Add to manifest anyway
                    file_manifest = FileManifest(
                        path=str(local_path),
                        size=file_info['size'],
                        checksum=local_checksum,
                        mtime=file_info['mtime'],
                        gcs_path=gcs_path,
                        gcs_checksum=blob_info['md5']
                    )
                    manifest.files.append(file_manifest)
                    continue
            
            # Upload file
            if not dry_run:
                try:
                    uploaded_path = gcs_client.upload_file(
                        local_path=local_path,
                        blob_path=gcs_path,
                        checksum=file_info['checksum'],
                        resumable=True
                    )
                    
                    # Update partition metadata
                    partition.output_path_gcs = f"gs://{config.gcs_bucket}/{uploaded_path}"
                    partition.synced_at = datetime.utcnow()
                    
                    # Get uploaded blob info
                    uploaded_blob_info = gcs_client.get_blob_info(uploaded_path)
                    
                    file_manifest = FileManifest(
                        path=str(local_path),
                        size=file_info['size'],
                        checksum=file_info['checksum'],
                        mtime=file_info['mtime'],
                        uploaded_at=datetime.utcnow(),
                        gcs_path=uploaded_path,
                        gcs_checksum=uploaded_blob_info['md5'] if uploaded_blob_info else None
                    )
                    
                    manifest.files.append(file_manifest)
                    manifest.stats['uploaded'] += 1
                    
                    logger.info(
                        "uploaded",
                        local=str(local_path),
                        gcs=uploaded_path,
                        size=file_info['size']
                    )
                
                except Exception as e:
                    logger.error("upload_failed", path=str(local_path), error=str(e))
                    manifest.stats['failed'] += 1
            else:
                # Dry run - just log
                logger.info("dry_run_upload", local=str(local_path), gcs=gcs_path)
                manifest.stats['uploaded'] += 1
        
        except Exception as e:
            logger.error("sync_error", partition=partition.manifest_id, error=str(e))
            manifest.stats['failed'] += 1
            continue
    
    # Complete manifest
    manifest.completed_at = datetime.utcnow()
    
    # Save manifest
    if not dry_run:
        manifest_dir = Path("data/manifests")
        manifest_dir.mkdir(parents=True, exist_ok=True)
        manifest_file = manifest_dir / f"{sync_id}.json"
        save_manifest(manifest, manifest_file)
        logger.info("manifest_saved", path=str(manifest_file))
    
    logger.info(
        "sync_complete",
        uploaded=manifest.stats['uploaded'],
        skipped=manifest.stats['skipped'],
        failed=manifest.stats['failed']
    )
    
    return manifest

