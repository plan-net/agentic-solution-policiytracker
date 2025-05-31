"""
News collectors for the ETL pipeline.
"""

# Import collectors with graceful error handling
_collectors = {}

try:
    from .apify_news import ApifyNewsCollector

    _collectors["ApifyNewsCollector"] = ApifyNewsCollector
except ImportError:
    pass

try:
    from .exa_news import ExaNewsCollector

    _collectors["ExaNewsCollector"] = ExaNewsCollector
except ImportError:
    pass

try:
    from .exa_direct import ExaDirectCollector

    _collectors["ExaDirectCollector"] = ExaDirectCollector
except ImportError:
    pass

try:
    from .policy_landscape import PolicyLandscapeCollector

    _collectors["PolicyLandscapeCollector"] = PolicyLandscapeCollector
except ImportError:
    pass

# Factory functions should always be available
try:
    from .factory import create_news_collector, get_available_collectors, validate_collector_config

    _factory_available = True
except ImportError:
    _factory_available = False

# Export what's available
__all__ = list(_collectors.keys())
if _factory_available:
    __all__.extend(
        ["create_news_collector", "get_available_collectors", "validate_collector_config"]
    )

# Add to module namespace
globals().update(_collectors)
if _factory_available:
    globals().update(
        {
            "create_news_collector": create_news_collector,
            "get_available_collectors": get_available_collectors,
            "validate_collector_config": validate_collector_config,
        }
    )
