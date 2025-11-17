"""
Example: Web app backend for querying Iceberg tables.

This example shows how to create a REST API backend that queries
Iceberg tables for use in a web application (e.g., React frontend).
"""
import sys
from pathlib import Path
from typing import Optional, List
from datetime import datetime

# Add 'src' to the Python path
src_path = Path(__file__).resolve().parent.parent / "src"
if str(src_path) not in sys.path:
    sys.path.insert(0, str(src_path))

try:
    from fastapi import FastAPI, HTTPException, Query
    from fastapi.middleware.cors import CORSMiddleware
    from pydantic import BaseModel
except ImportError:
    print("FastAPI not installed. Install with: pip install fastapi uvicorn")
    sys.exit(1)

from lakehouse_core.io.iceberg import load_table_by_name
import pandas as pd

app = FastAPI(title="Iceberg Data API", version="1.0.0")

# Enable CORS for web app
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class TableDataResponse(BaseModel):
    """Response model for table data."""
    table: str
    rows: int
    columns: List[str]
    data: List[dict]


@app.get("/")
async def root():
    """API root endpoint."""
    return {
        "name": "Iceberg Data API",
        "version": "1.0.0",
        "endpoints": [
            "/api/tables",
            "/api/data/{table_name}",
            "/api/latest-timestamp/{table_name}"
        ]
    }


@app.get("/api/tables")
async def list_tables():
    """List all available tables."""
    from lakehouse_core.io.iceberg_catalog import load_catalog
    
    catalog = load_catalog()
    return {
        "tables": list(catalog.keys()),
        "count": len(catalog)
    }


@app.get("/api/data/{table_name}", response_model=TableDataResponse)
async def get_table_data(
    table_name: str,
    region: Optional[str] = Query(None, description="Filter by region"),
    market: Optional[str] = Query(None, description="Filter by market"),
    zone: Optional[str] = Query(None, description="Filter by zone"),
    start_date: Optional[str] = Query(None, description="Start date (ISO format)"),
    end_date: Optional[str] = Query(None, description="End date (ISO format)"),
    limit: int = Query(100, ge=1, le=10000, description="Maximum rows to return")
):
    """
    Query an Iceberg table with optional filters.
    
    Example:
        GET /api/data/pend?region=SIN&market=MDA&limit=10
    """
    try:
        # Load table
        table = load_table_by_name(table_name)
        
        # Build filter
        filters = []
        if region:
            filters.append(f"region = '{region}'")
        if market:
            filters.append(f"market = '{market}'")
        if zone:
            filters.append(f"zone = '{zone}'")
        if start_date:
            filters.append(f"timestamp >= '{start_date}'")
        if end_date:
            filters.append(f"timestamp < '{end_date}'")
        
        row_filter = " AND ".join(filters) if filters else None
        
        # Query table
        df = table.scan(
            row_filter=row_filter,
            limit=limit
        ).to_pandas()
        
        return TableDataResponse(
            table=table_name,
            rows=len(df),
            columns=list(df.columns),
            data=df.to_dict(orient="records")
        )
        
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Query error: {str(e)}")


@app.get("/api/latest-timestamp/{table_name}")
async def get_latest_timestamp(
    table_name: str,
    region: Optional[str] = Query(None),
    market: Optional[str] = Query(None)
):
    """
    Get the latest timestamp in a table.
    
    Example:
        GET /api/latest-timestamp/pend?region=SIN&market=MDA
    """
    try:
        table = load_table_by_name(table_name)
        
        # Build filter
        filters = []
        if region:
            filters.append(f"region = '{region}'")
        if market:
            filters.append(f"market = '{market}'")
        
        row_filter = " AND ".join(filters) if filters else None
        
        # Query for timestamps
        df = table.scan(
            row_filter=row_filter,
            selected_fields=("timestamp",)
        ).to_pandas()
        
        if df.empty:
            return {
                "table": table_name,
                "latest_timestamp": None,
                "message": "No data found"
            }
        
        latest_ts = df['timestamp'].max()
        
        return {
            "table": table_name,
            "latest_timestamp": latest_ts.isoformat() if isinstance(latest_ts, pd.Timestamp) else str(latest_ts),
            "row_count": len(df)
        }
        
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Query error: {str(e)}")


@app.get("/api/schema/{table_name}")
async def get_table_schema(table_name: str):
    """Get the schema of a table."""
    try:
        table = load_table_by_name(table_name)
        
        schema_info = []
        for field in table.schema().fields:
            schema_info.append({
                "name": field.name,
                "type": str(field.field_type),
                "required": field.required,
                "doc": field.doc if hasattr(field, 'doc') else None
            })
        
        return {
            "table": table_name,
            "schema": schema_info
        }
        
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error: {str(e)}")


if __name__ == "__main__":
    import uvicorn
    print("Starting Iceberg Data API server...")
    print("API will be available at http://localhost:8000")
    print("API docs at http://localhost:8000/docs")
    uvicorn.run(app, host="0.0.0.0", port=8000)

