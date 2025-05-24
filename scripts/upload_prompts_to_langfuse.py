#!/usr/bin/env python3
"""
Upload local prompt files to Langfuse for centralized management.
This script helps migrate prompts from local files to Langfuse.
"""

import asyncio
import os
import sys
from pathlib import Path
from typing import Dict, Any
import yaml

# Add src to path so we can import our modules
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from integrations.langfuse_client import LangfuseClient
from prompts.prompt_manager import PromptManager


async def upload_prompts_to_langfuse():
    """Upload all local prompt files to Langfuse."""
    
    print("🚀 Uploading prompts to Langfuse...")
    print()
    
    # Initialize clients
    langfuse_client = LangfuseClient()
    prompt_manager = PromptManager()
    
    # Initialize Langfuse client
    await langfuse_client._initialize()
    
    # Check if Langfuse is available
    if not langfuse_client.available:
        print("❌ Langfuse is not available. Please ensure:")
        print("   1. Services are running: just services-up")
        print("   2. API keys are configured in .env")
        print("   3. Langfuse is accessible at http://localhost:3001")
        return False
    
    print("✅ Langfuse connection verified")
    print()
    
    # Get all prompt files
    prompts_dir = Path(__file__).parent.parent / "src" / "prompts"
    prompt_files = list(prompts_dir.glob("*.md"))
    
    if not prompt_files:
        print("❌ No prompt files found in src/prompts/")
        return False
    
    print(f"📄 Found {len(prompt_files)} prompt files:")
    for file in prompt_files:
        print(f"   • {file.name}")
    print()
    
    # Upload each prompt
    uploaded_count = 0
    for prompt_file in prompt_files:
        try:
            print(f"📤 Uploading {prompt_file.name}...")
            
            # Read and parse prompt file
            content = prompt_file.read_text(encoding='utf-8')
            
            # Split frontmatter and content
            if content.startswith('---'):
                parts = content.split('---', 2)
                if len(parts) >= 3:
                    frontmatter = yaml.safe_load(parts[1])
                    prompt_content = parts[2].strip()
                else:
                    print(f"   ⚠️  Invalid frontmatter in {prompt_file.name}, skipping...")
                    continue
            else:
                print(f"   ⚠️  No frontmatter found in {prompt_file.name}, skipping...")
                continue
            
            # Extract metadata
            prompt_name = frontmatter.get('name', prompt_file.stem)
            version = frontmatter.get('version', 1)
            description = frontmatter.get('description', f'Prompt from {prompt_file.name}')
            
            # Check if prompt already exists
            try:
                existing = await langfuse_client.get_prompt(prompt_name, version)
                if existing:
                    print(f"   ⚠️  Prompt '{prompt_name}' version {version} already exists, skipping...")
                    continue
            except Exception:
                # Prompt doesn't exist, which is expected for new uploads
                pass
            
            # Upload to Langfuse
            success = await langfuse_client.create_prompt(
                name=prompt_name,
                prompt=prompt_content,
                version=version,
                labels=[prompt_file.stem],
                tags=["political-monitoring", "uploaded-from-file"]
            )
            
            if success:
                print(f"   ✅ Uploaded '{prompt_name}' version {version}")
                uploaded_count += 1
            else:
                print(f"   ❌ Failed to upload '{prompt_name}'")
                
        except Exception as e:
            print(f"   ❌ Error uploading {prompt_file.name}: {e}")
            continue
    
    print()
    print(f"🎉 Upload complete! {uploaded_count}/{len(prompt_files)} prompts uploaded successfully")
    
    if uploaded_count > 0:
        print()
        print("📋 Next steps:")
        print("   1. Visit Langfuse: http://localhost:3001")
        print("   2. Go to Prompts section to view uploaded prompts")
        print("   3. Edit prompts in Langfuse UI for centralized management")
        print("   4. Create new versions for A/B testing")
        print()
        print("💡 The system will now prefer Langfuse prompts over local files")
    
    return uploaded_count > 0


async def verify_prompt_access():
    """Verify that prompts can be accessed via the prompt manager."""
    print("🔍 Verifying prompt access...")
    print()
    
    prompt_manager = PromptManager()
    
    # Test each prompt
    prompt_names = [
        "document_analysis",
        "semantic_scoring", 
        "topic_clustering",
        "report_insights"
    ]
    
    for prompt_name in prompt_names:
        try:
            prompt = await prompt_manager.get_prompt(prompt_name)
            if prompt:
                source = "Langfuse" if "langfuse" in prompt.get('source', '').lower() else "Local file"
                print(f"   ✅ {prompt_name}: Available from {source}")
            else:
                print(f"   ❌ {prompt_name}: Not found")
        except Exception as e:
            print(f"   ❌ {prompt_name}: Error - {e}")
    
    print()


def main():
    """Main script entry point."""
    print("=" * 60)
    print("Langfuse Prompt Upload Tool")
    print("=" * 60)
    print()
    
    # Check if we're in the right directory
    if not Path("src/prompts").exists():
        print("❌ Please run this script from the project root directory")
        print("   Current directory should contain 'src/prompts/' folder")
        sys.exit(1)
    
    # Run upload
    success = asyncio.run(upload_prompts_to_langfuse())
    
    if success:
        # Verify access
        asyncio.run(verify_prompt_access())
        print("🎉 Prompt upload and verification complete!")
    else:
        print("❌ Prompt upload failed. Check the errors above.")
        sys.exit(1)


if __name__ == "__main__":
    main()