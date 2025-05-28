#!/usr/bin/env python3
"""
Tests for Prometheus metrics integration in Reddit sentiment analysis pipeline.

Tests coverage:
- Metrics initialization and configuration
- Counter, Gauge, and Histogram metric types
- Error tracking and health monitoring
- Metrics server functionality
- Integration with collector components
"""

import pytest
import time
import tempfile
from unittest.mock import Mock, patch, MagicMock
from prometheus_client import CollectorRegistry, generate_latest

# Import our modules
from apps.collector.metrics import (
    PipelineMetrics,
    MetricsServer,
    get_metrics,
    initialize_metrics,
)


class TestPipelineMetrics:
    """Test suite for PipelineMetrics class."""

    def setup_method(self):
        """Set up test fixtures."""
        # Use custom registry for each test to avoid conflicts
        self.registry = CollectorRegistry()
        self.metrics = PipelineMetrics(registry=self.registry)

    def test_metrics_initialization(self):
        """Test that metrics are properly initialized."""
        assert self.metrics is not None
        assert self.metrics.registry == self.registry
        
        # Check that all metrics are created
        assert hasattr(self.metrics, 'posts_fetched_total')
        assert hasattr(self.metrics, 'posts_deduplicated_total')
        assert hasattr(self.metrics, 'posts_processed_total')
        assert hasattr(self.metrics, 'sentiment_analysis_duration')
        assert hasattr(self.metrics, 'sentiment_batch_size')
        assert hasattr(self.metrics, 'sentiment_distribution')
        assert hasattr(self.metrics, 'errors_total')
        assert hasattr(self.metrics, 'reddit_api_errors_total')
        assert hasattr(self.metrics, 'pipeline_status')
        assert hasattr(self.metrics, 'last_successful_run')
        assert hasattr(self.metrics, 'pipeline_duration')
        assert hasattr(self.metrics, 'memory_usage_bytes')
        assert hasattr(self.metrics, 'model_load_duration')
        assert hasattr(self.metrics, 'build_info')

    def test_default_registry_initialization(self):
        """Test metrics initialization with default registry."""
        metrics = PipelineMetrics()
        assert metrics.registry is None  # Uses default registry

    def test_record_posts_fetched(self):
        """Test recording posts fetched metrics."""
        self.metrics.record_posts_fetched(50, "Bitcoin")
        self.metrics.record_posts_fetched(30, "ethereum")
        
        # Verify metrics are recorded
        metrics_text = generate_latest(self.registry).decode('utf-8')
        assert 'reddit_posts_fetched_total{subreddit="Bitcoin"} 50.0' in metrics_text
        assert 'reddit_posts_fetched_total{subreddit="ethereum"} 30.0' in metrics_text

    def test_record_posts_deduplicated(self):
        """Test recording deduplication metrics."""
        self.metrics.record_posts_deduplicated(15)
        
        metrics_text = generate_latest(self.registry).decode('utf-8')
        assert 'reddit_posts_deduplicated_total 15.0' in metrics_text

    def test_record_posts_processed(self):
        """Test recording processed posts metrics."""
        self.metrics.record_posts_processed(45)
        
        metrics_text = generate_latest(self.registry).decode('utf-8')
        assert 'reddit_posts_processed_total 45.0' in metrics_text

    def test_record_sentiment_analysis(self):
        """Test recording sentiment analysis performance metrics."""
        self.metrics.record_sentiment_analysis(2.5, 10)
        
        metrics_text = generate_latest(self.registry).decode('utf-8')
        assert 'sentiment_analysis_duration_seconds' in metrics_text
        assert 'sentiment_batch_size' in metrics_text

    def test_record_sentiment_distribution(self):
        """Test recording sentiment distribution metrics."""
        sentiment_counts = {
            'positive': 20,
            'negative': 5,
            'neutral': 35
        }
        self.metrics.record_sentiment_distribution(sentiment_counts)
        
        metrics_text = generate_latest(self.registry).decode('utf-8')
        assert 'sentiment_distribution_total{label="positive"} 20.0' in metrics_text
        assert 'sentiment_distribution_total{label="negative"} 5.0' in metrics_text
        assert 'sentiment_distribution_total{label="neutral"} 35.0' in metrics_text

    def test_record_error(self):
        """Test error recording and health status update."""
        # Initially healthy
        assert self.metrics.pipeline_status._value._value == 1
        
        self.metrics.record_error("sentiment_analyzer", "model_load_failed")
        
        # Should mark as unhealthy
        assert self.metrics.pipeline_status._value._value == 0
        
        metrics_text = generate_latest(self.registry).decode('utf-8')
        assert 'pipeline_errors_total{component="sentiment_analyzer",error_type="model_load_failed"} 1.0' in metrics_text

    def test_record_reddit_api_error(self):
        """Test Reddit API error recording."""
        self.metrics.record_reddit_api_error("rate_limit_exceeded")
        
        metrics_text = generate_latest(self.registry).decode('utf-8')
        assert 'reddit_api_errors_total{error_type="rate_limit_exceeded"} 1.0' in metrics_text

    def test_record_successful_run(self):
        """Test recording successful pipeline run."""
        duration = 45.5
        
        # Mock time.time() to test timestamp recording
        with patch('time.time', return_value=1640995200):
            self.metrics.record_successful_run(duration)
        
        # Should mark as healthy
        assert self.metrics.pipeline_status._value._value == 1
        
        # Check timestamp is recorded
        assert self.metrics.last_successful_run._value._value == 1640995200
        
        metrics_text = generate_latest(self.registry).decode('utf-8')
        assert 'pipeline_total_duration_seconds' in metrics_text

    def test_record_memory_usage(self):
        """Test memory usage recording."""
        memory_bytes = 1024 * 1024 * 256  # 256 MB
        self.metrics.record_memory_usage(memory_bytes)
        
        assert self.metrics.memory_usage_bytes._value._value == memory_bytes

    def test_record_model_load_time(self):
        """Test model load time recording."""
        load_time = 12.3
        self.metrics.record_model_load_time(load_time)
        
        metrics_text = generate_latest(self.registry).decode('utf-8')
        assert 'finbert_model_load_duration_seconds' in metrics_text

    def test_set_build_info(self):
        """Test setting build information."""
        self.metrics.set_build_info(
            version="1.0.0",
            commit="abc123def",
            build_date="2025-01-01"
        )
        
        metrics_text = generate_latest(self.registry).decode('utf-8')
        assert 'pipeline_build_info_info{build_date="2025-01-01",commit="abc123def",version="1.0.0"} 1.0' in metrics_text

    def test_get_metrics_text(self):
        """Test getting metrics in Prometheus text format."""
        self.metrics.record_posts_fetched(10, "Bitcoin")
        
        metrics_text = self.metrics.get_metrics_text()
        assert isinstance(metrics_text, str)
        assert 'reddit_posts_fetched_total' in metrics_text

    def test_get_content_type(self):
        """Test getting correct content type for metrics."""
        content_type = self.metrics.get_content_type()
        assert content_type == 'text/plain; version=0.0.4; charset=utf-8'

    def test_reset_health_status(self):
        """Test resetting health status to healthy."""
        # Mark as unhealthy first
        self.metrics.record_error("test", "test_error")
        assert self.metrics.pipeline_status._value._value == 0
        
        # Reset to healthy
        self.metrics.reset_health_status()
        assert self.metrics.pipeline_status._value._value == 1


