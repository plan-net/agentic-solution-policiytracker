"""
Storage module for ETL pipeline.
"""

from .base import BaseStorage
from .local import LocalStorage
from .azure import AzureStorage

__all__ = ['BaseStorage', 'LocalStorage', 'AzureStorage', 'get_storage']


def get_storage(storage_type: str = "local", **kwargs) -> BaseStorage:
    """Factory function to get storage implementation."""
    if storage_type == "local":
        return LocalStorage(**kwargs)
    elif storage_type == "azure":
        return AzureStorage(**kwargs)
    else:
        raise ValueError(f"Unknown storage type: {storage_type}")