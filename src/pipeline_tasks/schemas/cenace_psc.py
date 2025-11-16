"""
Schema definitions for CENACE PSC (Precios de Servicios Conexos) dataset.

Defines PyArrow schemas and Pydantic models for data contracts.
"""
from datetime import datetime
from typing import Optional
import pyarrow as pa
from pydantic import BaseModel, Field


# PyArrow schema for PSC parquet files
PSC_SCHEMA = pa.schema([
    pa.field('timestamp', pa.timestamp('ns', tz='UTC'), nullable=False),
    pa.field('zone', pa.string(), nullable=False),
    pa.field('price', pa.float64(), nullable=False),
    pa.field('service_type', pa.string(), nullable=False),  # Type of ancillary service
    pa.field('market', pa.string(), nullable=False),  # MDA or MTR
    pa.field('region', pa.string(), nullable=False),  # SIN, BCA, or BCS
])


class PscRecord(BaseModel):
    """Pydantic model for a single PSC record."""
    timestamp: datetime
    zone: str
    price: float
    service_type: str
    market: str = Field(pattern=r'^(MDA|MTR)$')
    region: str = Field(pattern=r'^(SIN|BCA|BCS)$')
    
    class Config:
        json_schema_extra = {
            "example": {
                "timestamp": "2025-01-15T10:00:00Z",
                "zone": "SIN",
                "price": 1234.56,
                "service_type": "reserve",
                "market": "MDA",
                "region": "SIN"
            }
        }


class PscRawBatch(BaseModel):
    """Metadata for a raw PSC batch."""
    dataset: str = "psc"
    batch_key: str  # e.g., "SIN-MDA-2025-02-10"
    source_urls: list[str] = Field(default_factory=list)
    raw_path: str
    status: str = Field(pattern=r'^(SUCCESS|FAILED)$')
    row_count: int = 0
    fetched_at: datetime
    market: str
    region: str
    zones: list[str] = Field(default_factory=list)
    start_date: datetime
    end_date: datetime


class PscStagePartition(BaseModel):
    """Metadata for a staged PSC partition."""
    dataset: str = "psc"
    partition: dict[str, str | int]  # e.g., {"market": "MDA", "region": "SIN", "zone": "SIN", "year": 2025}
    staged_path: str
    schema_version: str = "psc_v1"
    row_count: int
    start_ts: datetime
    end_ts: datetime
    created_by: str = "transform.cenace_psc"


def validate_psc_dataframe(df) -> bool:
    """
    Validate a DataFrame against the PSC schema.
    
    Args:
        df: pandas DataFrame to validate
    
    Returns:
        True if valid, raises ValueError if invalid
    """
    required_columns = ['timestamp', 'zone', 'price', 'service_type', 'market', 'region']
    missing = [col for col in required_columns if col not in df.columns]
    if missing:
        raise ValueError(f"Missing required columns: {missing}")
    
    # Check data types
    if not df['timestamp'].dtype.name.startswith('datetime'):
        raise ValueError("Column 'timestamp' must be datetime type")
    
    if df['price'].dtype.name not in ['float64', 'float32']:
        raise ValueError("Column 'price' must be float type")
    
    # Check market values
    valid_markets = {'MDA', 'MTR'}
    invalid_markets = set(df['market'].unique()) - valid_markets
    if invalid_markets:
        raise ValueError(f"Invalid market values: {invalid_markets}")
    
    # Check region values
    valid_regions = {'SIN', 'BCA', 'BCS'}
    invalid_regions = set(df['region'].unique()) - valid_regions
    if invalid_regions:
        raise ValueError(f"Invalid region values: {invalid_regions}")
    
    return True