class TestMetricsServer:
    """Test suite for MetricsServer class."""

    def test_metrics_server_initialization(self):
        """Test metrics server initialization."""
        registry = CollectorRegistry()
        metrics = PipelineMetrics(registry=registry)
        server = MetricsServer(port=8080, metrics=metrics)
        
        assert server.port == 8080
        assert server.metrics == metrics

    def test_metrics_server_default_initialization(self):
        """Test metrics server with default configuration."""
        server = MetricsServer()
        assert server.port == 8000
        assert server.metrics is not None

    def test_start_server(self):
        """Test starting the metrics server (placeholder functionality)."""
        registry = CollectorRegistry()
        metrics = PipelineMetrics(registry=registry)
        server = MetricsServer(metrics=metrics)
        
        # Since we're not implementing a real HTTP server in this step,
        # just test that the method exists and returns successfully
        result = server.start_server()
        assert result is True

    def test_get_metrics_response(self):
        """Test getting metrics response for manual serving."""
        registry = CollectorRegistry()
        metrics = PipelineMetrics(registry=registry)
        metrics.record_posts_fetched(5, "Bitcoin")
        
        server = MetricsServer(metrics=metrics)
        content, content_type = server.get_metrics_response()
        
        assert isinstance(content, str)
        assert 'reddit_posts_fetched_total' in content
        assert content_type == 'text/plain; version=0.0.4; charset=utf-8'


