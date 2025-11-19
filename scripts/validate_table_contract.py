"""
Validate a table contract follows lakehouse standards.

Usage:
    python scripts/validate_table_contract.py bronze.pend
    python scripts/validate_table_contract.py bronze.your_new_table

Note: Requires phoenix_lakehouse to be installed (pip install -e .)
"""
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

try:
    from lakehouse_core import get_lakehouse_config
    from lakehouse_core.tables import get_table_contract, get_table_identifier
except ImportError as e:
    print(f"❌ Failed to import lakehouse_core: {e}")
    print("   Please install phoenix_lakehouse: pip install -e .")
    sys.exit(1)


def validate_table_contract(table_name: str) -> bool:
    """
    Validate table contract follows lakehouse standards.
    
    Args:
        table_name: Full table name (e.g., "bronze.pend")
    
    Returns:
        True if valid, False otherwise
    """
    config = get_lakehouse_config()
    contract = get_table_contract(table_name)
    
    if not contract:
        print(f"❌ Table contract not found: {table_name}")
        print(f"   Available tables: {list(config.tables.keys())}")
        return False
    
    errors = []
    warnings = []
    
    # Check required fields
    required_fields = ["domain", "zone", "schema", "partition_by"]
    for field in required_fields:
        if field not in contract:
            errors.append(f"Missing required field: '{field}'")
    
    # Check zone is valid
    valid_zones = ["raw", "bronze", "silver", "gold"]
    zone = contract.get("zone")
    if zone not in valid_zones:
        errors.append(f"Invalid zone: '{zone}'. Must be one of: {valid_zones}")
    
    # Check partition_by is list
    partition_by = contract.get("partition_by")
    if partition_by is not None:
        if not isinstance(partition_by, list):
            errors.append("'partition_by' must be a list")
        elif len(partition_by) == 0:
            warnings.append("'partition_by' is empty (no partitioning)")
    else:
        errors.append("Missing 'partition_by' field")
    
    # Check naming conventions
    if "." not in table_name:
        errors.append(f"Table name must be in format 'zone.table_name', got '{table_name}'")
    else:
        zone_part, table_base = table_name.split(".", 1)
        
        # Check zone matches
        if zone_part != zone:
            errors.append(f"Zone mismatch: table name has '{zone_part}' but contract has '{zone}'")
        
        # Check table name is lowercase
        if table_base != table_base.lower():
            errors.append(f"Table name must be lowercase, got '{table_base}'")
        
        # Check table name is snake_case
        if not (table_base.replace("_", "").isalnum()):
            errors.append(f"Table name must be snake_case (lowercase with underscores), got '{table_base}'")
    
    # Check domain naming
    domain = contract.get("domain")
    if domain:
        if domain != domain.lower():
            errors.append(f"Domain name must be lowercase, got '{domain}'")
        if not domain.replace("_", "").isalnum():
            errors.append(f"Domain name must be snake_case, got '{domain}'")
    
    # Check schema key format
    schema_key = contract.get("schema")
    if schema_key:
        expected_schema = f"{table_base}_{zone}" if "." in table_name else f"{table_name}_{zone}"
        if schema_key != expected_schema:
            warnings.append(
                f"Schema key '{schema_key}' doesn't follow convention '{expected_schema}'. "
                "This is OK if intentional."
            )
    
    # Check identifier format
    try:
        identifier = get_table_identifier(table_name)
        if not isinstance(identifier, tuple) or len(identifier) != 2:
            errors.append(f"Invalid identifier format: {identifier}")
    except Exception as e:
        errors.append(f"Failed to get table identifier: {e}")
    
    # Report results
    if errors:
        print(f"❌ Validation FAILED for '{table_name}':")
        for error in errors:
            print(f"   • {error}")
        return False
    
    if warnings:
        print(f"⚠️  Validation passed with warnings for '{table_name}':")
        for warning in warnings:
            print(f"   • {warning}")
    else:
        print(f"✅ Validation PASSED for '{table_name}'")
        print(f"   Domain: {contract.get('domain')}")
        print(f"   Zone: {contract.get('zone')}")
        print(f"   Schema: {contract.get('schema')}")
        print(f"   Partitions: {contract.get('partition_by')}")
    
    return True


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python scripts/validate_table_contract.py <table_name>")
        print("Example: python scripts/validate_table_contract.py bronze.pend")
        sys.exit(1)
    
    table_name = sys.argv[1]
    success = validate_table_contract(table_name)
    sys.exit(0 if success else 1)

