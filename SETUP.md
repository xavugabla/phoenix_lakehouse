# Lakehouse Core Setup Guide

## Prerequisites

- Python 3.10 or higher
- Google Cloud credentials configured (for GCS access)
- GCS bucket access (for storage and catalog operations)

## Quick Setup

### Windows (PowerShell)

```powershell
# Run the setup script
.\setup.ps1
```

### Manual Setup

```bash
# Create virtual environment
python -m venv .venv

# Activate virtual environment
# Windows:
.\.venv\Scripts\Activate.ps1
# Linux/Mac:
source .venv/bin/activate

# Install package
pip install -e .

# Install development dependencies (optional)
pip install -e ".[dev]"
```

## Configuration

1. **Set up Google Cloud credentials:**
   - Create a service account with Storage Admin role
   - Download JSON key file
   - Set environment variable:
     ```powershell
     $env:GOOGLE_APPLICATION_CREDENTIALS="C:\path\to\credentials.json"
     ```

2. **Configure lakehouse:**
   - Edit `configs/lakehouse.yaml`
   - Set your GCS bucket name
   - Configure catalog warehouse path (e.g., `gs://lakehouse_phoenix/iceberg/`)

3. **Verify setup:**
   ```python
   from lakehouse_core import get_lakehouse_config
   from lakehouse_core.catalogs import get_iceberg_catalog
   
   cfg = get_lakehouse_config()
   print(f"Bucket: {cfg.bucket}")
   print(f"Catalog warehouse: {cfg.catalog['warehouse']}")
   
   catalog = get_iceberg_catalog()
   print("Catalog initialized successfully!")
   ```

## Catalog Configuration

**Important:** This platform uses a **file-based/Hadoop-style catalog on GCS**. The catalog warehouse path stores all Iceberg table metadata (snapshots, schemas, manifests) directly in GCS.

The catalog:
- Type: `hadoop` (file-based)
- Warehouse: `gs://lakehouse_phoenix/iceberg/` (configurable)
- All metadata stored in GCS under the warehouse path
- No external catalog service required

BigQuery is **not** used as an Iceberg catalog in this repo. BigQuery may be used as a compute engine in consuming repositories, but it is not part of the catalog system here.

## Development

```bash
# Activate virtual environment
.\.venv\Scripts\Activate.ps1  # Windows
source .venv/bin/activate     # Linux/Mac

# Run tests (when available)
pytest

# Format code
black src/
isort src/

# Type checking
mypy src/
```

## Troubleshooting

**Import errors:**
- Ensure virtual environment is activated
- Verify package is installed: `pip list | grep lakehouse-core`

**Catalog errors:**
- Verify `GOOGLE_APPLICATION_CREDENTIALS` is set
- Check GCS bucket exists and is accessible
- Verify service account has Storage Admin permissions
- Ensure warehouse path is correctly formatted (must end with `/`)

**Config errors:**
- Ensure `configs/lakehouse.yaml` exists
- Check YAML syntax is valid
- Verify all required fields are present (bucket, catalog.type, catalog.warehouse)
