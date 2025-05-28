"""
ETL (Extract, Transform, Load) module for Political Monitoring Agent.

This module provides components for:
- Collecting news data from external sources (Apify)
- Transforming data into standardized formats (Markdown)
- Loading data into storage systems (Local, Azure)
- Orchestrating the entire pipeline via Airflow

Architecture:
    collectors/ - Data collection from external APIs
    transformers/ - Data transformation and cleaning
    storage/ - Storage abstractions (local, cloud)
    dags/ - Airflow DAG definitions
    utils/ - Shared utilities and configuration
"""

from .collectors.apify_news import ApifyNewsCollector
from .transformers.markdown_transformer import MarkdownTransformer
from .storage import get_storage, BaseStorage, LocalStorage, AzureStorage
from .utils.config_loader import ClientConfigLoader

__all__ = [
    'ApifyNewsCollector',
    'MarkdownTransformer', 
    'get_storage',
    'BaseStorage',
    'LocalStorage',
    'AzureStorage',
    'ClientConfigLoader'
]