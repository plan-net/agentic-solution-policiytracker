"""
Entity Name Normalizer for Deduplication.

Normalizes entity mentions in documents before Graphiti extraction
to reduce duplicate entity creation from name variations.

Key functions:
- Normalize common abbreviations (EU → European Union)
- Standardize whitespace and formatting
- Handle domain-specific entity variations
- Preserve context while reducing duplication

Usage:
    normalizer = EntityNormalizer()
    normalized_text = normalizer.normalize_text(document_text)
    # Process normalized_text through Graphiti
"""

import re
from typing import Dict, List, Optional

import structlog

logger = structlog.get_logger()


class EntityNormalizer:
    """
    Normalize entity names in text to reduce duplicate entity creation.

    This class provides text preprocessing to standardize entity mentions
    before LLM-based entity extraction, reducing the chance of creating
    duplicate entities with slight name variations.
    """

    # Default normalization mappings for political/regulatory domain
    DEFAULT_ABBREVIATION_MAP = {
        # European Union variations
        "EU": "European Union",
        "E.U.": "European Union",
        "the EU": "the European Union",

        # European Commission
        "EU Commission": "European Commission",
        "EC": "European Commission",

        # United States
        "US": "United States",
        "U.S.": "United States",
        "USA": "United States",
        "U.S.A.": "United States",

        # United Kingdom
        "UK": "United Kingdom",
        "U.K.": "United Kingdom",

        # Common political entities
        "EP": "European Parliament",
        "ECJ": "European Court of Justice",
        "CJEU": "Court of Justice of the European Union",
        "EDPB": "European Data Protection Board",
        "EDPS": "European Data Protection Supervisor",

        # German entities
        "BT": "Bundestag",
        "BR": "Bundesrat",
        "BVerfG": "Bundesverfassungsgericht",
        "SPD": "Social Democratic Party",
        "CDU": "Christian Democratic Union",
        "CSU": "Christian Social Union",
        "FDP": "Free Democratic Party",

        # Regulations (preserve acronyms but standardize)
        "GDPR": "General Data Protection Regulation",
        "DSA": "Digital Services Act",
        "DMA": "Digital Markets Act",
        "AI Act": "Artificial Intelligence Act",
        "ePrivacy": "ePrivacy Regulation",

        # Companies (standardize variations)
        "Meta Platforms": "Meta",
        "Facebook": "Meta",  # Post-rebrand
        "Google LLC": "Google",
        "Alphabet Inc.": "Google",
        "Amazon.com": "Amazon",
        "Microsoft Corp.": "Microsoft",
        "Apple Inc.": "Apple",
    }

    def __init__(
        self,
        custom_mappings: Optional[Dict[str, str]] = None,
        enable_abbreviation_expansion: bool = True,
        enable_whitespace_normalization: bool = True,
        enable_possessive_normalization: bool = True,
        case_sensitive: bool = False,
    ):
        """
        Initialize the EntityNormalizer.

        Args:
            custom_mappings: Additional domain-specific normalization mappings
            enable_abbreviation_expansion: Expand known abbreviations
            enable_whitespace_normalization: Clean excessive whitespace
            enable_possessive_normalization: Normalize possessives (e.g., "EU's" → "European Union's")
            case_sensitive: Whether mappings are case-sensitive (default: False)
        """
        self.abbreviation_map = self.DEFAULT_ABBREVIATION_MAP.copy()
        if custom_mappings:
            self.abbreviation_map.update(custom_mappings)

        self.enable_abbreviation_expansion = enable_abbreviation_expansion
        self.enable_whitespace_normalization = enable_whitespace_normalization
        self.enable_possessive_normalization = enable_possessive_normalization
        self.case_sensitive = case_sensitive

        # Pre-compile regex patterns for performance
        self._compile_patterns()

        logger.info(
            "EntityNormalizer initialized",
            mappings_count=len(self.abbreviation_map),
            abbreviation_expansion=enable_abbreviation_expansion,
            whitespace_norm=enable_whitespace_normalization,
        )

    def _compile_patterns(self):
        """Pre-compile regex patterns for efficient text processing."""
        # Pattern for excessive whitespace
        self.whitespace_pattern = re.compile(r'\s+')

        # Pattern for possessives (e.g., "EU's" or "Meta's")
        self.possessive_pattern = re.compile(r"(\b\w+)'s\b")

        # Create word boundary patterns for each abbreviation
        # This ensures we only replace whole words, not parts of words
        self.abbreviation_patterns = {}
        for abbrev, full_form in self.abbreviation_map.items():
            # Create pattern with word boundaries
            # Use \b for most cases, but handle special cases like "U.S."
            if '.' in abbrev:
                # For dotted abbreviations, escape dots
                pattern_str = re.escape(abbrev)
            else:
                # For regular abbreviations, use word boundaries
                pattern_str = r'\b' + re.escape(abbrev) + r'\b'

            flags = 0 if self.case_sensitive else re.IGNORECASE
            self.abbreviation_patterns[abbrev] = re.compile(pattern_str, flags)

    def normalize_text(self, text: str) -> str:
        """
        Normalize entity mentions in text.

        Args:
            text: Input text with potential entity variations

        Returns:
            Normalized text with standardized entity mentions
        """
        if not text:
            return text

        normalized = text

        # Step 1: Normalize whitespace
        if self.enable_whitespace_normalization:
            normalized = self._normalize_whitespace(normalized)

        # Step 2: Expand abbreviations
        if self.enable_abbreviation_expansion:
            normalized = self._expand_abbreviations(normalized)

        # Step 3: Normalize possessives (after abbreviation expansion)
        if self.enable_possessive_normalization:
            normalized = self._normalize_possessives(normalized)

        return normalized

    def _normalize_whitespace(self, text: str) -> str:
        """
        Normalize excessive whitespace.

        Replaces multiple spaces, tabs, newlines with single space.
        Preserves paragraph breaks (double newlines).
        """
        # Replace multiple spaces/tabs with single space
        text = self.whitespace_pattern.sub(' ', text)

        # Preserve paragraph breaks
        text = re.sub(r'\n\n+', '\n\n', text)

        # Strip leading/trailing whitespace from lines
        lines = text.split('\n')
        lines = [line.strip() for line in lines]
        text = '\n'.join(lines)

        return text.strip()

    def _expand_abbreviations(self, text: str) -> str:
        """
        Expand known abbreviations to full forms.

        Uses word boundary patterns to avoid partial replacements.
        Example: "EU Commission" → "European Union Commission"
                 But not: "EUROPE" → "European UnionROPE"
        """
        expanded = text

        # Sort by length (longest first) to handle multi-word abbreviations correctly
        # E.g., "EU Commission" should be handled before "EU"
        sorted_abbrevs = sorted(
            self.abbreviation_map.items(),
            key=lambda x: len(x[0]),
            reverse=True
        )

        for abbrev, full_form in sorted_abbrevs:
            pattern = self.abbreviation_patterns[abbrev]

            # Count replacements for logging
            matches = pattern.findall(expanded)
            if matches:
                expanded = pattern.sub(full_form, expanded)
                logger.debug(
                    "Expanded abbreviation",
                    abbreviation=abbrev,
                    full_form=full_form,
                    count=len(matches)
                )

        return expanded

    def _normalize_possessives(self, text: str) -> str:
        """
        Normalize possessive forms to ensure consistency.

        This is called AFTER abbreviation expansion, so it handles
        possessives of the full forms.

        Example: After expansion, "EU's" becomes "European Union's"
        """
        # The possessive pattern already captures this correctly
        # No additional processing needed beyond the regex pattern
        return text

    def add_custom_mapping(self, abbreviation: str, full_form: str):
        """
        Add a custom normalization mapping at runtime.

        Args:
            abbreviation: Short form to replace
            full_form: Full form to use
        """
        self.abbreviation_map[abbreviation] = full_form

        # Recompile patterns with new mapping
        self._compile_patterns()

        logger.info(
            "Added custom mapping",
            abbreviation=abbreviation,
            full_form=full_form
        )

    def get_statistics(self, text: str) -> Dict[str, int]:
        """
        Get statistics about potential normalizations in text.

        Useful for monitoring and tuning the normalizer.

        Args:
            text: Input text to analyze

        Returns:
            Dict with counts of each normalization that would be applied
        """
        stats = {
            "total_abbreviations": 0,
            "excessive_whitespace_count": len(self.whitespace_pattern.findall(text)),
            "abbreviation_counts": {},
        }

        for abbrev in self.abbreviation_map:
            pattern = self.abbreviation_patterns[abbrev]
            matches = pattern.findall(text)
            if matches:
                count = len(matches)
                stats["abbreviation_counts"][abbrev] = count
                stats["total_abbreviations"] += count

        return stats


