"""Prompt templates for agent phases."""

import os
import logging
from typing import Dict, Any, Optional
from pathlib import Path

logger = logging.getLogger(__name__)


class PromptTemplateManager:
    """Manager for loading and formatting prompt templates."""
    
    def __init__(self):
        """Initialize the prompt template manager."""
        self.templates_dir = Path(__file__).parent
        self._templates: Dict[str, str] = {}
        self._load_templates()
    
    def _load_templates(self) -> None:
        """Load all prompt templates from markdown files."""
        template_files = {
            'query_analysis': 'query_analysis.md',
            'tool_selection': 'tool_selection.md', 
            'synthesis': 'synthesis.md',
            'context_awareness': 'context_awareness.md'
        }
        
        for template_name, filename in template_files.items():
            file_path = self.templates_dir / filename
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    self._templates[template_name] = f.read()
                logger.debug(f"Loaded template: {template_name}")
            except FileNotFoundError:
                logger.warning(f"Template file not found: {filename}")
            except Exception as e:
                logger.error(f"Error loading template {filename}: {e}")
    
    def get_template(self, template_name: str, **kwargs) -> str:
        """Get a formatted template with variables substituted."""
        if template_name not in self._templates:
            logger.error(f"Template not found: {template_name}")
            return f"Template '{template_name}' not available."
        
        template = self._templates[template_name]
        
        # Format template with provided variables
        try:
            return template.format(**kwargs)
        except KeyError as e:
            logger.warning(f"Missing template variable: {e}")
            # Return template with missing variables as placeholders
            return template
        except Exception as e:
            logger.error(f"Error formatting template {template_name}: {e}")
            return template
    
    def get_query_analysis_prompt(self, query: str, context: str = "") -> str:
        """Get query analysis prompt."""
        return self.get_template('query_analysis', query=query, context=context)
    
    def get_tool_selection_prompt(self, query: str, intent: str = "", 
                                 available_tools: str = "") -> str:
        """Get tool selection prompt.""" 
        return self.get_template('tool_selection', 
                                query=query, 
                                intent=intent,
                                available_tools=available_tools)
    
    def get_synthesis_prompt(self, query: str, intent: str = "", 
                            tools_used: str = "", tool_results: str = "") -> str:
        """Get response synthesis prompt."""
        return self.get_template('synthesis',
                                query=query,
                                intent=intent, 
                                tools_used=tools_used,
                                tool_results=tool_results)
    
    def get_context_awareness_prompt(self, session_id: str = "",
                                   session_duration: str = "",
                                   recent_queries: str = "",
                                   frequent_entities: str = "",
                                   recent_entities: str = "") -> str:
        """Get context awareness prompt."""
        return self.get_template('context_awareness',
                                session_id=session_id,
                                session_duration=session_duration,
                                recent_queries=recent_queries,
                                frequent_entities=frequent_entities,
                                recent_entities=recent_entities)
    
    def list_templates(self) -> list[str]:
        """List available template names."""
        return list(self._templates.keys())


# Global instance
prompt_manager = PromptTemplateManager()