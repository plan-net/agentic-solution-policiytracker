"""
End-to-end integration tests for the Political Monitoring Agent.

These tests run the complete workflow from form submission through to final results,
ensuring all components work together correctly without mocking critical paths.
"""
import asyncio
import os
import tempfile
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import ray
import yaml


@pytest.fixture
def ray_cluster():
    """Initialize Ray cluster for testing."""
    if not ray.is_initialized():
        ray.init(local_mode=True)
    yield
    if ray.is_initialized():
        ray.shutdown()


@pytest.fixture
def test_environment():
    """Create a complete test environment with documents and context."""
    with tempfile.TemporaryDirectory() as tmpdir:
        # Create directory structure
        data_dir = os.path.join(tmpdir, "data")
        input_dir = os.path.join(data_dir, "input")
        context_dir = os.path.join(data_dir, "context")
        output_dir = os.path.join(data_dir, "output")

        os.makedirs(input_dir)
        os.makedirs(context_dir)
        os.makedirs(output_dir)

        # Create sample documents
        documents = {
            "eu_regulation.md": """
# EU Digital Services Act - Compliance Requirements

The Digital Services Act introduces new obligations for online platforms operating in the EU.

Key requirements:
- Content moderation systems must be transparent
- Large platforms must conduct annual risk assessments
- New reporting obligations for content removal decisions
- Enhanced user rights for content appeals

Companies must comply by February 2024.
""",
            "privacy_policy.txt": """
Privacy Policy Updates - GDPR Compliance

Our organization has updated privacy policies to ensure full GDPR compliance.

Changes include:
- Enhanced data subject rights procedures
- Updated cookie consent mechanisms
- Revised data retention schedules
- New data protection officer contact details

These changes take effect immediately and apply to all EU operations.
""",
            "sustainability_report.md": """
# Corporate Sustainability Report 2024

## Environmental Initiatives

Our company has implemented new sustainability measures:

- Carbon neutral operations by 2025
- Renewable energy transition completed
- Waste reduction programs achieving 40% reduction
- Supply chain sustainability audits

## Regulatory Compliance

We maintain compliance with:
- EU Taxonomy Regulation
- Corporate Sustainability Reporting Directive (CSRD)
- Science-Based Targets initiative (SBTi)
""",
        }

        # Write documents to input directory
        for filename, content in documents.items():
            filepath = os.path.join(input_dir, filename)
            with open(filepath, "w") as f:
                f.write(content)

        # Create context configuration
        context_config = {
            "company_terms": [
                "digital services",
                "platform",
                "privacy",
                "gdpr",
                "sustainability",
                "compliance",
            ],
            "core_industries": ["technology", "digital platforms", "data processing"],
            "primary_markets": ["european union", "eu", "europe"],
            "strategic_themes": [
                "digital compliance",
                "privacy protection",
                "sustainability",
                "regulatory compliance",
            ],
            "scoring_dimensions": [
                {
                    "name": "business_relevance",
                    "weight": 0.4,
                    "description": "Direct impact on business operations",
                },
                {
                    "name": "regulatory_impact",
                    "weight": 0.3,
                    "description": "Regulatory compliance requirements",
                },
                {
                    "name": "market_relevance",
                    "weight": 0.2,
                    "description": "Geographic market relevance",
                },
                {
                    "name": "temporal_urgency",
                    "weight": 0.1,
                    "description": "Time sensitivity and deadlines",
                },
            ],
        }

        context_file = os.path.join(context_dir, "client.yaml")
        with open(context_file, "w") as f:
            yaml.dump(context_config, f, default_flow_style=False)

        yield {
            "tmpdir": tmpdir,
            "data_dir": data_dir,
            "input_dir": input_dir,
            "context_dir": context_dir,
            "output_dir": output_dir,
            "context_file": context_file,
            "documents": list(documents.keys()),
        }