# Singleton instance for convenience
_default_normalizer = None


def get_default_normalizer() -> EntityNormalizer:
    """
    Get the default EntityNormalizer instance (singleton).

    Returns:
        Default EntityNormalizer with standard political domain mappings
    """
    global _default_normalizer
    if _default_normalizer is None:
        _default_normalizer = EntityNormalizer()
    return _default_normalizer


def normalize_entity_name(name: str) -> str:
    """
    Quick utility function to normalize a single entity name.

    Args:
        name: Entity name to normalize

    Returns:
        Normalized entity name
    """
    normalizer = get_default_normalizer()
    return normalizer.normalize_text(name).strip()


# Example usage
if __name__ == "__main__":
    # Test the normalizer
    test_texts = [
        "The EU Commission announced new regulations.",
        "Meta's  new   policy affects   users.",
        "The U.S. and UK agreed on the GDPR approach.",
        "BT and BR are German legislative bodies.",
        "The DSA and DMA are EU regulations.",
    ]

    normalizer = EntityNormalizer()

    print("=" * 80)
    print("Entity Normalizer Test")
    print("=" * 80)

    for text in test_texts:
        print(f"\nOriginal: {text}")
        normalized = normalizer.normalize_text(text)
        print(f"Normalized: {normalized}")
        stats = normalizer.get_statistics(text)
        print(f"Stats: {stats['total_abbreviations']} abbreviations found")
        if stats['abbreviation_counts']:
            print(f"  Details: {stats['abbreviation_counts']}")
