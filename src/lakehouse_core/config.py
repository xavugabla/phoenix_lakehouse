"""
Configuration loading and validation for pipeline tasks.

Uses Pydantic models to validate dataset configurations.
"""
import os
from pathlib import Path
from typing import Dict, Any, Optional, List

import yaml
from pydantic import BaseModel, Field, field_validator


class LakehouseCatalogConfig(BaseModel):
    """Configuration for the Iceberg Catalog (BigQuery)."""
    name: str
    project: str
    dataset: str

class LakehousePaths(BaseModel):
    """Named prefixes within the lakehouse bucket."""

    raw_zone: str = "raw"
    bronze_zone: str = "bronze"
    silver_zone: str = "silver"
    gold_zone: str = "gold"
    manifests: str = "data/manifests"


class TableContract(BaseModel):
    """Declarative mapping for a logical table across zones."""

    bronze: Optional[str] = None
    silver: Optional[str] = None
    gold: Optional[str] = None
    partitions: List[str] = Field(default_factory=list)
    description: Optional[str] = None


class LakehouseConfig(BaseModel):
    """Configuration for the Data Lakehouse."""

    gcs_bucket: str
    gcs_prefix: str
    catalog_type: str = "file"  # "file" or "bigquery"
    catalog_file: str = "catalogues/iceberg_catalog.json"  # For file-based catalog
    catalog: Optional[LakehouseCatalogConfig] = None  # Optional, only for BigQuery catalog
    namespaces: Dict[str, str] = Field(default_factory=dict)
    paths: Optional[LakehousePaths] = None
    tables: Dict[str, TableContract] = Field(default_factory=dict)


class RetryConfig(BaseModel):
    """Retry configuration."""
    total: int = 5
    backoff: float = 0.5
    max_delay: int = 60


class StorageConfig(BaseModel):
    """Storage configuration."""
    bucket: str = "novogrid-workqueue"
    prefix: str = "data/cenace"
    enable_versioning: bool = False
    checksum_algorithm: str = "md5"


class LocalStorageConfig(BaseModel):
    """Local storage configuration."""
    base_path: str = "data/local"
    prefer_consolidated: bool = True


class DatasetConfig(BaseModel):
    """Configuration for a single dataset."""
    description: str
    api_path: str
    markets: List[str] = Field(default_factory=lambda: ["MDA", "MTR"])
    regions: List[str] = Field(default_factory=lambda: ["SIN", "BCA", "BCS"])
    
    # API constraints
    max_nodes_per_request: Optional[int] = None
    max_zones_per_request: Optional[int] = None
    max_days_per_request: int = 7
    
    # Data structure
    raw_format: str = "json"
    partition_keys: List[str] = Field(default_factory=list)
    
    # Catalog reference
    catalog_file: Optional[str] = None
    catalog_key: Optional[str] = None
    
    # Transformation
    schema_version: str
    required_fields: List[str] = Field(default_factory=list)
    
    @field_validator('markets', 'regions', 'partition_keys', 'required_fields')
    @classmethod
    def validate_list_not_empty(cls, v):
        if isinstance(v, list) and len(v) == 0:
            raise ValueError("List cannot be empty")
        return v


class ConsolidationConfig(BaseModel):
    """Consolidation configuration."""
    partition_by: List[str] = Field(default_factory=lambda: ["market", "region", "zone"])
    time_partition: str = "year"  # year, month, or all
    compression: str = "snappy"
    row_group_size: int = 128 * 1024 * 1024  # 128MB
    deduplicate: bool = True
    sort_by: List[str] = Field(default_factory=lambda: ["timestamp"])


class CatalogConfig(BaseModel):
    """Catalog enrichment configuration."""
    base_path: str = "catalogues/cenace_catalogues"
    output_format: List[str] = Field(default_factory=lambda: ["json", "parquet"])
    partition_by: List[str] = Field(default_factory=lambda: ["region"])
    incremental: bool = True


class MonitoringConfig(BaseModel):
    """Monitoring configuration."""
    min_rows_per_partition: int = 1
    max_missing_days: int = 7
    alert_on_failure: bool = True
    alert_on_stale_data: bool = True
    stale_threshold_days: int = 2


class PipelineConfig(BaseModel):
    """Complete pipeline configuration."""
    # Base paths
    raw_root: str = "data/raw"
    staged_root: str = "data/staged"
    consolidated_root: str = "data/consolidated"
    local_root: str = "data/local"
    
    # API settings
    api_base_url: str = "https://ws01.cenace.gob.mx:8082"
    user_agent: str = "CENACE-Data-Collector/1.0"
    verify_ssl: bool = False
    timeout: int = 60
    
    # Retry settings
    retries: RetryConfig = Field(default_factory=RetryConfig)
    
    # Rate limiting
    rate_limit_delay: float = 3.0
    
    # Storage
    gcs_bucket: str = "novogrid-workqueue"
    gcs_prefix: str = "data/cenace"
    
    # Partitioning
    partition_format: str = "hive"
    
    # Dataset configurations
    datasets: Dict[str, DatasetConfig] = Field(default_factory=dict)
    
    # Storage configuration
    storage: Dict[str, Any] = Field(default_factory=dict)
    
    # Consolidation configuration
    consolidation: ConsolidationConfig = Field(default_factory=ConsolidationConfig)
    
    # Catalog configuration
    catalog: CatalogConfig = Field(default_factory=CatalogConfig)
    
    # Monitoring configuration
    monitoring: MonitoringConfig = Field(default_factory=MonitoringConfig)

    # Lakehouse configuration
    lakehouse: Optional[LakehouseConfig] = None


