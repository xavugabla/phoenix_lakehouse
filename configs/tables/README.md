# Table Contracts Directory

This directory contains modular table contract definitions, organized by domain.

## Structure

Each file in this directory defines table contracts for a specific domain:

```
configs/tables/
├── README.md           # This file
├── cenace.yaml         # CENACE energy data tables
├── weather.yaml        # Weather observation tables
└── revenue.yaml        # Revenue modeling tables
```

## File Format

Each YAML file should contain a `tables` dictionary:

```yaml
# configs/tables/cenace.yaml
tables:
  bronze.pend:
    domain: "cenace"
    zone: "bronze"
    schema: "pend_bronze"
    partition_by: ["market", "region", "zone", "year"]
  
  bronze.pml:
    domain: "cenace"
    zone: "bronze"
    schema: "pml_bronze"
    partition_by: ["market", "region", "node", "year"]
```

## Benefits

- **Modular**: Each domain is self-contained
- **Scalable**: Add new domains without touching existing files
- **Maintainable**: Easy to find and edit domain-specific tables
- **Version Control**: Clear git diffs per domain

## Naming Convention

- Use descriptive filenames: `{domain}.yaml` (e.g., `cenace.yaml`, `weather.yaml`)
- Table names: `{zone}.{table_name}` (e.g., `bronze.pend`, `silver.energy_prices`)

## Adding New Tables

1. Create or edit the appropriate domain file (e.g., `configs/tables/cenace.yaml`)
2. Add table contracts following the format above
3. The config loader will automatically merge all table contracts

## Conflicts

If the same table name appears in multiple files, the main `configs/lakehouse.yaml` takes precedence, then files are processed alphabetically (last wins). Avoid conflicts by using clear domain boundaries.

