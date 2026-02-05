"""Unit tests for schema_helpers.py

Tests extraction functions for both nested and flat schema formats.
"""

import pytest

from src.etl.utils.schema_helpers import (
    extract_company_terms,
    extract_exclusion_terms,
    extract_industries,
    extract_legislative_terms,
    extract_markets,
    extract_regulatory_actors,
    validate_required_fields,
)


class TestExtractIndustries:
    """Test extract_industries function."""

    def test_nested_format(self):
        """Test extraction from nested format."""
        config = {
            "core_industries": {
                "primary": "E-commerce / Online Retail",
                "secondary": ["fashion retail", "marketplace operator", "digital platform"],
            }
        }
        result = extract_industries(config)
        assert result == [
            "E-commerce / Online Retail",
            "fashion retail",
            "marketplace operator",
            "digital platform",
        ]

    def test_nested_format_no_primary(self):
        """Test nested format with no primary industry."""
        config = {
            "core_industries": {
                "primary": "",
                "secondary": ["fashion retail", "marketplace operator"],
            }
        }
        result = extract_industries(config)
        assert result == ["fashion retail", "marketplace operator"]

    def test_flat_format(self):
        """Test extraction from flat list format."""
        config = {
            "core_industries": [
                "E-commerce",
                "fashion retail",
                "marketplace operator",
            ]
        }
        result = extract_industries(config)
        assert result == ["E-commerce", "fashion retail", "marketplace operator"]

    def test_empty_config(self):
        """Test with empty config."""
        config = {}
        result = extract_industries(config)
        assert result == []

    def test_invalid_type(self):
        """Test with invalid type (string instead of list/dict)."""
        config = {"core_industries": "e-commerce"}
        result = extract_industries(config)
        assert result == []


class TestExtractMarkets:
    """Test extract_markets function."""

    def test_nested_format(self):
        """Test extraction from nested format."""
        config = {
            "markets": {
                "primary": ["germany", "european union"],
                "secondary": ["poland", "france", "italy"],
            }
        }
        primary, secondary = extract_markets(config)
        assert primary == ["germany", "european union"]
        assert secondary == ["poland", "france", "italy"]

    def test_flat_format(self):
        """Test extraction from flat format."""
        config = {
            "primary_markets": ["germany", "european union"],
            "secondary_markets": ["poland", "france"],
        }
        primary, secondary = extract_markets(config)
        assert primary == ["germany", "european union"]
        assert secondary == ["poland", "france"]

    def test_mixed_format_prefers_nested(self):
        """Test that nested format is preferred when both exist."""
        config = {
            "markets": {
                "primary": ["nested_primary"],
                "secondary": ["nested_secondary"],
            },
            "primary_markets": ["flat_primary"],
            "secondary_markets": ["flat_secondary"],
        }
        primary, secondary = extract_markets(config)
        assert primary == ["nested_primary"]
        assert secondary == ["nested_secondary"]

    def test_empty_config(self):
        """Test with empty config."""
        config = {}
        primary, secondary = extract_markets(config)
        assert primary == []
        assert secondary == []


class TestExtractCompanyTerms:
    """Test extract_company_terms function."""

    def test_company_terms_list(self):
        """Test extraction from company_terms list."""
        config = {
            "company_terms": ["Zalando", "Zalando SE", "ASOS", "About You"]
        }
        result = extract_company_terms(config)
        assert result == ["Zalando", "Zalando SE", "ASOS", "About You"]

    def test_client_name_fallback(self):
        """Test fallback to client_name string."""
        config = {"client_name": "zalando"}
        result = extract_company_terms(config)
        assert result == ["zalando"]

    def test_company_terms_preferred_over_client_name(self):
        """Test that company_terms is preferred when both exist."""
        config = {
            "company_terms": ["Zalando", "Zalando SE"],
            "client_name": "zalando",
        }
        result = extract_company_terms(config)
        assert result == ["Zalando", "Zalando SE"]

    def test_empty_config(self):
        """Test with empty config."""
        config = {}
        result = extract_company_terms(config)
        assert result == []


class TestExtractExclusionTerms:
    """Test extract_exclusion_terms function."""

    def test_flat_format(self):
        """Test extraction from flat format."""
        config = {
            "exclusion_terms": ["sports", "automotive", "real estate"]
        }
        result = extract_exclusion_terms(config)
        assert result == ["sports", "automotive", "real estate"]

    def test_nested_format(self):
        """Test extraction from nested format."""
        config = {
            "exclusions": {
                "industries": ["sports", "automotive"]
            }
        }
        result = extract_exclusion_terms(config)
        assert result == ["sports", "automotive"]

    def test_flat_format_preferred(self):
        """Test that flat format is preferred when both exist."""
        config = {
            "exclusion_terms": ["flat_term1", "flat_term2"],
            "exclusions": {"industries": ["nested_term1"]},
        }
        result = extract_exclusion_terms(config)
        assert result == ["flat_term1", "flat_term2"]

    def test_empty_config(self):
        """Test with empty config."""
        config = {}
        result = extract_exclusion_terms(config)
        assert result == []


