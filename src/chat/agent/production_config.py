"""
Production configuration and optimization settings for multi-agent system.
"""

import logging
import os
from dataclasses import dataclass
from enum import Enum
from typing import Any, Optional

logger = logging.getLogger(__name__)


class DeploymentMode(Enum):
    """Deployment mode configuration."""

    DEVELOPMENT = "development"
    STAGING = "staging"
    PRODUCTION = "production"


class PerformanceLevel(Enum):
    """Performance optimization levels."""

    BASIC = "basic"
    OPTIMIZED = "optimized"
    HIGH_PERFORMANCE = "high_performance"


@dataclass
class ResourceLimits:
    """Resource usage limits for production deployment."""

    max_memory_mb: int = 2048
    max_cpu_cores: int = 4
    max_concurrent_requests: int = 100
    max_execution_time_seconds: int = 60
    max_response_length: int = 10000
    max_tool_executions: int = 10


@dataclass
class QualityThresholds:
    """Quality thresholds for production deployment."""

    minimum_response_quality: float = 0.7
    minimum_confidence: float = 0.6
    maximum_error_rate: float = 0.1
    quality_assessment_enabled: bool = True
    auto_optimization_enabled: bool = True


@dataclass
class MonitoringConfig:
    """Monitoring and logging configuration."""

    enable_performance_monitoring: bool = True
    enable_quality_monitoring: bool = True
    enable_user_feedback_tracking: bool = True
    log_level: str = "INFO"
    metrics_export_interval: int = 300  # seconds
    enable_distributed_tracing: bool = False


