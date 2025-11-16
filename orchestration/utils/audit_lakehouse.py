"""
Utility script to audit Iceberg table locations against the configured lakehouse.

This is used while re-enabling the BigQuery catalog to ensure we know which
GCS paths should be registered. It inspects the configured datasets and prints
the inferred Iceberg table locations along with any on-disk consolidated data
that already exists locally.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, List

import structlog

# Ensure src/ is on the path when running as a script
SRC_ROOT = Path(__file__).resolve().parent.parent.parent / "src"
if str(SRC_ROOT) not in os.sys.path:
    os.sys.path.insert(0, str(SRC_ROOT))

from pipeline_tasks.config import PipelineConfig, load_config

logger = structlog.get_logger()


@dataclass
class TableAudit:
    dataset_id: str
    gcs_path: str
    local_partitions: List[Path]


def _list_local_partitions(consolidated_root: Path, dataset_id: str) -> List[Path]:
    dataset_root = consolidated_root / dataset_id.split("_")[-1]
    if not dataset_root.exists():
        return []
    return [p for p in dataset_root.glob("**/*.parquet")]


def audit_tables(config: PipelineConfig) -> Iterable[TableAudit]:
    bucket = config.lakehouse.gcs_bucket if config.lakehouse else config.gcs_bucket
    prefix = ""
    if config.lakehouse and config.lakehouse.gcs_prefix:
        prefix = config.lakehouse.gcs_prefix.strip("/")

    base = f"gs://{bucket}" + (f"/{prefix}" if prefix else "")

    results: List[TableAudit] = []
    for dataset_id in sorted(config.datasets.keys()):
        gcs_path = f"{base}/{dataset_id.split('_', 1)[-1]}"
        local_partitions = _list_local_partitions(Path(config.consolidated_root), dataset_id.split("_")[-1])
        results.append(TableAudit(dataset_id=dataset_id, gcs_path=gcs_path, local_partitions=local_partitions))
    return results


def print_audit_report(audits: Iterable[TableAudit]) -> None:
    for audit in audits:
        logger.info(
            "lakehouse_audit",
            dataset=audit.dataset_id,
            gcs_path=audit.gcs_path,
            local_partitions=len(audit.local_partitions),
        )


def main() -> None:
    config = load_config()
    audits = audit_tables(config)
    print_audit_report(audits)


if __name__ == "__main__":
    main()

