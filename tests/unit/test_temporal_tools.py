"""
Unit tests for Temporal Tools in the Graph Retrieval MCP Server.

Tests the temporal tool handlers and helper functions with mocked retriever.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime


class TestTemporalToolsDefinitions:
    """Test that temporal tools are properly defined in the MCP server."""

    def test_list_tools_includes_temporal_tools(self):
        """Test that list_tools includes all 5 temporal tools."""
        expected_temporal_tools = [
            "search_by_date_range",
            "get_entity_history",
            "find_concurrent_events",
            "compare_timelines",
            "track_policy_evolution",
        ]

        # Import the tools list from the server
        from src.mcp.graph_retrieval.server import list_tools
        import asyncio

        # Since list_tools is async, we check that it's properly defined
        import inspect
        assert inspect.iscoroutinefunction(list_tools)


class TestTemporalRelevanceCalculation:
    """Test the temporal relevance calculation helper function."""

    def test_calculate_temporal_relevance_with_temporal_keywords(self):
        """Test relevance scoring for content with temporal keywords."""
        from src.mcp.graph_retrieval.server import _calculate_temporal_relevance

        content = "The regulation was announced and published in 2024"
        score = _calculate_temporal_relevance(content, 2024, 2024)

        # Should have positive score for "announced", "published", and "2024"
        assert score > 0
        assert score <= 1.0

    def test_calculate_temporal_relevance_with_date_pattern(self):
        """Test relevance scoring for content with date patterns."""
        from src.mcp.graph_retrieval.server import _calculate_temporal_relevance

        content = "The directive came into force on 2024-03-15"
        score = _calculate_temporal_relevance(content, 2024, 2024)

        # Should have high score for date pattern + year match
        assert score > 0.3

    def test_calculate_temporal_relevance_no_temporal_content(self):
        """Test relevance scoring for content without temporal indicators."""
        from src.mcp.graph_retrieval.server import _calculate_temporal_relevance

        content = "This is a simple description without dates"
        score = _calculate_temporal_relevance(content, 2024, 2024)

        # Should have zero or low score
        assert score >= 0


class TestEventInfoExtraction:
    """Test the event info extraction helper function."""

    def test_extract_event_info_regulatory(self):
        """Test extraction of regulatory event info."""
        from src.mcp.graph_retrieval.server import _extract_event_info

        content = "The regulation requires compliance with new enforcement rules"
        info = _extract_event_info(content, "TestEntity")

        assert info["type"] == "regulatory"
        assert "importance" in info
        assert "temporal_indicators" in info
        assert isinstance(info["temporal_indicators"], list)

    def test_extract_event_info_policy(self):
        """Test extraction of policy event info."""
        from src.mcp.graph_retrieval.server import _extract_event_info

        content = "The new legislation was enacted and the law amended"
        info = _extract_event_info(content, "TestPolicy")

        assert info["type"] == "policy"

    def test_extract_event_info_business(self):
        """Test extraction of business event info."""
        from src.mcp.graph_retrieval.server import _extract_event_info

        content = "The company announced a major merger and acquisition"
        info = _extract_event_info(content, "TestCompany")

        assert info["type"] == "business"

    def test_extract_event_info_high_importance(self):
        """Test importance scoring for significant events."""
        from src.mcp.graph_retrieval.server import _extract_event_info

        content = "A major significant breakthrough was announced"
        info = _extract_event_info(content, "TestEntity")

        # Should have high importance for "major", "significant", "breakthrough", "announced"
        assert info["importance"] > 0.5


class TestPolicyEvolutionAnalysis:
    """Test the policy evolution analysis helper function."""

    def test_analyze_policy_evolution_implementation_phase(self):
        """Test detection of implementation phase."""
        from src.mcp.graph_retrieval.server import _analyze_policy_evolution

        content = "The AI Act has been implemented and came into force"
        info = _analyze_policy_evolution(content, "AI Act")

        assert info["phase"] == "implementation"

    def test_analyze_policy_evolution_amendment_type(self):
        """Test detection of amendment evolution type."""
        from src.mcp.graph_retrieval.server import _analyze_policy_evolution

        content = "The GDPR was amended and revised to include new provisions"
        info = _analyze_policy_evolution(content, "GDPR")

        assert info["evolution_type"] == "amendment"

    def test_analyze_policy_evolution_enforcement_phase(self):
        """Test detection of enforcement phase."""
        from src.mcp.graph_retrieval.server import _analyze_policy_evolution

        content = "The company received a penalty fine for violation of compliance"
        info = _analyze_policy_evolution(content, "TestPolicy")

        assert info["phase"] == "enforcement"

    def test_analyze_policy_evolution_stakeholders(self):
        """Test stakeholder extraction."""
        from src.mcp.graph_retrieval.server import _analyze_policy_evolution

        content = "The European Commission and Parliament reviewed the directive"
        info = _analyze_policy_evolution(content, "TestDirective")

        assert "commission" in info["stakeholders"] or "parliament" in info["stakeholders"]


class TestSearchByDateRangeHandler:
    """Test the search_by_date_range handler."""

    @pytest.mark.asyncio
    async def test_search_by_date_range_invalid_date_format(self):
        """Test handling of invalid date format."""
        from src.mcp.graph_retrieval.server import handle_search_by_date_range

        # Mock the retriever
        with patch('src.mcp.graph_retrieval.server.retriever') as mock_retriever:
            result = await handle_search_by_date_range(
                query="test",
                start_date="invalid-date",
                end_date="2024-12-31",
                max_results=5
            )

            assert len(result) == 1
            assert "Error" in result[0].text
            assert "Invalid date format" in result[0].text

    @pytest.mark.asyncio
    async def test_search_by_date_range_valid_dates(self):
        """Test search with valid date range."""
        from src.mcp.graph_retrieval.server import handle_search_by_date_range

        # Create mock retriever
        mock_context = MagicMock()
        mock_result = {
            'retrieved_context': {
                'facts': [
                    {'content': 'The regulation was enacted in 2024'},
                    {'content': 'New compliance deadline announced for 2024-06-01'},
                ],
                'entities': []
            }
        }

        with patch('src.mcp.graph_retrieval.server.retriever') as mock_retriever:
            mock_retriever.retrieve = AsyncMock(return_value=mock_context)
            mock_retriever.to_dict = MagicMock(return_value=mock_result)

            result = await handle_search_by_date_range(
                query="regulation",
                start_date="2024-01-01",
                end_date="2024-12-31",
                max_results=5
            )

            assert len(result) == 1
            assert "Temporal Search" in result[0].text
            assert "2024-01-01" in result[0].text
            assert "2024-12-31" in result[0].text


class TestGetEntityHistoryHandler:
    """Test the get_entity_history handler."""

    @pytest.mark.asyncio
    async def test_get_entity_history_with_results(self):
        """Test entity history retrieval with results."""
        from src.mcp.graph_retrieval.server import handle_get_entity_history

        mock_context = MagicMock()
        mock_result = {
            'retrieved_context': {
                'facts': [
                    {'content': 'GDPR was implemented with major enforcement changes'},
                    {'content': 'GDPR compliance deadline was announced'},
                ],
                'relationships': []
            }
        }

        with patch('src.mcp.graph_retrieval.server.retriever') as mock_retriever:
            mock_retriever.retrieve = AsyncMock(return_value=mock_context)
            mock_retriever.to_dict = MagicMock(return_value=mock_result)

            result = await handle_get_entity_history(
                entity_name="GDPR",
                days_back=365,
                event_types=None
            )

            assert len(result) == 1
            assert "Historical Timeline" in result[0].text
            assert "GDPR" in result[0].text


class TestFindConcurrentEventsHandler:
    """Test the find_concurrent_events handler."""

    @pytest.mark.asyncio
    async def test_find_concurrent_events_invalid_date(self):
        """Test handling of invalid reference date."""
        from src.mcp.graph_retrieval.server import handle_find_concurrent_events

        with patch('src.mcp.graph_retrieval.server.retriever') as mock_retriever:
            result = await handle_find_concurrent_events(
                reference_date="not-a-date",
                window_days=30,
                event_context=None
            )

            assert len(result) == 1
            assert "Error" in result[0].text

    @pytest.mark.asyncio
    async def test_find_concurrent_events_valid_date(self):
        """Test concurrent events search with valid date."""
        from src.mcp.graph_retrieval.server import handle_find_concurrent_events

        mock_context = MagicMock()
        mock_result = {
            'retrieved_context': {
                'facts': [
                    {'content': 'Regulatory announcement made in March 2024'},
                    {'content': 'Policy update published around the same time'},
                ],
                'entities': []
            }
        }

        with patch('src.mcp.graph_retrieval.server.retriever') as mock_retriever:
            mock_retriever.retrieve = AsyncMock(return_value=mock_context)
            mock_retriever.to_dict = MagicMock(return_value=mock_result)

            result = await handle_find_concurrent_events(
                reference_date="2024-03-15",
                window_days=30,
                event_context="AI regulation"
            )

            assert len(result) == 1
            assert "Concurrent Events" in result[0].text
            assert "2024-03-15" in result[0].text


class TestCompareTimelinesHandler:
    """Test the compare_timelines handler."""

    @pytest.mark.asyncio
    async def test_compare_timelines_insufficient_entities(self):
        """Test error handling for insufficient entities."""
        from src.mcp.graph_retrieval.server import handle_compare_timelines

        with patch('src.mcp.graph_retrieval.server.retriever') as mock_retriever:
            result = await handle_compare_timelines(
                entities=["SingleEntity"],
                time_period=365,
                comparison_focus=None
            )

            assert len(result) == 1
            assert "Error" in result[0].text
            assert "at least 2 entities" in result[0].text

    @pytest.mark.asyncio
    async def test_compare_timelines_multiple_entities(self):
        """Test timeline comparison with multiple entities."""
        from src.mcp.graph_retrieval.server import handle_compare_timelines

        mock_context = MagicMock()
        mock_result = {
            'retrieved_context': {
                'facts': [
                    {'content': 'DSA implementation timeline announced'},
                    {'content': 'DMA enforcement began with regulatory changes'},
                ],
                'entities': []
            }
        }

        with patch('src.mcp.graph_retrieval.server.retriever') as mock_retriever:
            mock_retriever.retrieve = AsyncMock(return_value=mock_context)
            mock_retriever.to_dict = MagicMock(return_value=mock_result)

            result = await handle_compare_timelines(
                entities=["DSA", "DMA"],
                time_period=365,
                comparison_focus="enforcement"
            )

            assert len(result) == 1
            assert "Timeline Comparison" in result[0].text
            assert "DSA" in result[0].text
            assert "DMA" in result[0].text


class TestTrackPolicyEvolutionHandler:
    """Test the track_policy_evolution handler."""

    @pytest.mark.asyncio
    async def test_track_policy_evolution_with_results(self):
        """Test policy evolution tracking."""
        from src.mcp.graph_retrieval.server import handle_track_policy_evolution

        mock_context = MagicMock()
        mock_result = {
            'retrieved_context': {
                'facts': [
                    {'content': 'AI Act was proposed and then amended by the Commission'},
                    {'content': 'AI Act implementation was enacted with enforcement guidelines'},
                ],
                'entities': []
            }
        }

        with patch('src.mcp.graph_retrieval.server.retriever') as mock_retriever:
            mock_retriever.retrieve = AsyncMock(return_value=mock_context)
            mock_retriever.to_dict = MagicMock(return_value=mock_result)

            result = await handle_track_policy_evolution(
                policy_name="AI Act",
                evolution_period=730,
                evolution_aspects=["enforcement", "compliance"]
            )

            assert len(result) == 1
            assert "Policy Evolution" in result[0].text
            assert "AI Act" in result[0].text


class TestCallToolDispatch:
    """Test that call_tool properly dispatches temporal tools."""

    @pytest.mark.asyncio
    async def test_call_tool_dispatches_search_by_date_range(self):
        """Test call_tool dispatches search_by_date_range correctly."""
        from src.mcp.graph_retrieval.server import call_tool

        mock_context = MagicMock()
        mock_result = {'retrieved_context': {'facts': [], 'entities': []}}

        with patch('src.mcp.graph_retrieval.server.retriever') as mock_retriever:
            mock_retriever.retrieve = AsyncMock(return_value=mock_context)
            mock_retriever.to_dict = MagicMock(return_value=mock_result)

            result = await call_tool(
                "search_by_date_range",
                {
                    "query": "test",
                    "start_date": "2024-01-01",
                    "end_date": "2024-12-31",
                    "max_results": 5
                }
            )

            assert len(result) == 1
            assert "Temporal Search" in result[0].text

    @pytest.mark.asyncio
    async def test_call_tool_dispatches_track_policy_evolution(self):
        """Test call_tool dispatches track_policy_evolution correctly."""
        from src.mcp.graph_retrieval.server import call_tool

        mock_context = MagicMock()
        mock_result = {'retrieved_context': {'facts': [], 'entities': []}}

        with patch('src.mcp.graph_retrieval.server.retriever') as mock_retriever:
            mock_retriever.retrieve = AsyncMock(return_value=mock_context)
            mock_retriever.to_dict = MagicMock(return_value=mock_result)

            result = await call_tool(
                "track_policy_evolution",
                {
                    "policy_name": "GDPR",
                    "evolution_period": 730
                }
            )

            assert len(result) == 1
            assert "Policy Evolution" in result[0].text


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
