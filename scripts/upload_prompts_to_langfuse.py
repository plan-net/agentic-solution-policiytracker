#!/usr/bin/env python3
"""
Upload local prompt files to Langfuse for centralized management.
This script helps migrate prompts from local files to Langfuse.
"""

import sys
from pathlib import Path

import yaml
from dotenv import load_dotenv

# Load environment variables from .env file BEFORE importing settings
# This ensures API keys and configuration are available
load_dotenv()

# Add src to path so we can import our modules
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from config import settings
from langfuse import Langfuse


def upload_prompts_to_langfuse():
    """Upload all local prompt files to Langfuse."""

    print("🚀 Uploading prompts to Langfuse...")
    print()

    # Initialize official Langfuse client
    try:
        langfuse = Langfuse(
            secret_key=settings.LANGFUSE_SECRET_KEY,
            public_key=settings.LANGFUSE_PUBLIC_KEY,
            host=settings.LANGFUSE_HOST,
        )

        # Test connection
        langfuse.auth_check()
        print("✅ Langfuse connection verified")

    except Exception as e:
        print("❌ Langfuse is not available. Please ensure:")
        print("   1. Services are running: just services-up")
        print("   2. API keys are configured in .env")
        print("   3. Langfuse is accessible at http://localhost:3001")
        print(f"   Error: {e}")
        return False
    print()

    # Get all prompt files (recursively search subdirectories)
    prompts_dir = Path(__file__).parent.parent / "src" / "prompts"
    prompt_files = sorted(prompts_dir.rglob("*.md"))

    if not prompt_files:
        print("❌ No prompt files found in src/prompts/")
        return False

    print(f"📄 Found {len(prompt_files)} prompt files:")
    for file in prompt_files:
        # Show relative path from prompts_dir for clarity
        rel_path = file.relative_to(prompts_dir)
        print(f"   • {rel_path}")
    print()

    # Upload each prompt
    uploaded_count = 0

    for prompt_file in prompt_files:
        try:
            rel_path = prompt_file.relative_to(prompts_dir)
            print(f"📤 Processing {rel_path}...")

            # Read file content
            content = prompt_file.read_text(encoding="utf-8")

            # Parse frontmatter and content
            if content.startswith("---"):
                parts = content.split("---", 2)
                if len(parts) >= 3:
                    frontmatter = yaml.safe_load(parts[1])
                    prompt_content = parts[2].strip()
                else:
                    print(f"   ⚠️  Invalid frontmatter in {rel_path}, skipping...")
                    continue
            else:
                print(f"   ⚠️  No frontmatter found in {rel_path}, skipping...")
                continue

            # Extract metadata
            prompt_name = frontmatter.get("name", prompt_file.stem)
            version = frontmatter.get("version", 1)
            description = frontmatter.get("description", f"Prompt from {prompt_file.name}")

            # Check if prompt already exists - but still upload if we want to add config
            try:
                existing = langfuse.get_prompt(name=prompt_name, label="production")
                if existing:
                    print(
                        f"   ℹ️  Prompt '{prompt_name}' exists, uploading new version with config..."
                    )
                else:
                    print(f"   📤 New prompt '{prompt_name}', uploading...")
            except Exception:
                # Prompt doesn't exist, which is expected for new uploads
                print(f"   📤 New prompt '{prompt_name}', uploading...")

            # Determine the best model for this prompt
            # Use Anthropic for analysis tasks, OpenAI as fallback
            model = (
                settings.ANTHROPIC_MODEL if settings.ANTHROPIC_API_KEY else settings.OPENAI_MODEL
            )

            # Create config for Langfuse prompt
            config = {
                "model": model,
                "temperature": settings.LLM_TEMPERATURE,
                "max_tokens": settings.LLM_MAX_TOKENS,
            }

            # Upload to Langfuse with production label and config
            try:
                langfuse.create_prompt(
                    name=prompt_name,
                    prompt=prompt_content,
                    config=config,  # Include model and temperature settings
                    labels=["production"],  # Use production label for active version
                    tags=["political-monitoring", "uploaded-from-file"],
                )
                print(f"   ✅ Uploaded '{prompt_name}' with production label")
                print(f"      Model: {model}, Temperature: {settings.LLM_TEMPERATURE}")
                uploaded_count += 1
            except Exception as e:
                print(f"   ❌ Failed to upload '{prompt_name}': {e}")

        except Exception as e:
            print(f"   ❌ Error uploading {rel_path}: {e}")
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
    success = upload_prompts_to_langfuse()

    if success:
        print("🎉 Prompt upload complete!")
    else:
        print("❌ Prompt upload failed. Check the errors above.")
        sys.exit(1)


if __name__ == "__main__":
    main()
