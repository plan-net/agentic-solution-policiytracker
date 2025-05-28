#!/usr/bin/env python3
"""
Test ETL initialization system.
"""

import asyncio
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

# Load environment variables from .env file
from dotenv import load_dotenv
load_dotenv()

from src.etl.collectors import create_news_collector
from src.etl.transformers.markdown_transformer import MarkdownTransformer
from src.etl.storage import get_storage
from src.etl.utils.config_loader import ClientConfigLoader
from src.etl.utils.initialization_tracker import ETLInitializationTracker


async def test_initialization_flow():
    """Test the complete initialization flow."""
    print("🚀 Testing ETL Initialization Flow")
    print("=" * 50)
    
    # 1. Setup
    config_loader = ClientConfigLoader()
    company_name = config_loader.get_primary_company_name()
    collector_type = "exa_direct"
    
    print(f"Company: {company_name}")
    print(f"Collector: {collector_type}")
    
    # 2. Check initial status
    tracker = ETLInitializationTracker()
    print(f"\nInitial Status:")
    print(f"  Initialized: {tracker.is_initialized(collector_type)}")
    print(f"  Collection days: {tracker.get_collection_days(collector_type)}")
    
    # 3. Create collector and test collection
    print(f"\nTesting Collection...")
    collector = create_news_collector(collector_type)
    
    # Simulate initialization collection (small amount for testing)
    days_back = 7  # Use 7 days for testing instead of 30
    articles = await collector.collect_news(
        query=company_name,
        max_items=5,  # Small number for testing
        days_back=days_back
    )
    
    print(f"  Collected: {len(articles)} articles from {days_back} days")
    
    # 4. Process articles
    print(f"\nProcessing Articles...")
    transformer = MarkdownTransformer()
    storage = get_storage("local")
    
    saved_count = 0
    for article in articles:
        try:
            markdown_content, filename = transformer.transform_article(article)
            
            # Use news subdirectory to avoid conflicts
            from datetime import datetime
            pub_date = article.get('published_date', '')[:10] if article.get('published_date') else datetime.now().strftime('%Y-%m-%d')
            year_month = pub_date[:7]
            file_path = f"test_init/{year_month}/{filename}"
            
            metadata = {
                'url': article['url'],
                'source': article.get('source'),
                'published_date': article.get('published_date'),
                'exa_id': article.get('exa_id'),
                'collector_type': collector_type,
                'test_run': True
            }
            
            success = await storage.save_document(markdown_content, file_path, metadata)
            if success:
                saved_count += 1
        except Exception as e:
            print(f"    ❌ Failed to process article: {e}")
    
    print(f"  Saved: {saved_count} articles")
    
    # 5. Mark as initialized
    print(f"\nMarking as Initialized...")
    tracker.mark_initialized(
        collector_type=collector_type,
        initialization_days=days_back,
        articles_collected=saved_count
    )
    
    # 6. Check final status
    print(f"\nFinal Status:")
    print(f"  Initialized: {tracker.is_initialized(collector_type)}")
    print(f"  Collection days: {tracker.get_collection_days(collector_type)}")
    
    init_info = tracker.get_initialization_info(collector_type)
    if init_info:
        print(f"  Initialization date: {init_info.get('initialization_date')}")
        print(f"  Articles collected: {init_info.get('articles_collected')}")
        print(f"  Days used: {init_info.get('initialization_days')}")
    
    # 7. Test second run (should be daily mode)
    print(f"\nTesting Second Run (should be daily mode)...")
    days_back_second = tracker.get_collection_days(collector_type)
    print(f"  Days back for second run: {days_back_second}")
    
    return True


async def main():
    """Main test function."""
    try:
        success = await test_initialization_flow()
        if success:
            print("\n✅ Initialization test completed successfully!")
            print("\nTo reset for testing again, run:")
            print("  just etl-reset exa_direct")
        else:
            print("\n❌ Initialization test failed!")
            sys.exit(1)
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())