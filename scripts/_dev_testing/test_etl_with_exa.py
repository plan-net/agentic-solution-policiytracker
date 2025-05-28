#!/usr/bin/env python3
"""
Test ETL pipeline with Exa Direct collector.
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


async def test_etl_pipeline():
    """Test the complete ETL pipeline with Exa Direct."""
    print("🚀 Testing ETL Pipeline with Exa Direct")
    print("=" * 50)
    
    try:
        # 1. Load client config
        print("📋 Loading client configuration...")
        config_loader = ClientConfigLoader()
        company_name = config_loader.get_primary_company_name()
        print(f"   Company: {company_name}")
        
        # 2. Create collector
        print("🔍 Creating news collector...")
        collector = create_news_collector("exa_direct")
        print(f"   Collector: {collector.__class__.__name__}")
        
        # 3. Collect news
        print("📰 Collecting news articles...")
        articles = await collector.collect_news(
            query=company_name,
            max_items=3,  # Small number for testing
            days_back=2
        )
        print(f"   Collected: {len(articles)} articles")
        
        # 4. Create transformer and storage
        print("🔄 Setting up transformer and storage...")
        transformer = MarkdownTransformer()
        storage = get_storage("local")
        
        # 5. Transform and save articles
        print("💾 Transforming and saving articles...")
        saved_count = 0
        
        for i, article in enumerate(articles, 1):
            print(f"   Processing article {i}/{len(articles)}...")
            
            # Transform to markdown
            markdown_content, filename = transformer.transform_article(article)
            
            # Determine path with date-based subdirectory
            from datetime import datetime
            pub_date = article.get('published_date', '')[:10] if article.get('published_date') else datetime.now().strftime('%Y-%m-%d')
            year_month = pub_date[:7]  # YYYY-MM
            file_path = f"news/{year_month}/{filename}"
            
            # Save with metadata
            metadata = {
                'url': article['url'],
                'source': article.get('source'),
                'published_date': article.get('published_date'),
                'exa_id': article.get('exa_id'),
                'collector_type': 'exa_direct'
            }
            
            success = await storage.save_document(markdown_content, file_path, metadata)
            
            if success:
                saved_count += 1
                print(f"     ✅ Saved: {file_path}")
                
                # Show first few lines
                lines = markdown_content.split('\n')[:8]
                for line in lines:
                    if line.strip():
                        print(f"        {line}")
                print("        ...")
                print()
            else:
                print(f"     ❌ Failed to save: {file_path}")
        
        # 6. Summary
        print("📊 ETL Pipeline Results")
        print("=" * 30)
        print(f"Articles collected: {len(articles)}")
        print(f"Articles saved: {saved_count}")
        print(f"Success rate: {(saved_count/len(articles)*100):.1f}%" if articles else "N/A")
        
        # Show content quality comparison
        if articles:
            print(f"\n📝 Content Quality Analysis")
            print("=" * 30)
            for i, article in enumerate(articles, 1):
                content_length = len(article.get('content', ''))
                print(f"Article {i}: {content_length} characters")
                if content_length > 0:
                    print(f"  ✅ Full content available")
                else:
                    print(f"  ⚠️  No content (headline only)")
        
        return saved_count > 0
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = asyncio.run(test_etl_pipeline())
    sys.exit(0 if success else 1)