class ConfigError(Exception):
    """Configuration error."""
    pass


def _load_lakehouse_settings() -> Optional[Dict[str, Any]]:
    """
    Load the dedicated lakehouse settings file if it exists.
    """
    candidate_paths = [
        Path("configs/lakehouse.yaml"),
        Path(__file__).resolve().parent.parent.parent / "configs" / "lakehouse.yaml",
    ]

    for candidate in candidate_paths:
        if candidate.exists():
            try:
                with open(candidate, "r", encoding="utf-8") as handle:
                    data = yaml.safe_load(handle) or {}
                return data.get("lakehouse", data)
            except yaml.YAMLError as exc:
                raise ConfigError(f"Failed to parse lakehouse settings: {exc}") from exc
            except Exception as exc:
                raise ConfigError(f"Failed to read lakehouse settings: {exc}") from exc
    return None


def load_config(config_path: Optional[str] = None) -> PipelineConfig:
    """
    Load configuration from YAML file.
    
    Args:
        config_path: Path to config file (default: configs/datasets.yaml)
    
    Returns:
        PipelineConfig instance
    
    Raises:
        ConfigError: If config file not found or invalid
    """
    if config_path is None:
        # Try default locations
        candidates = [
            'configs/datasets.yaml',
            'configs/datasets.yml',
            Path(__file__).parent.parent.parent / 'configs' / 'datasets.yaml',
        ]
        for candidate in candidates:
            candidate_path = Path(candidate) if not isinstance(candidate, Path) else candidate
            if candidate_path.exists():
                config_path = str(candidate_path)
                break
        
        if config_path is None:
            raise ConfigError(
                f"Config file not found. Tried: {', '.join(str(c) for c in candidates)}"
            )
    
    config_file = Path(config_path)
    if not config_file.exists():
        raise ConfigError(f"Config file not found: {config_path}")
    
    try:
        with open(config_file, 'r', encoding='utf-8') as f:
            config_dict = yaml.safe_load(f) or {}
    except yaml.YAMLError as e:
        raise ConfigError(f"Failed to parse YAML config: {e}")
    except Exception as e:
        raise ConfigError(f"Failed to read config file: {e}")
    
    # Extract defaults and merge with dataset configs
    defaults = config_dict.get('defaults', {})
    datasets_raw = config_dict.get('datasets', {})
    
    # Merge defaults into each dataset config
    datasets = {}
    for dataset_id, dataset_raw in datasets_raw.items():
        merged = {**defaults, **dataset_raw}
        datasets[dataset_id] = DatasetConfig(**merged)
    
    # Build complete config
    config_dict['datasets'] = datasets
    
    # Parse nested configs
    if 'consolidation' in config_dict:
        config_dict['consolidation'] = ConsolidationConfig(**config_dict['consolidation'])
    if 'catalog' in config_dict:
        config_dict['catalog'] = CatalogConfig(**config_dict['catalog'])
    if 'monitoring' in config_dict:
        config_dict['monitoring'] = MonitoringConfig(**config_dict['monitoring'])
    
    # Prefer dedicated lakehouse.yaml overrides if present
    lakehouse_override = _load_lakehouse_settings()
    if lakehouse_override:
        config_dict['lakehouse'] = lakehouse_override

    if 'lakehouse' in config_dict:
        config_dict['lakehouse'] = LakehouseConfig(**config_dict['lakehouse'])
        
    try:
        return PipelineConfig(**config_dict)
    except Exception as e:
        raise ConfigError(f"Failed to validate config: {e}")


def get_dataset_config(config: PipelineConfig, dataset_id: str) -> DatasetConfig:
    """
    Get configuration for a specific dataset.
    
    Args:
        config: Pipeline configuration
        dataset_id: Dataset identifier
    
    Returns:
        Dataset configuration
    
    Raises:
        ConfigError: If dataset not found
    """
    if dataset_id not in config.datasets:
        available = list(config.datasets.keys())
        raise ConfigError(
            f"Dataset '{dataset_id}' not found in config. "
            f"Available: {', '.join(available[:10])}"
            + (f" and {len(available) - 10} more" if len(available) > 10 else "")
        )
    
    return config.datasets[dataset_id]