class ProductionConfig:
    """Centralized production configuration management."""

    def __init__(self, deployment_mode: DeploymentMode | None = None):
        self.deployment_mode = deployment_mode or self._detect_deployment_mode()
        self.performance_level = self._determine_performance_level()

        # Load configuration based on deployment mode
        self.resource_limits = self._load_resource_limits()
        self.quality_thresholds = self._load_quality_thresholds()
        self.monitoring_config = self._load_monitoring_config()

        # Performance optimization settings
        self.optimization_settings = self._load_optimization_settings()

        # Integration settings
        self.integration_settings = self._load_integration_settings()

        logger.info(f"Production config loaded for {self.deployment_mode.value} mode")

    def _detect_deployment_mode(self) -> DeploymentMode:
        """Auto-detect deployment mode from environment."""
        env_mode = os.getenv("DEPLOYMENT_MODE", "development").lower()

        if env_mode in ["prod", "production"]:
            return DeploymentMode.PRODUCTION
        elif env_mode in ["stage", "staging"]:
            return DeploymentMode.STAGING
        else:
            return DeploymentMode.DEVELOPMENT

    def _determine_performance_level(self) -> PerformanceLevel:
        """Determine performance level based on deployment mode."""
        if self.deployment_mode == DeploymentMode.PRODUCTION:
            return PerformanceLevel.HIGH_PERFORMANCE
        elif self.deployment_mode == DeploymentMode.STAGING:
            return PerformanceLevel.OPTIMIZED
        else:
            return PerformanceLevel.BASIC

    def _load_resource_limits(self) -> ResourceLimits:
        """Load resource limits based on deployment mode."""
        if self.deployment_mode == DeploymentMode.PRODUCTION:
            return ResourceLimits(
                max_memory_mb=4096,
                max_cpu_cores=8,
                max_concurrent_requests=500,
                max_execution_time_seconds=45,
                max_response_length=15000,
                max_tool_executions=15,
            )
        elif self.deployment_mode == DeploymentMode.STAGING:
            return ResourceLimits(
                max_memory_mb=2048,
                max_cpu_cores=4,
                max_concurrent_requests=200,
                max_execution_time_seconds=60,
                max_response_length=12000,
                max_tool_executions=12,
            )
        else:
            return ResourceLimits()  # Development defaults

    def _load_quality_thresholds(self) -> QualityThresholds:
        """Load quality thresholds based on deployment mode."""
        if self.deployment_mode == DeploymentMode.PRODUCTION:
            return QualityThresholds(
                minimum_response_quality=0.8,
                minimum_confidence=0.7,
                maximum_error_rate=0.05,
                quality_assessment_enabled=True,
                auto_optimization_enabled=True,
            )
        elif self.deployment_mode == DeploymentMode.STAGING:
            return QualityThresholds(
                minimum_response_quality=0.75,
                minimum_confidence=0.65,
                maximum_error_rate=0.08,
                quality_assessment_enabled=True,
                auto_optimization_enabled=True,
            )
        else:
            return QualityThresholds()  # Development defaults

    def _load_monitoring_config(self) -> MonitoringConfig:
        """Load monitoring configuration based on deployment mode."""
        if self.deployment_mode == DeploymentMode.PRODUCTION:
            return MonitoringConfig(
                enable_performance_monitoring=True,
                enable_quality_monitoring=True,
                enable_user_feedback_tracking=True,
                log_level="WARNING",
                metrics_export_interval=60,
                enable_distributed_tracing=True,
            )
        elif self.deployment_mode == DeploymentMode.STAGING:
            return MonitoringConfig(
                enable_performance_monitoring=True,
                enable_quality_monitoring=True,
                enable_user_feedback_tracking=True,
                log_level="INFO",
                metrics_export_interval=120,
                enable_distributed_tracing=False,
            )
        else:
            return MonitoringConfig(log_level="DEBUG", metrics_export_interval=300)

    def _load_optimization_settings(self) -> dict[str, Any]:
        """Load performance optimization settings."""
        base_settings = {
            "enable_response_caching": False,
            "cache_ttl_seconds": 300,
            "enable_query_preprocessing": True,
            "enable_result_compression": False,
            "parallel_tool_execution": False,
            "adaptive_timeout": True,
            "memory_optimization": False,
            "enable_request_batching": False,
        }

        if self.performance_level == PerformanceLevel.HIGH_PERFORMANCE:
            base_settings.update(
                {
                    "enable_response_caching": True,
                    "cache_ttl_seconds": 600,
                    "enable_result_compression": True,
                    "parallel_tool_execution": True,
                    "memory_optimization": True,
                    "enable_request_batching": True,
                }
            )
        elif self.performance_level == PerformanceLevel.OPTIMIZED:
            base_settings.update(
                {
                    "enable_response_caching": True,
                    "cache_ttl_seconds": 300,
                    "parallel_tool_execution": True,
                    "memory_optimization": False,
                }
            )

        return base_settings

    def _load_integration_settings(self) -> dict[str, Any]:
        """Load integration and external service settings."""
        return {
            "graphiti": {
                "enabled": os.getenv("GRAPHITI_ENABLED", "true").lower() == "true",
                "host": os.getenv("GRAPHITI_HOST", "localhost"),
                "port": int(os.getenv("GRAPHITI_PORT", "8000")),
                "timeout_seconds": int(os.getenv("GRAPHITI_TIMEOUT", "30")),
                "max_retries": int(os.getenv("GRAPHITI_MAX_RETRIES", "3")),
            },
            "neo4j": {
                "enabled": os.getenv("NEO4J_ENABLED", "true").lower() == "true",
                "uri": os.getenv("NEO4J_URI", "bolt://localhost:7687"),
                "username": os.getenv("NEO4J_USERNAME", "neo4j"),
                "password": os.getenv("NEO4J_PASSWORD", "password123"),
                "timeout_seconds": int(os.getenv("NEO4J_TIMEOUT", "30")),
                "pool_size": int(os.getenv("NEO4J_POOL_SIZE", "10")),
            },
            "langfuse": {
                "enabled": os.getenv("LANGFUSE_ENABLED", "false").lower() == "true",
                "host": os.getenv("LANGFUSE_HOST", "localhost"),
                "port": int(os.getenv("LANGFUSE_PORT", "3001")),
                "public_key": os.getenv("LANGFUSE_PUBLIC_KEY", ""),
                "secret_key": os.getenv("LANGFUSE_SECRET_KEY", ""),
            },
            "openai": {
                "api_key": os.getenv("OPENAI_API_KEY", ""),
                "model": os.getenv("OPENAI_MODEL", "gpt-4o-mini"),
                "max_tokens": int(os.getenv("OPENAI_MAX_TOKENS", "4000")),
                "temperature": float(os.getenv("OPENAI_TEMPERATURE", "0.1")),
                "timeout_seconds": int(os.getenv("OPENAI_TIMEOUT", "60")),
            },
        }

    def get_llm_config(self) -> dict[str, Any]:
        """Get LLM configuration optimized for deployment mode."""
        base_config: dict[str, Any] = self.integration_settings["openai"].copy()

        if self.deployment_mode == DeploymentMode.PRODUCTION:
            base_config.update(
                {
                    "temperature": 0.0,  # More deterministic
                    "max_retries": 3,
                    "retry_delay": 1.0,
                }
            )
        elif self.deployment_mode == DeploymentMode.STAGING:
            base_config.update({"temperature": 0.1, "max_retries": 2, "retry_delay": 0.5})

        return base_config

    def get_memory_config(self) -> dict[str, Any]:
        """Get memory system configuration."""
        return {
            "max_conversation_tokens": 4000
            if self.deployment_mode == DeploymentMode.PRODUCTION
            else 2000,
            "max_user_patterns": 1000,
            "pattern_retention_days": 90
            if self.deployment_mode == DeploymentMode.PRODUCTION
            else 30,
            "enable_pattern_compression": self.deployment_mode == DeploymentMode.PRODUCTION,
            "memory_cleanup_interval": 3600,  # 1 hour
        }

    def get_streaming_config(self) -> dict[str, Any]:
        """Get streaming configuration."""
        return {
            "enable_thinking_output": True,
            "adaptive_timing": True,
            "max_thinking_length": 500,
            "enable_progress_indicators": True,
            "stream_buffer_size": 1024
            if self.deployment_mode == DeploymentMode.PRODUCTION
            else 512,
        }

    def get_tool_config(self) -> dict[str, Any]:
        """Get tool integration configuration."""
        return {
            "max_parallel_tools": 5 if self.optimization_settings["parallel_tool_execution"] else 1,
            "tool_timeout_seconds": self.resource_limits.max_execution_time_seconds // 2,
            "enable_tool_caching": self.optimization_settings["enable_response_caching"],
            "max_tool_retries": 2,
            "enable_intelligent_selection": True,
        }

    def validate_configuration(self) -> dict[str, Any]:
        """Validate configuration and return validation results."""
        validation_results: dict[str, Any] = {"valid": True, "warnings": [], "errors": []}
        warnings: list[str] = validation_results["warnings"]
        errors: list[str] = validation_results["errors"]

        # Check required environment variables for production
        if self.deployment_mode == DeploymentMode.PRODUCTION:
            required_vars = ["OPENAI_API_KEY"]
            for var in required_vars:
                if not os.getenv(var):
                    errors.append(
                        f"Missing required environment variable: {var}"
                    )
                    validation_results["valid"] = False

        # Check resource limits
        if self.resource_limits.max_memory_mb < 512:
            warnings.append(
                "Memory limit may be too low for optimal performance"
            )

        # Check quality thresholds
        if self.quality_thresholds.minimum_response_quality > 0.9:
            warnings.append("Quality threshold may be too strict")

        # Check integration settings
        if not self.integration_settings["graphiti"]["enabled"]:
            warnings.append(
                "Graphiti integration disabled - tool intelligence limited"
            )

        return validation_results


