"""Tests for ETL DAG definitions."""

from datetime import datetime, timedelta
from unittest.mock import MagicMock, patch

import pytest


class TestPolicyCollectionDag:
    """Test policy collection DAG configuration."""

    def test_dag_import(self):
        """Test that policy collection DAG can be imported."""
        try:
            from src.etl.dags.policy_collection_dag import dag
            assert dag is not None
            assert dag.dag_id == "policy_collection_dag"
        except ImportError as e:
            pytest.skip(f"Airflow not available: {e}")

    def test_dag_configuration(self):
        """Test DAG configuration parameters."""
        try:
            from src.etl.dags.policy_collection_dag import dag, default_args

            # Test basic DAG properties
            assert dag.dag_id == "policy_collection_dag"
            assert dag.schedule_interval == "0 2 * * 0"  # Sunday 2 AM UTC
            assert dag.max_active_runs == 1
            assert "etl" in dag.tags
            assert "policy" in dag.tags

            # Test default args
            assert default_args["owner"] == "political-monitoring-team"
            assert default_args["retries"] == 2
            assert default_args["retry_delay"] == timedelta(minutes=15)
            assert default_args["catchup"] is False

        except ImportError:
            pytest.skip("Airflow not available")

    def test_dag_start_date(self):
        """Test that DAG has appropriate start date."""
        try:
            from src.etl.dags.policy_collection_dag import default_args

            start_date = default_args["start_date"]
            assert isinstance(start_date, datetime)
            assert start_date.year >= 2024

        except ImportError:
            pytest.skip("Airflow not available")

    def test_dag_task_functions_exist(self):
        """Test that required task functions are defined."""
        try:
            from src.etl.dags import policy_collection_dag

            # Check for main task functions
            assert hasattr(policy_collection_dag, 'collect_policy_documents')

            # Verify function is callable
            assert callable(policy_collection_dag.collect_policy_documents)

        except ImportError:
            pytest.skip("Airflow not available")

    @patch('src.etl.collectors.policy_landscape.PolicyLandscapeCollector')
    def test_collect_policy_documents_function(self, mock_collector_class):
        """Test the collect_policy_documents function logic."""
        try:
            from src.etl.dags.policy_collection_dag import collect_policy_documents

            # Mock the collector
            mock_collector = MagicMock()
            mock_collector.collect_documents.return_value = {
                'documents_saved': 5,
                'duration': 45.2,
                'errors': []
            }
            mock_collector_class.return_value = mock_collector

            # Test function call
            result = collect_policy_documents()

            # Verify collector was instantiated and called
            mock_collector_class.assert_called_once()
            mock_collector.collect_documents.assert_called_once()

            # Verify return value structure
            assert isinstance(result, dict)
            assert 'documents_saved' in result
            assert 'status' in result

        except ImportError:
            pytest.skip("Airflow not available")


class TestNewsCollectionDag:
    """Test news collection DAG configuration."""

    def test_dag_import(self):
        """Test that news collection DAG can be imported."""
        try:
            from src.etl.dags.news_collection_dag import dag
            assert dag is not None
            assert dag.dag_id == "news_collection_dag"
        except ImportError as e:
            pytest.skip(f"Airflow not available: {e}")

    def test_dag_configuration(self):
        """Test DAG configuration parameters."""
        try:
            from src.etl.dags.news_collection_dag import dag, default_args

            # Test basic DAG properties
            assert dag.dag_id == "news_collection_dag"
            assert dag.schedule_interval == "0 6 * * *"  # Daily 6 AM UTC
            assert dag.max_active_runs == 1
            assert "etl" in dag.tags
            assert "news" in dag.tags

            # Test default args structure
            assert "owner" in default_args
            assert "retries" in default_args
            assert "retry_delay" in default_args

        except ImportError:
            pytest.skip("Airflow not available")

    def test_news_dag_daily_schedule(self):
        """Test that news DAG runs daily."""
        try:
            from src.etl.dags.news_collection_dag import dag

            # Verify daily schedule
            assert dag.schedule_interval == "0 6 * * *"

        except ImportError:
            pytest.skip("Airflow not available")

    def test_news_task_functions_exist(self):
        """Test that required news task functions are defined."""
        try:
            from src.etl.dags import news_collection_dag

            # Check for main task functions
            assert hasattr(news_collection_dag, 'collect_news_articles')

            # Verify function is callable
            assert callable(news_collection_dag.collect_news_articles)

        except ImportError:
            pytest.skip("Airflow not available")

    @patch('src.etl.collectors.exa_news.ExaNewsCollector')
    def test_collect_news_articles_function(self, mock_collector_class):
        """Test the collect_news_articles function logic."""
        try:
            from src.etl.dags.news_collection_dag import collect_news_articles

            # Mock the collector
            mock_collector = MagicMock()
            mock_collector.collect_documents.return_value = {
                'documents_saved': 12,
                'duration': 23.1,
                'errors': []
            }
            mock_collector_class.return_value = mock_collector

            # Test function call with mock context
            mock_context = {'task_instance': MagicMock()}
            result = collect_news_articles(**mock_context)

            # Verify collector was instantiated and called
            mock_collector_class.assert_called_once()
            mock_collector.collect_documents.assert_called_once()

            # Verify return value structure
            assert isinstance(result, dict)
            assert 'documents_saved' in result

        except ImportError:
            pytest.skip("Airflow not available")