class TestExtractRegulatoryActors:
    """Test extract_regulatory_actors function."""

    def test_extract_all_actors(self):
        """Test extraction of all actors."""
        config = {
            "regulatory_actors": {
                "german_federal": ["Bundestag", "BMWK"],
                "eu_institutions": ["European Commission", "EDPB"]
            }
        }
        result = extract_regulatory_actors(config)
        assert result == ["Bundestag", "BMWK", "European Commission", "EDPB"]

    def test_extract_german_actors_only(self):
        """Test extraction with region filter."""
        config = {
            "regulatory_actors": {
                "german_federal": ["Bundestag", "BMWK"],
                "eu_institutions": ["European Commission"]
            }
        }
        result = extract_regulatory_actors(config, region="german_federal")
        assert result == ["Bundestag", "BMWK"]

    def test_extract_eu_actors_only(self):
        """Test extraction with EU region filter."""
        config = {
            "regulatory_actors": {
                "german_federal": ["Bundestag"],
                "eu_institutions": ["European Commission", "EDPB"]
            }
        }
        result = extract_regulatory_actors(config, region="eu_institutions")
        assert result == ["European Commission", "EDPB"]

    def test_empty_config(self):
        """Test with empty config."""
        config = {}
        result = extract_regulatory_actors(config)
        assert result == []

    def test_invalid_type(self):
        """Test with invalid type (string instead of dict)."""
        config = {"regulatory_actors": "Bundestag"}
        result = extract_regulatory_actors(config)
        assert result == []


class TestExtractLegislativeTerms:
    """Test extract_legislative_terms function."""

    def test_extract_all_terms(self):
        """Test extraction of all terms."""
        config = {
            "legislative_terms": {
                "german": ["Gesetzentwurf", "Verordnung"],
                "english": ["draft legislation", "regulation"]
            }
        }
        result = extract_legislative_terms(config)
        assert result == ["Gesetzentwurf", "Verordnung", "draft legislation", "regulation"]

    def test_extract_german_terms_only(self):
        """Test extraction with language filter."""
        config = {
            "legislative_terms": {
                "german": ["Gesetzentwurf"],
                "english": ["draft legislation"]
            }
        }
        result = extract_legislative_terms(config, language="german")
        assert result == ["Gesetzentwurf"]

    def test_extract_english_terms_only(self):
        """Test extraction with English language filter."""
        config = {
            "legislative_terms": {
                "german": ["Gesetzentwurf"],
                "english": ["draft legislation", "regulation"]
            }
        }
        result = extract_legislative_terms(config, language="english")
        assert result == ["draft legislation", "regulation"]

    def test_empty_config(self):
        """Test with empty config."""
        config = {}
        result = extract_legislative_terms(config)
        assert result == []

    def test_invalid_type(self):
        """Test with invalid type (string instead of dict)."""
        config = {"legislative_terms": "Gesetzentwurf"}
        result = extract_legislative_terms(config)
        assert result == []


class TestValidateRequiredFields:
    """Test validate_required_fields function."""

    def test_valid_nested_config(self):
        """Test with all required fields in nested format."""
        config = {
            "company_terms": ["Zalando"],
            "core_industries": {
                "primary": "E-commerce",
                "secondary": ["fashion"],
            },
            "markets": {
                "primary": ["germany"],
                "secondary": ["uk"],
            },
            "strategic_themes": ["digital transformation"],
            "direct_impact_keywords": ["must comply"],
            "topic_patterns": {"data-protection": ["gdpr"]},
            "exclusion_terms": ["sports"],
        }
        is_valid, missing = validate_required_fields(config)
        assert is_valid is True
        assert missing == []

    def test_valid_flat_config(self):
        """Test with all required fields in flat format."""
        config = {
            "client_name": "zalando",
            "core_industries": ["E-commerce", "fashion"],
            "primary_markets": ["germany"],
            "secondary_markets": ["uk"],
            "strategic_themes": ["digital transformation"],
            "direct_impact_keywords": ["must comply"],
            "topic_patterns": {"data-protection": ["gdpr"]},
            "exclusion_terms": ["sports"],
        }
        is_valid, missing = validate_required_fields(config)
        assert is_valid is True
        assert missing == []

    def test_missing_company_terms(self):
        """Test with missing company_terms."""
        config = {
            "core_industries": ["E-commerce"],
            "primary_markets": ["germany"],
            "secondary_markets": ["uk"],
            "strategic_themes": ["digital transformation"],
            "direct_impact_keywords": ["must comply"],
            "topic_patterns": {"data-protection": ["gdpr"]},
            "exclusion_terms": ["sports"],
        }
        is_valid, missing = validate_required_fields(config)
        assert is_valid is False
        assert "company_terms or client_name" in missing

    def test_missing_multiple_fields(self):
        """Test with multiple missing fields."""
        config = {
            "client_name": "zalando",
            "core_industries": ["E-commerce"],
        }
        is_valid, missing = validate_required_fields(config)
        assert is_valid is False
        assert len(missing) > 0
        assert "primary_markets or markets.primary" in missing
        assert "secondary_markets or markets.secondary" in missing
        assert "strategic_themes" in missing
        assert "direct_impact_keywords" in missing
        assert "topic_patterns" in missing


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
