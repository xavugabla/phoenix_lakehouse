"""
Master schemas for the CENACE datasets.

This file serves as the single source of truth for the data structure of
each Iceberg table in the Lakehouse. It uses PyIceberg's type system.
"""
from pyiceberg.schema import Schema
from pyiceberg.types import (
    NestedField,
    StringType,
    TimestampType,
    FloatType,
    IntegerType,
    BooleanType,
    MapType,
    ListType,
    StructType,
)

# ============================================================================
# DATA TABLE SCHEMAS
# ============================================================================

# CENACE PEND (Precios de Energía en Nodos Distribuidos)
PEND_SCHEMA = Schema(
    NestedField(1, "system", StringType(), required=True, doc="The electric system (e.g., SIN, BCA, BCS)"),
    NestedField(2, "market", StringType(), required=True, doc="The market type (e.g., MDA, MTR)"),
    NestedField(3, "region", StringType(), required=True, doc="The control region within the system"),
    NestedField(4, "zone", StringType(), required=True, doc="The load zone"),
    NestedField(5, "timestamp", TimestampType(), required=True, doc="The timestamp of the measurement (UTC)"),
    NestedField(6, "pz", FloatType(), required=False, doc="Price of Energy at the Distributed Node ($/MWh)"),
    NestedField(7, "pz_ene", FloatType(), required=False, doc="Energy component of the price ($/MWh)"),
    NestedField(8, "pz_per", FloatType(), required=False, doc="Loss component of the price ($/MWh)"),
    NestedField(9, "pz_cng", FloatType(), required=False, doc="Congestion component of the price ($/MWh)"),
)

# ============================================================================
# CENACE PML (Precios Marginales Locales)
# ============================================================================
PML_SCHEMA = Schema(
    NestedField(1, "system", StringType(), required=True),
    NestedField(2, "market", StringType(), required=True),
    NestedField(3, "region", StringType(), required=True),
    NestedField(4, "node", StringType(), required=True),
    NestedField(5, "timestamp", TimestampType(), required=True),
    NestedField(6, "pml", FloatType(), required=False, doc="Locational Marginal Price (PML) ($/MWh)"),
    NestedField(7, "pml_ene", FloatType(), required=False, doc="Energy component of PML ($/MWh)"),
    NestedField(8, "pml_per", FloatType(), required=False, doc="Loss component of PML ($/MWh)"),
    NestedField(9, "pml_cng", FloatType(), required=False, doc="Congestion component of PML ($/MWh)"),
)

# ============================================================================
# CENACE PSC (Precios de Servicios Conexos)
# ============================================================================
PSC_SCHEMA = Schema(
    NestedField(1, "system", StringType(), required=True),
    NestedField(2, "market", StringType(), required=True),
    NestedField(3, "region", StringType(), required=True),
    NestedField(4, "zone", StringType(), required=True),  # Often represents the whole system
    NestedField(5, "timestamp", TimestampType(), required=True),
    NestedField(6, "price", FloatType(), required=False, doc="Price of the ancillary service"),
    NestedField(7, "service_type", StringType(), required=False, doc="Type of ancillary service"),
)

# ============================================================================
# ENTITY & CATALOGUE TABLE SCHEMAS
# ============================================================================

# CENACE Node Catalog (from cenace_node_catalog.json)
NODE_CATALOG_SCHEMA = Schema(
    NestedField(100, "node_id", StringType(), required=True),
    NestedField(101, "name", StringType(), required=False),
    NestedField(102, "system", StringType(), required=False),
    NestedField(103, "voltage_kv", FloatType(), required=False),
    NestedField(104, "load_zone", StringType(), required=False),
    NestedField(105, "transmission_zone", StringType(), required=False),
    NestedField(106, "state", StringType(), required=False),
    NestedField(107, "municipality", StringType(), required=False),
    # For simplicity, we can flatten the rich geospatial data
    NestedField(108, "latitude", FloatType(), required=False),
    NestedField(109, "longitude", FloatType(), required=False),
    NestedField(110, "altitude_m", FloatType(), required=False),
    NestedField(111, "cvegeo", StringType(), required=False),
    NestedField(112, "locality", StringType(), required=False),
    NestedField(113, "population", IntegerType(), required=False),
)

# CENACE Load Zones (from cenace_load_zones.json)
# This will just be a list of zone names.
LOAD_ZONES_SCHEMA = Schema(
    NestedField(200, "zone_name", StringType(), required=True),
)

# Bridge table to link Load Zones to Nodes
LOAD_ZONE_NODES_SCHEMA = Schema(
    NestedField(300, "zone_name", StringType(), required=True),
    NestedField(301, "node_id", StringType(), required=True),
)

# CENACE Reserve Zones (from cenace_reserve_zones.json)
RESERVE_ZONES_SCHEMA = Schema(
    NestedField(400, "zone_name", StringType(), required=True),
)

# Bridge table to link Reserve Zones to Nodes
RESERVE_ZONE_NODES_SCHEMA = Schema(
    NestedField(500, "zone_name", StringType(), required=True),
    NestedField(501, "node_id", StringType(), required=True),
)


# A dictionary to easily access all master schemas
MASTER_SCHEMAS = {
    "pend": PEND_SCHEMA,
    "pml": PML_SCHEMA,
    "psc": PSC_SCHEMA,
    # Entity Schemas
    "cenace_node_catalog": NODE_CATALOG_SCHEMA,
    "cenace_load_zones": LOAD_ZONES_SCHEMA,
    "cenace_load_zone_nodes": LOAD_ZONE_NODES_SCHEMA,
    "cenace_reserve_zones": RESERVE_ZONES_SCHEMA,
    "cenace_reserve_zone_nodes": RESERVE_ZONE_NODES_SCHEMA,
}
