"""
Schema definitions for CENACE PML (Precios Marginales Locales) dataset.

Defines PyArrow schemas and Pydantic models for data contracts.
"""
from datetime import datetime
from typing import Optional
import pyarrow as pa
from pydantic import BaseModel, Field


# PyArrow schema for PML parquet files
# Includes component breakdown (pml_ene, pml_per, pml_cng) for analytical use cases
PML_SCHEMA = pa.schema([
    pa.field('timestamp', pa.timestamp('ns', tz='UTC'), nullable=False),
    pa.field('node', pa.string(), nullable=False),
    pa.field('pml', pa.float64(), nullable=False),  # Total price (Precio Marginal Local)
    pa.field('pml_ene', pa.float64(), nullable=False),  # Energy component
    pa.field('pml_per', pa.float64(), nullable=False),  # Losses component
    pa.field('pml_cng', pa.float64(), nullable=False),  # Congestion component
    pa.field('market', pa.string(), nullable=False),  # MDA or MTR
    pa.field('region', pa.string(), nullable=False),  # SIN, BCA, or BCS
])


class PmlRecord(BaseModel):
    """Pydantic model for a single PML record."""
    timestamp: datetime
    node: str
    pml: float  # Total price (Precio Marginal Local)
    pml_ene: float  # Energy component
    pml_per: float  # Losses component
    pml_cng: float  # Congestion component
    market: str = Field(pattern=r'^(MDA|MTR)$')
    region: str = Field(pattern=r'^(SIN|BCA|BCS)$')
    
    class Config:
        json_schema_extra = {
            "example": {
                "timestamp": "2025-01-15T10:00:00Z",
                "node": "07ACU-115",
                "pml": 1234.56,
                "pml_ene": 1000.00,
                "pml_per": 150.00,
                "pml_cng": 84.56,
                "market": "MDA",
                "region": "SIN"
            }
        }


class PmlRawBatch(BaseModel):
    """Metadata for a raw PML batch."""
    dataset: str = "pml"
    batch_key: str  # e.g., "SIN-MDA-2025-02-10"
    source_urls: list[str] = Field(default_factory=list)
    raw_path: str
    status: str = Field(pattern=r'^(SUCCESS|FAILED)$')
    row_count: int = 0
    fetched_at: datetime
    market: str
    region: str
    nodes: list[str] = Field(default_factory=list)
    start_date: datetime
    end_date: datetime


class PmlStagePartition(BaseModel):
    """Metadata for a staged PML partition."""
    dataset: str = "pml"
    partition: dict[str, str | int]  # e.g., {"market": "MDA", "region": "SIN", "node": "07ACU-115", "year": 2025}
    staged_path: str
    schema_version: str = "pml_v1"
    row_count: int
    start_ts: datetime
    end_ts: datetime
    created_by: str = "transform.cenace_pml"


def validate_pml_dataframe(df) -> bool:
    """
    Validate a DataFrame against the PML schema.
    
    Args:
        df: pandas DataFrame to validate
    
    Returns:
        True if valid, raises ValueError if invalid
    """
    required_columns = ['timestamp', 'node', 'pml', 'pml_ene', 'pml_per', 'pml_cng', 'market', 'region']
    missing = [col for col in required_columns if col not in df.columns]
    if missing:
        raise ValueError(f"Missing required columns: {missing}")
    
    # Check data types
    if not df['timestamp'].dtype.name.startswith('datetime'):
        raise ValueError("Column 'timestamp' must be datetime type")
    
    price_columns = ['pml', 'pml_ene', 'pml_per', 'pml_cng']
    for col in price_columns:
        if df[col].dtype.name not in ['float64', 'float32']:
            raise ValueError(f"Column '{col}' must be float type")
    
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

