"""
Contract loader and validator for datasets.

This module provides functionality to load and validate dataset contracts
from YAML files.
"""
from pathlib import Path
from typing import Dict, Any, Optional, List
import yaml
from pydantic import BaseModel, Field, ValidationError


class ParamDefinition(BaseModel):
    """Definition of a runtime parameter."""
    name: str
    type: str
    required: bool = False
    allowed_values: Optional[List[Any]] = None
    description: Optional[str] = None


class ColumnDefinition(BaseModel):
    """Definition of a schema column."""
    name: str
    type: str


class SchemaDefinition(BaseModel):
    """Definition of dataset schema."""
    columns: List[ColumnDefinition]


class PartitioningDefinition(BaseModel):
    """Definition of partitioning strategy."""
    keys: List[str]


class StorageDefinition(BaseModel):
    """Definition of storage paths."""
    bronze: str
    silver: str
    gold: str


class SourceDefinition(BaseModel):
    """Definition of data source."""
    type: str
    script_path: Optional[str] = None
    description: Optional[str] = None


class DatasetContract(BaseModel):
    """Complete dataset contract definition."""
    model_config = {"protected_namespaces": ()}
    
    dataset_id: str
    version: str
    params: List[ParamDefinition]
    schema: SchemaDefinition
    partitioning: PartitioningDefinition
    storage: StorageDefinition
    source: SourceDefinition


class ContractError(Exception):
    """Contract loading or validation error."""
    pass


# Cache for loaded contracts
_contract_cache: Dict[str, DatasetContract] = {}


def _get_contracts_dir() -> Path:
    """
    Get the contracts directory path.
    
    Returns:
        Path to contracts directory
    """
    # Try relative to current working directory
    candidates = [
        Path("src/contracts_core/contracts"),
        Path(__file__).parent / "contracts",
    ]
    
    for candidate in candidates:
        if candidate.exists() and candidate.is_dir():
            return candidate
    
    raise ContractError(
        f"Contracts directory not found. Tried: {', '.join(str(c) for c in candidates)}"
    )


def load_contract(dataset_id: str, reload: bool = False) -> DatasetContract:
    """
    Load and validate a dataset contract by dataset_id.
    
    Args:
        dataset_id: Unique identifier for the dataset (e.g., "cenace_pml")
        reload: If True, reload from disk even if cached
    
    Returns:
        DatasetContract instance
    
    Raises:
        ContractError: If contract file not found or validation fails
    """
    # Check cache
    if not reload and dataset_id in _contract_cache:
        return _contract_cache[dataset_id]
    
    # Find contract file
    contracts_dir = _get_contracts_dir()
    contract_file = contracts_dir / f"{dataset_id}.yaml"
    
    if not contract_file.exists():
        available = [f.stem for f in contracts_dir.glob("*.yaml")]
        raise ContractError(
            f"Contract file not found for dataset_id '{dataset_id}'. "
            f"Available contracts: {', '.join(available)}"
        )
    
    # Load YAML
    try:
        with open(contract_file, 'r', encoding='utf-8') as f:
            contract_dict = yaml.safe_load(f)
    except yaml.YAMLError as e:
        raise ContractError(f"Failed to parse contract YAML for '{dataset_id}': {e}")
    except Exception as e:
        raise ContractError(f"Failed to read contract file for '{dataset_id}': {e}")
    
    # Validate and create contract
    try:
        contract = DatasetContract(**contract_dict)
    except ValidationError as e:
        raise ContractError(f"Invalid contract for '{dataset_id}': {e}")
    
    # Verify dataset_id matches filename
    if contract.dataset_id != dataset_id:
        raise ContractError(
            f"Contract dataset_id '{contract.dataset_id}' does not match "
            f"requested dataset_id '{dataset_id}'"
        )
    
    # Cache and return
    _contract_cache[dataset_id] = contract
    return contract


def list_available_contracts() -> List[str]:
    """
    List all available dataset contracts.
    
    Returns:
        List of dataset_ids for available contracts
    """
    try:
        contracts_dir = _get_contracts_dir()
        return sorted([f.stem for f in contracts_dir.glob("*.yaml")])
    except ContractError:
        return []


def get_contract_path(dataset_id: str) -> Path:
    """
    Get the file path for a dataset contract.
    
    Args:
        dataset_id: Unique identifier for the dataset
    
    Returns:
        Path to contract YAML file
    
    Raises:
        ContractError: If contract file not found
    """
    contracts_dir = _get_contracts_dir()
    contract_file = contracts_dir / f"{dataset_id}.yaml"
    
    if not contract_file.exists():
        raise ContractError(f"Contract file not found for dataset_id '{dataset_id}'")
    
    return contract_file
