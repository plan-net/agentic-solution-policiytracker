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

# Core components that should always be available
from .transformers.markdown_transformer import MarkdownTransformer
from .storage import get_storage, BaseStorage, LocalStorage, AzureStorage
from .utils.config_loader import ClientConfigLoader

# Optional collectors with graceful failure
_collectors = {}

try:
    from .collectors.apify_news import ApifyNewsCollector
    _collectors['ApifyNewsCollector'] = ApifyNewsCollector
except ImportError:
    pass

try:
    from .collectors.exa_direct import ExaDirectCollector
    _collectors['ExaDirectCollector'] = ExaDirectCollector
except ImportError:
    pass

try:
    from .collectors.policy_landscape import PolicyLandscapeCollector
    _collectors['PolicyLandscapeCollector'] = PolicyLandscapeCollector
except ImportError:
    pass

# Export what's available
__all__ = [
    'MarkdownTransformer', 
    'get_storage',
    'BaseStorage',
    'LocalStorage',
    'AzureStorage',
    'ClientConfigLoader'
] + list(_collectors.keys())

# Add collectors to module namespace
globals().update(_collectors)