#!/usr/bin/env python3
"""
ETL initialization management script.
"""

import asyncio
import os
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

# Load environment variables from .env file
from dotenv import load_dotenv
load_dotenv()

from src.etl.utils.initialization_tracker import ETLInitializationTracker
from src.etl.collectors import get_available_collectors


def show_status():
    """Show current initialization status."""
    print("🔍 ETL Initialization Status")
    print("=" * 40)
    
    tracker = ETLInitializationTracker()
    status = tracker.get_tracker_status()
    
    print(f"Status: {status['status']}")
    print(f"Tracker file: {status.get('tracker_file', 'N/A')}")
    
    if "configuration" in status:
        config = status["configuration"]
        print(f"\nConfiguration:")
        print(f"  Initialization days: {config['initialization_days']}")
        print(f"  Daily collection days: {config['daily_collection_days']}")
    
    available_collectors = get_available_collectors()
    print(f"\nAvailable collectors: {available_collectors}")
    
    collectors = status.get("collectors", {})
    if collectors:
        print(f"\nCollector Status:")
        for collector_type, info in collectors.items():
            if info.get("initialized"):
                print(f"  ✅ {collector_type}: Initialized")
                print(f"     Date: {info.get('initialization_date', 'Unknown')}")
                print(f"     Days: {info.get('initialization_days', 'Unknown')}")
                print(f"     Articles: {info.get('articles_collected', 'Unknown')}")
            else:
                print(f"  ❌ {collector_type}: Not initialized")
    else:
        print(f"\nNo collectors initialized yet.")
    
    print(f"\nNext collection will be:")
    for collector in available_collectors:
        days = tracker.get_collection_days(collector)
        mode = "DAILY" if tracker.is_initialized(collector) else "INITIALIZATION"
        print(f"  {collector}: {mode} ({days} days back)")


def reset_collector(collector_type: str):
    """Reset initialization for a specific collector."""
    tracker = ETLInitializationTracker()
    
    if not tracker.is_initialized(collector_type):
        print(f"❌ Collector {collector_type} is not initialized, nothing to reset")
        return
    
    tracker.reset_initialization(collector_type)
    print(f"✅ Reset initialization for {collector_type}")
    print(f"   Next collection will be INITIALIZATION mode")


def reset_all():
    """Reset initialization for all collectors."""
    available_collectors = get_available_collectors()
    tracker = ETLInitializationTracker()
    
    reset_count = 0
    for collector_type in available_collectors:
        if tracker.is_initialized(collector_type):
            tracker.reset_initialization(collector_type)
            reset_count += 1
            print(f"✅ Reset {collector_type}")
    
    if reset_count == 0:
        print("❌ No collectors were initialized, nothing to reset")
    else:
        print(f"✅ Reset {reset_count} collectors")


def main():
    """Main CLI interface."""
    if len(sys.argv) < 2:
        print("ETL Initialization Manager")
        print("=" * 30)
        print("Usage:")
        print("  python etl_init_manager.py status           # Show status")
        print("  python etl_init_manager.py reset <collector> # Reset specific collector")
        print("  python etl_init_manager.py reset-all        # Reset all collectors")
        print("")
        print("Available collectors:", get_available_collectors())
        sys.exit(1)
    
    command = sys.argv[1].lower()
    
    if command == "status":
        show_status()
    elif command == "reset" and len(sys.argv) == 3:
        collector_type = sys.argv[2]
        available_collectors = get_available_collectors()
        if collector_type not in available_collectors:
            print(f"❌ Unknown collector: {collector_type}")
            print(f"Available collectors: {available_collectors}")
            sys.exit(1)
        reset_collector(collector_type)
    elif command == "reset-all":
        reset_all()
    else:
        print(f"❌ Unknown command: {command}")
        sys.exit(1)


if __name__ == "__main__":
    main()