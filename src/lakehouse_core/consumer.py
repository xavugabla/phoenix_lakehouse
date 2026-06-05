"""
Consumer-facing contract helpers.

These helpers expose a minimal, cross-repo contract surface that can be used by
non-Python consumers and deployment tooling without re-implementing lakehouse
constants in every repo.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, Optional

from .config import LakehouseConfig, get_lakehouse_config


def get_consumer_contract(config_path: Optional[str] = None) -> Dict[str, Any]:
    """
    Build a minimal consumer contract from the canonical lakehouse config.

    The returned structure is intentionally small: bucket, warehouse, catalog,
    zone names, and legacy archive bucket aliases.
    """
    config: LakehouseConfig = get_lakehouse_config(config_path)

    return {
        "contract_source": "phoenix_lakehouse",
        "bucket": config.bucket,
        "warehouse": config.warehouse or config.catalog.get("warehouse", ""),
        "catalog": dict(config.catalog),
        "zones": dict(config.zones),
        "legacy": dict(config.legacy),
    }


def write_consumer_contract(
    output_path: str | Path,
    config_path: Optional[str] = None,
) -> Path:
    """Write the consumer contract JSON artifact to disk."""
    output = Path(output_path)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        json.dumps(get_consumer_contract(config_path), indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return output
