"""
Schema definitions for CENACE node catalog.

Defines Pydantic models for catalog entries.
"""
from datetime import datetime
from typing import Optional, Dict, List, Any
from pydantic import BaseModel, Field


class Geocode(BaseModel):
    """Geographic coordinates."""
    lat: float
    lon: float
    source: str  # e.g., "CENACE", "OSM", "INEGI"


class MarketAvailability(BaseModel):
    """Market data availability information."""
    data_points: int = 0
    years: List[int] = Field(default_factory=list)
    last_updated: Optional[datetime] = None


class CatalogEntry(BaseModel):
    """Catalog entry for a CENACE node."""
    node_id: str
    geocode: Optional[Geocode] = None
    markets: Dict[str, MarketAvailability] = Field(default_factory=dict)  # market -> availability
    zones: List[str] = Field(default_factory=list)
    pend_status: Optional[Dict[str, Any]] = None
    psc_status: Optional[Dict[str, Any]] = None
    enrichment: Optional[Dict[str, Any]] = None
    updated_at: datetime


class ConsolidatedPartition(BaseModel):
    """Metadata for a consolidated partition."""
    dataset: str
    partition: dict[str, str | int]  # Partition keys
    output_path_local: str
    output_path_gcs: Optional[str] = None
    row_count: int
    years: List[int] = Field(default_factory=list)
    checksum: Optional[str] = None  # MD5 checksum
    manifest_id: str
    synced_at: Optional[datetime] = None

