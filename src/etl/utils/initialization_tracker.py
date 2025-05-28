"""
ETL initialization tracking for managing first-time vs regular collection runs.
"""

import os
import json
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, Optional
import structlog

logger = structlog.get_logger()


class ETLInitializationTracker:
    """Tracks ETL initialization state to determine collection scope."""
    
    def __init__(self, storage_type: str = "local"):
        self.storage_type = storage_type
        self.tracker_file = self._get_tracker_file_path()
        logger.info(f"Initialized ETL tracker for {storage_type} storage: {self.tracker_file}")
    
    def _get_tracker_file_path(self) -> Path:
        """Get the path to the initialization tracker file."""
        if self.storage_type == "local":
            # Store in data directory
            data_dir = Path("data")
            data_dir.mkdir(exist_ok=True)
            return data_dir / "etl_initialization.json"
        else:
            # For Azure storage, use a local cache file
            # In production, this could be stored in Azure or a database
            cache_dir = Path.home() / ".cache" / "policiytracker"
            cache_dir.mkdir(parents=True, exist_ok=True)
            return cache_dir / "etl_initialization.json"
    
    def is_initialized(self, collector_type: str) -> bool:
        """Check if ETL has been initialized for the given collector."""
        try:
            if not self.tracker_file.exists():
                return False
            
            with open(self.tracker_file, 'r') as f:
                data = json.load(f)
            
            return data.get("collectors", {}).get(collector_type, {}).get("initialized", False)
            
        except Exception as e:
            logger.warning(f"Failed to read initialization tracker: {e}")
            return False
    
    def mark_initialized(self, collector_type: str, initialization_days: int, articles_collected: int) -> None:
        """Mark the collector as initialized."""
        try:
            # Load existing data
            data = {}
            if self.tracker_file.exists():
                with open(self.tracker_file, 'r') as f:
                    data = json.load(f)
            
            # Update initialization data
            if "collectors" not in data:
                data["collectors"] = {}
            
            data["collectors"][collector_type] = {
                "initialized": True,
                "initialization_date": datetime.now().isoformat(),
                "initialization_days": initialization_days,
                "articles_collected": articles_collected,
                "last_updated": datetime.now().isoformat()
            }
            
            # Save updated data
            with open(self.tracker_file, 'w') as f:
                json.dump(data, f, indent=2)
            
            logger.info(f"Marked {collector_type} as initialized with {articles_collected} articles from {initialization_days} days")
            
        except Exception as e:
            logger.error(f"Failed to mark collector as initialized: {e}")
            raise
    
    def get_initialization_info(self, collector_type: str) -> Optional[Dict[str, Any]]:
        """Get initialization information for a collector."""
        try:
            if not self.tracker_file.exists():
                return None
            
            with open(self.tracker_file, 'r') as f:
                data = json.load(f)
            
            return data.get("collectors", {}).get(collector_type)
            
        except Exception as e:
            logger.warning(f"Failed to get initialization info: {e}")
            return None
    
    def reset_initialization(self, collector_type: str) -> None:
        """Reset initialization status for a collector (for testing/re-initialization)."""
        try:
            if not self.tracker_file.exists():
                return
            
            with open(self.tracker_file, 'r') as f:
                data = json.load(f)
            
            if "collectors" in data and collector_type in data["collectors"]:
                del data["collectors"][collector_type]
                
                with open(self.tracker_file, 'w') as f:
                    json.dump(data, f, indent=2)
                
                logger.info(f"Reset initialization status for {collector_type}")
            
        except Exception as e:
            logger.error(f"Failed to reset initialization: {e}")
    
    def get_collection_days(self, collector_type: str) -> int:
        """
        Determine how many days back to collect based on initialization status.
        
        Returns:
            Number of days to look back for collection
        """
        # Get configuration
        initialization_days = int(os.getenv("ETL_INITIALIZATION_DAYS", "30"))
        daily_days = int(os.getenv("ETL_DAILY_COLLECTION_DAYS", "1"))
        
        # Check if initialized
        if self.is_initialized(collector_type):
            logger.info(f"Collector {collector_type} already initialized, using daily collection: {daily_days} days")
            return daily_days
        else:
            logger.info(f"Collector {collector_type} not initialized, using initialization period: {initialization_days} days")
            return initialization_days
    
    def get_tracker_status(self) -> Dict[str, Any]:
        """Get complete tracker status for monitoring."""
        try:
            if not self.tracker_file.exists():
                return {"status": "no_tracker_file", "collectors": {}}
            
            with open(self.tracker_file, 'r') as f:
                data = json.load(f)
            
            return {
                "status": "loaded",
                "tracker_file": str(self.tracker_file),
                "collectors": data.get("collectors", {}),
                "configuration": {
                    "initialization_days": os.getenv("ETL_INITIALIZATION_DAYS", "30"),
                    "daily_collection_days": os.getenv("ETL_DAILY_COLLECTION_DAYS", "1")
                }
            }
            
        except Exception as e:
            return {
                "status": "error",
                "error": str(e),
                "tracker_file": str(self.tracker_file)
            }