"""
Configuration loading and validation for the lakehouse platform.

This module provides the core configuration models and loading functions
for GCS storage layout, Iceberg catalog, and table contracts.

Table contracts can be defined in:
1. configs/lakehouse.yaml (tables: {})
2. configs/tables/*.yaml (modular per-domain files)
"""
from pathlib import Path
from typing import Dict, Optional, Any

import yaml
from pydantic import BaseModel, Field


class LakehouseConfig(BaseModel):
    """Configuration for the Data Lakehouse platform."""
    bucket: str
    prefix: str = ""
    zones: Dict[str, str] = Field(default_factory=dict)
    catalog: Dict[str, str] = Field(default_factory=dict)
    tables: Dict[str, Dict[str, Any]] = Field(default_factory=dict)  # Allow Any for partition_by lists


class ConfigError(Exception):
    """Configuration error."""
    pass


_config: Optional[LakehouseConfig] = None


def _load_table_contracts(config_dir: Path) -> Dict[str, Dict[str, str]]:
    """
    Load table contracts from modular YAML files.
    
    Looks for files in configs/tables/*.yaml and merges them.
    Each file should contain a 'tables' dict with table contracts.
    
    Args:
        config_dir: Directory containing config files
    
    Returns:
        Merged dictionary of all table contracts
    """
    tables_dir = config_dir / "tables"
    all_tables = {}
    
    if not tables_dir.exists():
        return all_tables
    
    # Load all YAML files in configs/tables/
    for table_file in tables_dir.glob("*.yaml"):
        try:
            with open(table_file, 'r', encoding='utf-8') as f:
                table_config = yaml.safe_load(f) or {}
            
            # Extract tables from file (supports both formats)
            file_tables = table_config.get('tables', table_config)
            
            if isinstance(file_tables, dict):
                # Merge into all_tables, warn on conflicts
                for table_name, contract in file_tables.items():
                    if table_name in all_tables:
                        raise ConfigError(
                            f"Duplicate table contract '{table_name}' found in {table_file.name}. "
                            f"Table contracts must be unique across all files."
                        )
                    all_tables[table_name] = contract
        except yaml.YAMLError as e:
            raise ConfigError(f"Failed to parse table config {table_file}: {e}")
        except Exception as e:
            raise ConfigError(f"Failed to load table config {table_file}: {e}")
    
    return all_tables


def get_lakehouse_config(config_path: Optional[str] = None) -> LakehouseConfig:
    """
    Get the lakehouse configuration (cached after first load).
    
    Loads configuration from:
    1. Main config file (configs/lakehouse.yaml)
    2. Modular table contracts (configs/tables/*.yaml)
    
    Args:
        config_path: Path to main config file (default: configs/lakehouse.yaml)
    
    Returns:
        LakehouseConfig instance
    
    Raises:
        ConfigError: If config file not found or invalid
    """
    global _config
    
    if _config is not None:
        return _config
    
    if config_path is None:
        candidates = [
            Path("configs/lakehouse.yaml"),
            Path(__file__).resolve().parent.parent.parent / "configs" / "lakehouse.yaml",
        ]
        for candidate in candidates:
            if candidate.exists():
                config_path = str(candidate)
                break
        
        if config_path is None:
            raise ConfigError(
                f"Config file not found. Tried: {', '.join(str(c) for c in candidates)}"
            )
    
    config_file = Path(config_path)
    if not config_file.exists():
        raise ConfigError(f"Config file not found: {config_path}")
    
    config_dir = config_file.parent
    
    try:
        # Load main config
        with open(config_file, 'r', encoding='utf-8') as f:
            config_dict = yaml.safe_load(f) or {}
    except yaml.YAMLError as e:
        raise ConfigError(f"Failed to parse YAML config: {e}")
    except Exception as e:
        raise ConfigError(f"Failed to read config file: {e}")
    
    # Load modular table contracts
    modular_tables = _load_table_contracts(config_dir)
    
    # Merge tables: main config tables + modular tables
    # Main config takes precedence if there are conflicts
    main_tables = config_dict.get('tables', {})
    all_tables = {**modular_tables, **main_tables}  # Main config overrides modular
    
    config_dict['tables'] = all_tables
    
    try:
        _config = LakehouseConfig(**config_dict)
        return _config
    except Exception as e:
        raise ConfigError(f"Failed to validate lakehouse config: {e}")