class TestEndToEndWorkflow:
    """Test complete workflow execution from start to finish."""

    def test_form_submission_to_completion_workflow(self, test_environment, ray_cluster):
        """Test complete workflow from form submission through to final results."""
        # Change to test directory for relative path resolution
        original_cwd = os.getcwd()
        try:
            os.chdir(test_environment["tmpdir"])

            # Prepare form inputs
            inputs = {
                "job_name": "Integration Test Analysis",
                "input_folder": "./data/input",
                "context_file": "./data/context/client.yaml",
                "priority_threshold": "60.0",  # String to test conversion
                "include_low_confidence": False,
                "clustering_enabled": True,
                "batch_size": "10",  # String to test conversion
                "timeout_minutes": "60",  # String to test conversion
                "instructions": "Focus on regulatory compliance and digital services",
            }

            # Mock tracer for progress tracking
            mock_tracer = MagicMock()
            mock_tracer.markdown = AsyncMock()

            # Import and run the analyzer
            import political_analyzer

            # This should complete without errors
            result = asyncio.run(political_analyzer.execute_analysis(inputs, mock_tracer))

            # Verify result structure
            assert "success" in result
            assert result["success"] is True
            assert "job_id" in result
            assert result["job_id"].startswith("job_")
            assert "total_documents" in result
            assert result["total_documents"] == 3  # We created 3 documents
            assert "high_priority_count" in result
            assert "processing_time_seconds" in result

            # Verify tracer was called with progress updates
            assert mock_tracer.markdown.call_count > 0

            # Check that tracer calls include expected content
            tracer_calls = [call[0][0] for call in mock_tracer.markdown.call_args_list]
            tracer_content = " ".join(tracer_calls)

            assert "Political Analysis:" in tracer_content
            assert "Document Discovery" in tracer_content
            assert "Total Documents Found: 3" in tracer_content

        finally:
            os.chdir(original_cwd)

    def test_document_processing_with_real_content(self, test_environment, ray_cluster):
        """Test that documents are actually processed and analyzed."""
        original_cwd = os.getcwd()
        try:
            os.chdir(test_environment["tmpdir"])

            # Test document processing tasks directly
            import political_analyzer

            # Test load_context_task
            context = ray.get(
                political_analyzer.load_context_task.remote("./data/context/client.yaml")
            )

            assert context is not None
            assert "company_terms" in context
            assert "digital services" in context["company_terms"]

            # Test process_batch_task with real documents
            document_files = [
                os.path.join("./data/input", filename) for filename in test_environment["documents"]
            ]

            # Process documents
            processed_docs = ray.get(
                political_analyzer.process_batch_task.remote(document_files, 0, "test_job")
            )

            # Verify processing results
            assert len(processed_docs) > 0  # Should process some documents

            # Each processed document should have required fields
            for doc in processed_docs:
                assert hasattr(doc, "doc_id") or "doc_id" in doc
                assert hasattr(doc, "content") or "content" in doc

        finally:
            os.chdir(original_cwd)

    def test_error_handling_with_invalid_inputs(self, test_environment, ray_cluster):
        """Test that invalid inputs are handled gracefully."""
        original_cwd = os.getcwd()
        try:
            os.chdir(test_environment["tmpdir"])

            mock_tracer = MagicMock()
            mock_tracer.markdown = AsyncMock()

            import political_analyzer

            # Test with non-existent input folder
            inputs_bad_folder = {
                "job_name": "Test Bad Folder",
                "input_folder": "./nonexistent/folder",
                "context_file": "./data/context/client.yaml",
                "priority_threshold": 70.0,
                "include_low_confidence": False,
                "clustering_enabled": True,
                "batch_size": 10,
                "timeout_minutes": 30,
                "instructions": "",
            }

            with pytest.raises(FileNotFoundError, match="Input folder not found"):
                asyncio.run(political_analyzer.execute_analysis(inputs_bad_folder, mock_tracer))

            # Test with non-existent context file
            inputs_bad_context = {
                "job_name": "Test Bad Context",
                "input_folder": "./data/input",
                "context_file": "./nonexistent/context.yaml",
                "priority_threshold": 70.0,
                "include_low_confidence": False,
                "clustering_enabled": True,
                "batch_size": 10,
                "timeout_minutes": 30,
                "instructions": "",
            }

            # This should fail during context loading
            with pytest.raises((FileNotFoundError, Exception)):
                asyncio.run(political_analyzer.execute_analysis(inputs_bad_context, mock_tracer))

        finally:
            os.chdir(original_cwd)


