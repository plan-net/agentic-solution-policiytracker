"""
Prompt management system with Langfuse integration and local fallbacks.
Implements the pattern specified in CLAUDE.md.
"""

import os
import re
from pathlib import Path
from typing import Dict, Any, Optional
import structlog
import aiofiles

# Use official Langfuse client directly
from langfuse import Langfuse
from src.config import settings

logger = structlog.get_logger()


class PromptManager:
    """
    Manages prompts with Langfuse integration and local file fallbacks.

    Implementation pattern:
    1. Store prompts as .md files in src/prompts/
    2. Try Langfuse.get_prompt() first
    3. Fall back to local file if unavailable
    4. Cache in memory after first load
    5. Log fallback occurrences
    """

    def __init__(self):
        self.cache: Dict[str, str] = {}
        self.prompts_dir = Path(__file__).parent
        self.fallback_count = 0
        self._langfuse: Optional[Langfuse] = None
        self._initialized = False

    async def get_prompt(
        self, name: str, variables: Optional[Dict[str, Any]] = None, version: Optional[int] = None
    ) -> str:
        """Get prompt text with variable substitution."""
        prompt_data = await self.get_prompt_with_config(name, variables, version)
        return prompt_data["prompt"]
    
    async def get_prompt_with_config(
        self, name: str, variables: Optional[Dict[str, Any]] = None, version: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Get prompt with config from Langfuse integration and local fallback.

        Args:
            name: Prompt name (matches filename without .md)
            variables: Variables for template substitution
            version: Specific prompt version (optional)

        Returns:
            Dict with 'prompt' (rendered text) and 'config' (model settings from Langfuse)
        """
        cache_key = f"{name}:v{version}" if version else name

        # Check memory cache first
        if cache_key in self.cache:
            logger.debug("Prompt cache hit", prompt_name=name, version=version)
            cached_data = self.cache[cache_key]
            return {
                "prompt": self._substitute_variables(cached_data["prompt"], variables or {}),
                "config": cached_data.get("config", {})
            }

        # Try Langfuse first
        try:
            prompt_data = await self._get_from_langfuse_with_config(name, version)
            if prompt_data:
                self.cache[cache_key] = prompt_data
                logger.info("Prompt loaded from Langfuse", prompt_name=name, version=version)
                return {
                    "prompt": self._substitute_variables(prompt_data["prompt"], variables or {}),
                    "config": prompt_data.get("config", {})
                }

        except Exception as e:
            logger.warning("Failed to load prompt from Langfuse", prompt_name=name, error=str(e))

        # Fall back to local file
        try:
            prompt_text = await self._get_from_local_file(name)
            fallback_data = {"prompt": prompt_text, "config": {}}
            self.cache[cache_key] = fallback_data
            self.fallback_count += 1
            logger.info(
                "Prompt loaded from local file (fallback)",
                prompt_name=name,
                total_fallbacks=self.fallback_count,
            )
            return {
                "prompt": self._substitute_variables(prompt_text, variables or {}),
                "config": {}  # No config from local files
            }

        except Exception as e:
            logger.error("Failed to load prompt from local file", prompt_name=name, error=str(e))
            raise ValueError(f"Unable to load prompt '{name}' from any source")

    def _initialize_langfuse(self) -> None:
        """Initialize official Langfuse client."""
        if self._initialized:
            return
            
        try:
            if not all([settings.LANGFUSE_SECRET_KEY, settings.LANGFUSE_PUBLIC_KEY, settings.LANGFUSE_HOST]):
                logger.info("Langfuse not configured, will use local prompts only")
                self._initialized = True
                return
                
            self._langfuse = Langfuse(
                secret_key=settings.LANGFUSE_SECRET_KEY,
                public_key=settings.LANGFUSE_PUBLIC_KEY,
                host=settings.LANGFUSE_HOST,
            )
            
            # Test connection
            self._langfuse.auth_check()
            logger.info("Official Langfuse client initialized successfully")
            self._initialized = True
            
        except Exception as e:
            logger.warning(f"Failed to initialize Langfuse: {e}, using local prompts only")
            self._langfuse = None
            self._initialized = True

    async def _get_from_langfuse(self, name: str, version: Optional[int]) -> Optional[str]:
        """Try to get prompt text from Langfuse using official client."""
        data = await self._get_from_langfuse_with_config(name, version)
        return data["prompt"] if data else None

    async def _get_from_langfuse_with_config(self, name: str, version: Optional[int]) -> Optional[Dict[str, Any]]:
        """Try to get prompt with config from Langfuse using official client."""
        try:
            self._initialize_langfuse()
            
            if not self._langfuse:
                logger.debug(f"Langfuse not available for prompt '{name}'")
                return None
            
            if version is not None:
                # Specific version requested
                prompt = self._langfuse.get_prompt(name=name, version=version)
            else:
                # Default to production label for current active version
                prompt = self._langfuse.get_prompt(name=name, label="production")
            
            return {
                "prompt": prompt.prompt,
                "config": getattr(prompt, 'config', {}) or {}  # Handle case where config might be None
            }
            
        except Exception as e:
            logger.warning(f"Langfuse prompt retrieval failed for '{name}': {e}")
            return None

    async def _get_from_local_file(self, name: str) -> str:
        """Load prompt from local markdown file."""
        file_path = self.prompts_dir / f"{name}.md"

        if not file_path.exists():
            raise FileNotFoundError(f"Prompt file not found: {file_path}")

        async with aiofiles.open(file_path, "r", encoding="utf-8") as f:
            content = await f.read()

        # Parse frontmatter and extract prompt content
        return self._parse_prompt_file(content)

    def _parse_prompt_file(self, content: str) -> str:
        """Parse prompt file and extract content after frontmatter."""
        # Split frontmatter and content
        parts = content.split("---", 2)

        if len(parts) >= 3:
            # Has frontmatter - return content after second ---
            return parts[2].strip()
        else:
            # No frontmatter - return entire content
            return content.strip()

    def _substitute_variables(self, template: str, variables: Dict[str, Any]) -> str:
        """Substitute {{variable}} placeholders with actual values."""
        result = template

        for key, value in variables.items():
            # Handle different value types
            if isinstance(value, list):
                value_str = ", ".join(str(v) for v in value)
            elif isinstance(value, dict):
                value_str = str(value)  # Could be improved with better formatting
            else:
                value_str = str(value)

            # Replace {{key}} with value
            pattern = r"\{\{" + re.escape(key) + r"\}\}"
            result = re.sub(pattern, value_str, result)

        return result

    async def preload_prompts(self) -> None:
        """Preload all available prompts into cache."""
        prompt_files = list(self.prompts_dir.glob("*.md"))

        for prompt_file in prompt_files:
            prompt_name = prompt_file.stem
            try:
                await self.get_prompt(prompt_name)
                logger.debug("Preloaded prompt", prompt_name=prompt_name)
            except Exception as e:
                logger.warning("Failed to preload prompt", prompt_name=prompt_name, error=str(e))

    def get_cache_stats(self) -> Dict[str, Any]:
        """Get cache statistics for monitoring."""
        return {
            "cached_prompts": len(self.cache),
            "fallback_count": self.fallback_count,
            "available_prompts": [f.stem for f in self.prompts_dir.glob("*.md")],
        }

    def clear_cache(self) -> None:
        """Clear prompt cache."""
        self.cache.clear()
        logger.info("Prompt cache cleared")


# Global instance
prompt_manager = PromptManager()
