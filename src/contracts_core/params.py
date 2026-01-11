"""
Runtime parameter validation against dataset contracts.

This module validates that runtime parameters match the contract specifications.
"""
from typing import Dict, Any, List
from datetime import datetime
from .loader import DatasetContract, ParamDefinition, ContractError


class ParamValidationError(Exception):
    """Parameter validation error."""
    pass


def validate_params(params: Dict[str, Any], contract: DatasetContract) -> Dict[str, Any]:
    """
    Validate runtime parameters against a dataset contract.
    
    Args:
        params: Dictionary of runtime parameters to validate
        contract: Dataset contract with parameter definitions
    
    Returns:
        Validated and type-converted parameters dictionary
    
    Raises:
        ParamValidationError: If validation fails
    """
    validated_params = {}
    errors = []
    
    # Check all required parameters are provided
    for param_def in contract.params:
        param_name = param_def.name
        param_value = params.get(param_name)
        
        # Check required
        if param_def.required and param_value is None:
            errors.append(f"Required parameter '{param_name}' is missing")
            continue
        
        # Skip validation for optional missing parameters
        if param_value is None:
            continue
        
        # Validate type and convert
        try:
            converted_value = _validate_and_convert_param(
                param_name, param_value, param_def
            )
            validated_params[param_name] = converted_value
        except ValueError as e:
            errors.append(str(e))
    
    # Check for unexpected parameters
    expected_params = {p.name for p in contract.params}
    provided_params = set(params.keys())
    unexpected = provided_params - expected_params
    
    if unexpected:
        errors.append(
            f"Unexpected parameters provided: {', '.join(unexpected)}"
        )
    
    if errors:
        raise ParamValidationError(
            f"Parameter validation failed for dataset '{contract.dataset_id}':\n  "
            + "\n  ".join(errors)
        )
    
    return validated_params


def _validate_and_convert_param(
    name: str, value: Any, param_def: ParamDefinition
) -> Any:
    """
    Validate and convert a single parameter value.
    
    Args:
        name: Parameter name
        value: Parameter value to validate
        param_def: Parameter definition from contract
    
    Returns:
        Converted parameter value
    
    Raises:
        ValueError: If validation fails
    """
    param_type = param_def.type.lower()
    
    # Type conversion and validation
    if param_type == "string":
        converted = str(value)
    elif param_type == "integer":
        try:
            converted = int(value)
        except (ValueError, TypeError):
            raise ValueError(
                f"Parameter '{name}' must be an integer, got '{value}'"
            )
    elif param_type == "double" or param_type == "float":
        try:
            converted = float(value)
        except (ValueError, TypeError):
            raise ValueError(
                f"Parameter '{name}' must be a float/double, got '{value}'"
            )
    elif param_type == "boolean":
        if isinstance(value, bool):
            converted = value
        elif isinstance(value, str):
            if value.lower() in ("true", "yes", "1"):
                converted = True
            elif value.lower() in ("false", "no", "0"):
                converted = False
            else:
                raise ValueError(
                    f"Parameter '{name}' must be a boolean, got '{value}'"
                )
        else:
            raise ValueError(
                f"Parameter '{name}' must be a boolean, got '{value}'"
            )
    elif param_type == "date" or param_type == "timestamp":
        # Validate date/timestamp format
        if isinstance(value, str):
            try:
                # Try parsing as ISO date
                datetime.fromisoformat(value.replace('Z', '+00:00'))
                converted = value
            except ValueError:
                raise ValueError(
                    f"Parameter '{name}' must be a valid ISO date/timestamp, got '{value}'"
                )
        else:
            converted = str(value)
    else:
        # Unknown type, just pass through as string
        converted = str(value)
    
    # Validate allowed values
    if param_def.allowed_values is not None:
        if converted not in param_def.allowed_values:
            raise ValueError(
                f"Parameter '{name}' value '{converted}' not in allowed values: "
                f"{param_def.allowed_values}"
            )
    
    return converted


def get_missing_required_params(
    params: Dict[str, Any], contract: DatasetContract
) -> List[str]:
    """
    Get list of missing required parameters.
    
    Args:
        params: Dictionary of provided parameters
        contract: Dataset contract
    
    Returns:
        List of missing required parameter names
    """
    missing = []
    for param_def in contract.params:
        if param_def.required and param_def.name not in params:
            missing.append(param_def.name)
    return missing


def get_param_summary(contract: DatasetContract) -> str:
    """
    Get a human-readable summary of parameter requirements.
    
    Args:
        contract: Dataset contract
    
    Returns:
        Formatted string describing parameters
    """
    lines = [f"Parameters for dataset '{contract.dataset_id}':"]
    
    for param_def in contract.params:
        required_str = "REQUIRED" if param_def.required else "optional"
        line = f"  - {param_def.name} ({param_def.type}, {required_str})"
        
        if param_def.allowed_values:
            line += f" - allowed: {param_def.allowed_values}"
        
        if param_def.description:
            line += f"\n    {param_def.description}"
        
        lines.append(line)
    
    return "\n".join(lines)