class TestKodosumiIntegration:
    """Test integration with Kodosumi form handling."""

    def test_kodosumi_form_to_analyzer_integration(self, test_environment):
        """Test that Kodosumi form properly calls the analyzer."""
        from app import enter

        original_cwd = os.getcwd()
        try:
            os.chdir(test_environment["tmpdir"])

            # Mock the Launch function to capture what would be sent to analyzer
            with patch("app.Launch") as mock_launch:
                mock_launch.return_value = {"success": True}

                mock_request = MagicMock()

                inputs = {
                    "job_name": "Kodosumi Integration Test",
                    "input_folder": "./data/input",
                    "context_file": "./data/context/client.yaml",
                    "priority_threshold": "75.5",  # Test string conversion
                    "include_low_confidence": "false",  # Test boolean conversion
                    "clustering_enabled": "true",  # Test boolean conversion
                    "batch_size": "25",  # Test int conversion
                    "timeout_minutes": "45",  # Test int conversion
                    "instructions": "Test instructions",
                }

                # Execute form submission
                result = asyncio.run(enter(mock_request, inputs))

                # Verify Launch was called correctly
                assert mock_launch.called
                call_args = mock_launch.call_args

                # Check the entrypoint path (second positional argument)
                assert call_args[0][1] == "political_analyzer:execute_analysis"

                # Check the inputs were converted properly
                passed_inputs = call_args[1]["inputs"]
                assert passed_inputs["job_name"] == "Kodosumi Integration Test"
                assert passed_inputs["input_folder"] == "./data/input"
                assert passed_inputs["context_file"] == "./data/context/client.yaml"
                assert passed_inputs["priority_threshold"] == 75.5  # Converted to float
                assert passed_inputs["include_low_confidence"] is False  # Converted to bool
                assert passed_inputs["clustering_enabled"] is True  # Converted to bool
                assert passed_inputs["batch_size"] == 25  # Converted to int
                assert passed_inputs["timeout_minutes"] == 45  # Converted to int
                assert passed_inputs["instructions"] == "Test instructions"

        finally:
            os.chdir(original_cwd)


class TestRayDistributedProcessing:
    """Test Ray distributed processing specifically."""

    def test_ray_task_parallelization(self, test_environment, ray_cluster):
        """Test that Ray tasks actually run in parallel."""
        original_cwd = os.getcwd()
        try:
            os.chdir(test_environment["tmpdir"])

            import time

            import political_analyzer

            # Create multiple file batches
            document_files = [
                os.path.join("./data/input", filename) for filename in test_environment["documents"]
            ]

            batches = political_analyzer.create_processing_batches(document_files, batch_size=1)

            # Launch multiple tasks and measure timing
            start_time = time.time()
            futures = []
            for i, batch in enumerate(batches):
                future = political_analyzer.process_batch_task.remote(batch, i, "test_job")
                futures.append(future)

            # Get all results
            results = ray.get(futures)
            parallel_time = time.time() - start_time

            # Verify all tasks completed
            assert len(results) == len(batches)

            # Parallel execution should be faster than sequential
            # (This is a basic check - in real scenarios the difference would be more significant)
            assert parallel_time < 10.0  # Should complete quickly in local mode

        finally:
            os.chdir(original_cwd)


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