class TestGlobalMetricsManagement:
    """Test suite for global metrics management functions."""

    def test_get_metrics_singleton(self):
        """Test global metrics singleton behavior."""
        # Reset global instance for clean test
        import apps.collector.metrics as metrics_module
        metrics_module._metrics_instance = None
        
        metrics1 = get_metrics()
        metrics2 = get_metrics()
        
        assert metrics1 is metrics2  # Should be the same instance

    def test_initialize_metrics_with_registry(self):
        """Test initializing global metrics with custom registry."""
        registry = CollectorRegistry()
        metrics = initialize_metrics(registry=registry)
        
        assert metrics.registry == registry

    def test_initialize_metrics_overwrites_global(self):
        """Test that initialize_metrics overwrites the global instance."""
        registry1 = CollectorRegistry()
        registry2 = CollectorRegistry()
        
        metrics1 = initialize_metrics(registry=registry1)
        metrics2 = initialize_metrics(registry=registry2)
        
        assert metrics1 is not metrics2
        assert metrics2.registry == registry2


class TestMetricsIntegration:
    """Integration tests for metrics with collector components."""

    def test_metrics_with_collector_simulation(self):
        """Test metrics recording in a simulated collector workflow."""
        registry = CollectorRegistry()
        metrics = PipelineMetrics(registry=registry)
        
        # Simulate a full pipeline run
        start_time = time.time()
        
        # Fetch phase
        metrics.record_posts_fetched(50, "Bitcoin")
        metrics.record_posts_fetched(30, "ethereum")
        
        # Deduplication phase
        metrics.record_posts_deduplicated(15)
        
        # Sentiment analysis phase
        metrics.record_sentiment_analysis(3.2, 65)
        metrics.record_sentiment_distribution({
            'positive': 25,
            'negative': 10,
            'neutral': 30
        })
        
        # Processing completion
        metrics.record_posts_processed(65)
        metrics.record_memory_usage(256 * 1024 * 1024)  # 256 MB
        
        # Successful completion
        duration = time.time() - start_time
        metrics.record_successful_run(duration)
        
        # Verify all metrics are recorded
        metrics_text = generate_latest(registry).decode('utf-8')
        
        assert 'reddit_posts_fetched_total{subreddit="Bitcoin"} 50.0' in metrics_text
        assert 'reddit_posts_fetched_total{subreddit="ethereum"} 30.0' in metrics_text
        assert 'reddit_posts_deduplicated_total 15.0' in metrics_text
        assert 'reddit_posts_processed_total 65.0' in metrics_text
        assert 'sentiment_distribution_total{label="positive"} 25.0' in metrics_text
        assert 'sentiment_distribution_total{label="negative"} 10.0' in metrics_text
        assert 'sentiment_distribution_total{label="neutral"} 30.0' in metrics_text
        assert 'pipeline_status 1.0' in metrics_text  # Healthy

    def test_metrics_error_scenarios(self):
        """Test metrics recording during error scenarios."""
        registry = CollectorRegistry()
        metrics = PipelineMetrics(registry=registry)
        
        # Simulate various error conditions
        metrics.record_reddit_api_error("authentication_failed")
        metrics.record_error("deduplicator", "database_error")
        metrics.record_error("sentiment_analyzer", "model_unavailable")
        
        metrics_text = generate_latest(registry).decode('utf-8')
        
        assert 'reddit_api_errors_total{error_type="authentication_failed"} 1.0' in metrics_text
        assert 'pipeline_errors_total{component="deduplicator",error_type="database_error"} 1.0' in metrics_text
        assert 'pipeline_errors_total{component="sentiment_analyzer",error_type="model_unavailable"} 1.0' in metrics_text
        assert 'pipeline_status 0.0' in metrics_text  # Unhealthy due to errors

    @patch('apps.collector.metrics.logger')
    def test_metrics_logging(self, mock_logger):
        """Test that metrics operations produce appropriate log messages."""
        registry = CollectorRegistry()
        metrics = PipelineMetrics(registry=registry)
        
        metrics.record_posts_fetched(10, "Bitcoin")
        metrics.record_error("test_component", "test_error")
        metrics.record_successful_run(30.0)
        
        # Verify logging calls were made
        assert mock_logger.debug.called
        assert mock_logger.warning.called
        assert mock_logger.info.called