class PerformanceOptimizer:
    """Runtime performance optimization for multi-agent system."""

    def __init__(self, config: ProductionConfig):
        self.config = config
        self.performance_metrics: dict[str, Any] = {
            "request_count": 0,
            "total_execution_time": 0.0,
            "error_count": 0,
            "quality_scores": [],
        }

    def should_enable_caching(self, query: str) -> bool:
        """Determine if caching should be enabled for this query."""
        if not self.config.optimization_settings["enable_response_caching"]:
            return False

        # Enable caching for common query patterns
        common_patterns = ["what is", "how does", "explain", "describe"]
        return any(pattern in query.lower() for pattern in common_patterns)

    def calculate_timeout(self, query_complexity: str, tool_count: int) -> float:
        """Calculate adaptive timeout based on query complexity."""
        base_timeout = self.config.resource_limits.max_execution_time_seconds

        complexity_multipliers = {"simple": 0.5, "medium": 1.0, "complex": 1.5}

        complexity_factor = complexity_multipliers.get(query_complexity, 1.0)
        tool_factor = min(1.0 + (tool_count * 0.2), 2.0)

        return min(base_timeout, base_timeout * complexity_factor * tool_factor)

    def should_parallelize_tools(self, tool_count: int, query_complexity: str) -> bool:
        """Determine if tools should be executed in parallel."""
        if not self.config.optimization_settings["parallel_tool_execution"]:
            return False

        # Parallelize for multiple tools in complex queries
        return tool_count >= 3 and query_complexity in ["medium", "complex"]

    def optimize_memory_usage(self, conversation_length: int) -> dict[str, Any]:
        """Optimize memory usage based on conversation length."""
        optimizations = {
            "enable_compression": False,
            "max_history": conversation_length,
            "cleanup_old_patterns": False,
        }

        if self.config.optimization_settings["memory_optimization"]:
            if conversation_length > 50:
                optimizations.update(
                    {"enable_compression": True, "max_history": 30, "cleanup_old_patterns": True}
                )

        return optimizations

    def update_performance_metrics(
        self, execution_time: float, success: bool, quality_score: float | None = None
    ) -> None:
        """Update performance metrics."""
        request_count: int = self.performance_metrics["request_count"]
        total_execution_time: float = self.performance_metrics["total_execution_time"]
        error_count: int = self.performance_metrics["error_count"]
        quality_scores: list[float] = self.performance_metrics["quality_scores"]

        self.performance_metrics["request_count"] = request_count + 1
        self.performance_metrics["total_execution_time"] = total_execution_time + execution_time

        if not success:
            self.performance_metrics["error_count"] = error_count + 1

        if quality_score is not None:
            quality_scores.append(quality_score)

    def get_performance_summary(self) -> dict[str, Any]:
        """Get performance summary and recommendations."""
        total_requests: int = self.performance_metrics["request_count"]

        if total_requests == 0:
            return {"status": "no_data"}

        total_execution_time: float = self.performance_metrics["total_execution_time"]
        error_count: int = self.performance_metrics["error_count"]
        quality_scores: list[float] = self.performance_metrics["quality_scores"]

        avg_execution_time = total_execution_time / total_requests
        error_rate = error_count / total_requests
        avg_quality = (
            sum(quality_scores)
            / len(quality_scores)
            if quality_scores
            else 0.0
        )

        summary: dict[str, Any] = {
            "total_requests": total_requests,
            "avg_execution_time": avg_execution_time,
            "error_rate": error_rate,
            "avg_quality_score": avg_quality,
            "performance_status": "good",
            "recommendations": [],
        }
        recommendations: list[str] = summary["recommendations"]

        # Generate recommendations
        if avg_execution_time > self.config.resource_limits.max_execution_time_seconds * 0.8:
            summary["performance_status"] = "slow"
            recommendations.append("Consider enabling parallel tool execution")

        if error_rate > self.config.quality_thresholds.maximum_error_rate:
            summary["performance_status"] = "unstable"
            recommendations.append("Review error patterns and improve error handling")

        if avg_quality < self.config.quality_thresholds.minimum_response_quality:
            recommendations.append("Enable quality optimization features")

        return summary


# Global configuration instance
_global_config: ProductionConfig | None = None


def get_production_config() -> ProductionConfig:
    """Get or create global production configuration."""
    global _global_config
    if _global_config is None:
        _global_config = ProductionConfig()
    return _global_config


def initialize_production_config(deployment_mode: DeploymentMode | None = None) -> ProductionConfig:
    """Initialize production configuration with specific deployment mode."""
    global _global_config
    _global_config = ProductionConfig(deployment_mode)
    return _global_config