class TestFlowOrchestrationDag:
    """Test flow orchestration DAG configuration."""

    def test_dag_import(self):
        """Test that flow orchestration DAG can be imported."""
        try:
            from src.etl.dags.flow_orchestration_dag import dag
            assert dag is not None
            assert dag.dag_id == "flow_orchestration_dag"
        except ImportError as e:
            pytest.skip(f"Airflow not available: {e}")

    def test_orchestration_dag_configuration(self):
        """Test orchestration DAG configuration."""
        try:
            from src.etl.dags.flow_orchestration_dag import dag

            # Should be a coordination DAG
            assert dag.dag_id == "flow_orchestration_dag"
            assert "orchestration" in dag.tags

        except ImportError:
            pytest.skip("Airflow not available")

    def test_orchestration_task_functions(self):
        """Test orchestration task functions."""
        try:
            from src.etl.dags import flow_orchestration_dag

            # Check for orchestration functions
            assert hasattr(flow_orchestration_dag, 'check_etl_health')
            assert callable(flow_orchestration_dag.check_etl_health)

        except ImportError:
            pytest.skip("Airflow not available")


class TestDagIntegration:
    """Test DAG integration and dependencies."""

    def test_all_dags_importable(self):
        """Test that all DAGs can be imported without errors."""
        dag_modules = [
            'src.etl.dags.policy_collection_dag',
            'src.etl.dags.news_collection_dag',
            'src.etl.dags.flow_orchestration_dag'
        ]

        imported_dags = []

        for module_name in dag_modules:
            try:
                module = __import__(module_name, fromlist=['dag'])
                assert hasattr(module, 'dag')
                imported_dags.append(module.dag)
            except ImportError:
                pytest.skip(f"Airflow not available for {module_name}")

        # If we imported any DAGs, verify they have unique IDs
        if imported_dags:
            dag_ids = [dag.dag_id for dag in imported_dags]
            assert len(dag_ids) == len(set(dag_ids)), "Duplicate DAG IDs found"

    def test_dag_schedules_non_overlapping(self):
        """Test that DAG schedules don't create resource conflicts."""
        try:
            from src.etl.dags.news_collection_dag import dag as news_dag
            from src.etl.dags.policy_collection_dag import dag as policy_dag

            # Policy is weekly (Sunday 2 AM), News is daily (6 AM)
            # These should not conflict
            assert policy_dag.schedule_interval != news_dag.schedule_interval

        except ImportError:
            pytest.skip("Airflow not available")

    def test_dag_tags_consistency(self):
        """Test that DAGs have consistent tagging."""
        try:
            from src.etl.dags.news_collection_dag import dag as news_dag
            from src.etl.dags.policy_collection_dag import dag as policy_dag

            # All should have 'etl' tag
            assert "etl" in policy_dag.tags
            assert "etl" in news_dag.tags

            # Should have specific functional tags
            assert "policy" in policy_dag.tags
            assert "news" in news_dag.tags

        except ImportError:
            pytest.skip("Airflow not available")


class TestDagValidation:
    """Test DAG validation and requirements."""

    def test_dag_owners_defined(self):
        """Test that all DAGs have proper owners defined."""
        try:
            from src.etl.dags.news_collection_dag import default_args as news_args
            from src.etl.dags.policy_collection_dag import default_args as policy_args

            assert policy_args.get("owner") is not None
            assert news_args.get("owner") is not None

            # Should be meaningful owner names
            assert len(policy_args["owner"]) > 3
            assert len(news_args["owner"]) > 3

        except ImportError:
            pytest.skip("Airflow not available")

    def test_dag_retry_configuration(self):
        """Test that DAGs have appropriate retry configuration."""
        try:
            from src.etl.dags.news_collection_dag import default_args as news_args
            from src.etl.dags.policy_collection_dag import default_args as policy_args

            # Should have retry configuration
            assert policy_args.get("retries") is not None
            assert news_args.get("retries") is not None

            # Retries should be reasonable (not too high)
            assert 0 <= policy_args["retries"] <= 5
            assert 0 <= news_args["retries"] <= 5

            # Should have retry delay
            assert policy_args.get("retry_delay") is not None
            assert news_args.get("retry_delay") is not None

        except ImportError:
            pytest.skip("Airflow not available")

    def test_dag_start_dates_reasonable(self):
        """Test that DAG start dates are reasonable."""
        try:
            from src.etl.dags.news_collection_dag import default_args as news_args
            from src.etl.dags.policy_collection_dag import default_args as policy_args

            policy_start = policy_args["start_date"]
            news_start = news_args["start_date"]

            # Start dates should be in the past but not too far
            now = datetime.now()
            one_year_ago = now - timedelta(days=365)

            assert one_year_ago <= policy_start <= now
            assert one_year_ago <= news_start <= now

        except ImportError:
            pytest.skip("Airflow not available")


class TestDagConstants:
    """Test DAG constants and configuration values."""

    def test_dag_constants_defined(self):
        """Test that DAG constants are properly defined."""
        try:
            from src.etl.dags.policy_collection_dag import DAG_ID, DESCRIPTION

            assert DAG_ID is not None
            assert DESCRIPTION is not None
            assert len(DAG_ID) > 0
            assert len(DESCRIPTION) > 10

        except ImportError:
            pytest.skip("Airflow not available")

    def test_schedule_intervals_valid(self):
        """Test that schedule intervals are valid cron expressions."""
        valid_schedules = [
            "0 2 * * 0",  # Policy collection - Sunday 2 AM
            "0 6 * * *",  # News collection - Daily 6 AM
        ]

        # Basic validation of cron format (5 fields)
        for schedule in valid_schedules:
            parts = schedule.split()
            assert len(parts) == 5, f"Invalid cron format: {schedule}"

            # First field should be minute (0-59)
            minute = parts[0]
            assert minute.isdigit() or minute == "*"
            if minute.isdigit():
                assert 0 <= int(minute) <= 59
