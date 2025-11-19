"""
Schema helper utilities for Iceberg tables.

This module provides helper functions for creating and managing
PyIceberg schemas. Domain-specific schemas should be defined in
consuming repositories (data-pipeline, data-manager, revenue-models).
"""
from pyiceberg.schema import Schema
from pyiceberg.types import NestedField

__all__ = ["Schema", "NestedField"]

# This file is kept for backward compatibility but should not contain
# domain-specific schemas. Those belong in the consuming repositories.
