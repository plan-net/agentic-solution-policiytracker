import os
from typing import Any, Dict, List

import yaml
import structlog

from src.utils.exceptions import ConfigurationError
from src.utils.validators import validate_context_file

logger = structlog.get_logger()


class ContextManager:
    """Manage client context data and configuration."""
    
    def __init__(self):
        self._context_cache: Dict[str, Dict[str, Any]] = {}
    
    async def load_context(self, context_file_path: str) -> Dict[str, Any]:
        """Load and validate context from YAML file."""
        try:
            logger.info("Loading context file", context_file=context_file_path)
            
            # Check cache first
            if context_file_path in self._context_cache:
                logger.debug("Using cached context", context_file=context_file_path)
                return self._context_cache[context_file_path]
            
            # Validate file exists and is secure
            validate_context_file(context_file_path)
            
            # Load YAML content
            with open(context_file_path, 'r', encoding='utf-8') as file:
                context_data = yaml.safe_load(file)
            
            if not context_data:
                raise ConfigurationError("context_file", "Context file is empty or invalid")
            
            # Validate required structure
            validated_context = self._validate_context_structure(context_data)
            
            # Cache the context
            self._context_cache[context_file_path] = validated_context
            
            logger.info("Context loaded successfully", 
                       context_file=context_file_path,
                       company_terms=len(validated_context.get('company_terms', [])),
                       industries=len(validated_context.get('core_industries', [])))
            
            return validated_context
            
        except yaml.YAMLError as e:
            raise ConfigurationError("context_file", f"Invalid YAML format: {str(e)}")
        except Exception as e:
            raise ConfigurationError("context_file", f"Failed to load context: {str(e)}")
    
    def _validate_context_structure(self, context_data: Dict[str, Any]) -> Dict[str, Any]:
        """Validate and normalize context structure."""
        required_fields = {
            'company_terms': list,
            'core_industries': list,
            'primary_markets': list,
            'strategic_themes': list
        }
        
        validated = {}
        
        # Check required fields
        for field, expected_type in required_fields.items():
            if field not in context_data:
                raise ConfigurationError("context_file", f"Missing required field: {field}")
            
            if not isinstance(context_data[field], expected_type):
                raise ConfigurationError("context_file", f"Field {field} must be a {expected_type.__name__}")
            
            # Normalize to lowercase strings
            if expected_type == list:
                validated[field] = [str(item).lower().strip() for item in context_data[field] if item]
        
        # Optional fields with defaults
        optional_fields = {
            'topic_patterns': {},
            'direct_impact_keywords': [],
            'secondary_markets': [],
            'exclusion_terms': []
        }
        
        for field, default_value in optional_fields.items():
            if field in context_data:
                validated[field] = context_data[field]
            else:
                validated[field] = default_value
        
        # Validate topic patterns structure if present
        if 'topic_patterns' in validated and validated['topic_patterns']:
            self._validate_topic_patterns(validated['topic_patterns'])
        
        return validated
    
    def _validate_topic_patterns(self, topic_patterns: Dict[str, Any]) -> None:
        """Validate topic patterns structure."""
        if not isinstance(topic_patterns, dict):
            raise ConfigurationError("context_file", "topic_patterns must be a dictionary")
        
        for topic_name, keywords in topic_patterns.items():
            if not isinstance(keywords, list):
                raise ConfigurationError("context_file", f"Keywords for topic '{topic_name}' must be a list")
            
            # Ensure all keywords are strings
            for i, keyword in enumerate(keywords):
                if not isinstance(keyword, str):
                    topic_patterns[topic_name][i] = str(keyword)
    
    def get_context_summary(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Get summary statistics of context data."""
        return {
            "company_terms_count": len(context.get('company_terms', [])),
            "core_industries_count": len(context.get('core_industries', [])),
            "primary_markets_count": len(context.get('primary_markets', [])),
            "strategic_themes_count": len(context.get('strategic_themes', [])),
            "topic_patterns_count": len(context.get('topic_patterns', {})),
            "has_direct_impact_keywords": bool(context.get('direct_impact_keywords')),
            "has_secondary_markets": bool(context.get('secondary_markets')),
            "has_exclusion_terms": bool(context.get('exclusion_terms'))
        }
    
    def clear_cache(self) -> None:
        """Clear context cache."""
        self._context_cache.clear()
        logger.info("Context cache cleared")
    
    def create_default_context(self, output_path: str) -> None:
        """Create a default context file template."""
        default_context = {
            'company_terms': [
                'your-company-name',
                'company-abbreviation'
            ],
            'core_industries': [
                'e-commerce',
                'online retail',
                'digital marketplace'
            ],
            'primary_markets': [
                'european union',
                'eu',
                'germany',
                'france'
            ],
            'strategic_themes': [
                'digital transformation',
                'customer experience',
                'regulatory compliance',
                'data privacy'
            ],
            'topic_patterns': {
                'data-protection': [
                    'gdpr',
                    'data privacy',
                    'personal information',
                    'data protection'
                ],
                'compliance': [
                    'regulatory compliance',
                    'legal requirement',
                    'enforcement action',
                    'compliance obligation'
                ]
            },
            'direct_impact_keywords': [
                'must comply',
                'required to',
                'obligation',
                'penalty',
                'enforcement'
            ],
            'secondary_markets': [
                'uk',
                'switzerland',
                'austria',
                'netherlands'
            ],
            'exclusion_terms': [
                'unrelated-term-1',
                'unrelated-term-2'
            ]
        }
        
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        
        with open(output_path, 'w', encoding='utf-8') as file:
            yaml.dump(default_context, file, default_flow_style=False, indent=2)
        
        logger.info("Default context file created", output_path=output_path)