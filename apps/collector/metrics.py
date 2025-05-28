#!/usr/bin/env python3
"""
Prometheus Metrics Module

Provides comprehensive monitoring metrics for the Reddit sentiment analysis pipeline.
Tracks performance, health, and operational metrics for production monitoring.
"""

import logging
import time
from http.server import BaseHTTPRequestHandler
from typing import Dict, Optional

from prometheus_client import (
    Counter,
    Gauge,
    Histogram,
    Info,
    generate_latest,
    CollectorRegistry,
    CONTENT_TYPE_LATEST,
    start_http_server,
)

logger = logging.getLogger(__name__)


class PipelineMetrics:
    """
    Prometheus metrics collector for Reddit sentiment analysis pipeline.
    
    Tracks:
    - Collection statistics (posts fetched, deduplicated, processed)
    - Sentiment analysis performance (processing time, batch efficiency)
    - Error rates and failure modes
    - System health indicators
    """
    
    def __init__(self, registry: Optional[CollectorRegistry] = None):
        """Initialize metrics with optional custom registry."""
        # Use provided registry or create new one, but not None
        if registry is None:
            from prometheus_client import REGISTRY
            self.registry = REGISTRY
        else:
            self.registry = registry
        
        # Collection metrics
        self.posts_fetched_total = Counter(
            'reddit_posts_fetched_total',
            'Total number of Reddit posts fetched from API',
            ['subreddit'],
            registry=registry
        )
        
        self.posts_deduplicated_total = Counter(
            'reddit_posts_deduplicated_total', 
            'Total number of duplicate posts filtered out',
            registry=registry
        )
        
        self.posts_processed_total = Counter(
            'reddit_posts_processed_total',
            'Total number of posts successfully processed with sentiment',
            registry=registry
        )
        
        # Sentiment analysis metrics
        self.sentiment_analysis_duration = Histogram(
            'sentiment_analysis_duration_seconds',
            'Time spent analyzing sentiment for batches',
            buckets=[0.1, 0.5, 1.0, 2.5, 5.0, 10.0, 30.0, 60.0],
            registry=registry
        )
        
        self.sentiment_batch_size = Histogram(
            'sentiment_batch_size',
            'Number of posts processed in sentiment batches',
            buckets=[1, 5, 10, 25, 50, 100, 200],
            registry=registry
        )
        
        self.sentiment_distribution = Counter(
            'sentiment_distribution_total',
            'Distribution of sentiment labels',
            ['label'],
            registry=registry
        )
        
        # Error tracking
        self.errors_total = Counter(
            'pipeline_errors_total',
            'Total number of errors by component',
            ['component', 'error_type'],
            registry=registry
        )
        
        self.reddit_api_errors_total = Counter(
            'reddit_api_errors_total',
            'Reddit API specific errors',
            ['error_type'],
            registry=registry
        )
        
        # System health
        self.pipeline_status = Gauge(
            'pipeline_status',
            'Current pipeline status (1=healthy, 0=unhealthy)',
            registry=registry
        )
        
        self.last_successful_run = Gauge(
            'pipeline_last_successful_run_timestamp',
            'Timestamp of last successful pipeline run',
            registry=registry
        )
        
        self.pipeline_duration = Histogram(
            'pipeline_total_duration_seconds',
            'Total time for complete pipeline execution',
            buckets=[10, 30, 60, 120, 300, 600, 1200],
            registry=registry
        )
        
        # Resource usage
        self.memory_usage_bytes = Gauge(
            'pipeline_memory_usage_bytes',
            'Current memory usage of the pipeline process',
            registry=registry
        )
        
        self.model_load_duration = Histogram(
            'finbert_model_load_duration_seconds',
            'Time taken to load FinBERT model',
            buckets=[1, 5, 10, 30, 60, 120],
            registry=registry
        )
        
        # Info metrics
        self.build_info = Info(
            'pipeline_build_info',
            'Build information for the pipeline',
            registry=registry
        )
        
        # Initialize status as healthy
        self.pipeline_status.set(1)
        
        logger.info("Prometheus metrics initialized successfully")
    
    def record_posts_fetched(self, count: int, subreddit: str):
        """Record the number of posts fetched from a subreddit."""
        self.posts_fetched_total.labels(subreddit=subreddit).inc(count)
        logger.debug(f"Recorded {count} posts fetched from r/{subreddit}")
    
    def record_posts_deduplicated(self, count: int):
        """Record the number of duplicate posts filtered out."""
        self.posts_deduplicated_total.inc(count)
        logger.debug(f"Recorded {count} posts deduplicated")
    
    def record_posts_processed(self, count: int):
        """Record the number of posts successfully processed."""
        self.posts_processed_total.inc(count)
        logger.debug(f"Recorded {count} posts processed")
    
    def record_sentiment_analysis(self, duration: float, batch_size: int):
        """Record sentiment analysis performance metrics."""
        self.sentiment_analysis_duration.observe(duration)
        self.sentiment_batch_size.observe(batch_size)
        logger.debug(f"Recorded sentiment analysis: {duration:.2f}s for {batch_size} posts")
    
    def record_sentiment_distribution(self, sentiment_counts: Dict[str, int]):
        """Record the distribution of sentiment labels."""
        for label, count in sentiment_counts.items():
            self.sentiment_distribution.labels(label=label).inc(count)
        logger.debug(f"Recorded sentiment distribution: {sentiment_counts}")
    
    def record_error(self, component: str, error_type: str):
        """Record an error by component and type."""
        self.errors_total.labels(component=component, error_type=error_type).inc()
        self.pipeline_status.set(0)  # Mark as unhealthy
        logger.warning(f"Recorded error in {component}: {error_type}")
    
    def record_reddit_api_error(self, error_type: str):
        """Record a Reddit API specific error."""
        self.reddit_api_errors_total.labels(error_type=error_type).inc()
        logger.warning(f"Recorded Reddit API error: {error_type}")
    
    def record_successful_run(self, duration: float):
        """Record a successful pipeline run."""
        self.pipeline_status.set(1)  # Mark as healthy
        self.last_successful_run.set(time.time())
        self.pipeline_duration.observe(duration)
        logger.info(f"Recorded successful pipeline run: {duration:.2f}s")
    
    def record_memory_usage(self, bytes_used: int):
        """Record current memory usage."""
        self.memory_usage_bytes.set(bytes_used)
    
    def record_model_load_time(self, duration: float):
        """Record FinBERT model loading time."""
        self.model_load_duration.observe(duration)
        logger.debug(f"Recorded model load time: {duration:.2f}s")
    
    def set_build_info(self, version: str, commit: str = "", build_date: str = ""):
        """Set build information."""
        self.build_info.info({
            'version': version,
            'commit': commit,
            'build_date': build_date
        })
        logger.info(f"Set build info: version={version}, commit={commit}")
    
    def get_metrics_text(self) -> str:
        """Get metrics in Prometheus text format."""
        return generate_latest(self.registry).decode('utf-8')
    
    def get_content_type(self) -> str:
        """Get the content type for metrics response."""
        return CONTENT_TYPE_LATEST
    
    def reset_health_status(self):
        """Reset pipeline to healthy status."""
        self.pipeline_status.set(1)


# Global metrics instance
_metrics_instance: Optional[PipelineMetrics] = None


def get_metrics() -> PipelineMetrics:
    """Get the global metrics instance, creating it if needed."""
    global _metrics_instance
    if _metrics_instance is None:
        _metrics_instance = PipelineMetrics()
    return _metrics_instance


def initialize_metrics(registry: Optional[CollectorRegistry] = None) -> PipelineMetrics:
    """Initialize global metrics instance with optional custom registry."""
    global _metrics_instance
    _metrics_instance = PipelineMetrics(registry=registry)
    return _metrics_instance


class MetricsHandler(BaseHTTPRequestHandler):
    """HTTP handler for metrics requests."""
    
    def __init__(self, metrics: PipelineMetrics, *args, **kwargs):
        self.metrics = metrics
        super().__init__(*args, **kwargs)
    
    def do_GET(self):
        """Handle GET requests."""
        if self.path == '/metrics':
            self.send_response(200)
            self.send_header('Content-Type', CONTENT_TYPE_LATEST)
            self.end_headers()
            
            metrics_text = generate_latest(self.metrics.registry)
            self.wfile.write(metrics_text)
        elif self.path == '/health':
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            self.wfile.write(b'{"status": "healthy"}')
        else:
            self.send_response(404)
            self.end_headers()
            self.wfile.write(b'Not Found')
    
    def log_message(self, format, *args):
        """Override to use our logger."""
        logger.debug(f"HTTP {format % args}")


class MetricsServer:
    """
    HTTP server to expose Prometheus metrics on /metrics endpoint.
    
    This will be used when running as a standalone service or in Kubernetes
    where Prometheus needs to scrape metrics.
    """
    
    def __init__(self, port: int = 8000, metrics: Optional[PipelineMetrics] = None):
        """Initialize metrics server."""
        self.port = port
        self.metrics = metrics or get_metrics()
        self.server = None
        self.server_thread = None
        self.running = False
        logger.info(f"Metrics server initialized on port {port}")
    
    def start(self):
        """Start the metrics server in a background thread."""
        if self.running:
            logger.warning("Metrics server is already running")
            return
        
        try:
            # Use prometheus_client's built-in server
            start_http_server(self.port, registry=self.metrics.registry)
            self.running = True
            logger.info(f"Metrics server started on port {self.port}")
            logger.info(f"Metrics available at http://localhost:{self.port}/metrics")
            
        except Exception as e:
            logger.error(f"Failed to start metrics server: {e}")
            raise
    
    def stop(self):
        """Stop the metrics server."""
        if not self.running:
            return
        
        self.running = False
        logger.info("Metrics server stopped")
    
    def get_metrics_response(self) -> tuple[str, str]:
        """Get metrics response for manual serving."""
        metrics_text = generate_latest(self.metrics.registry).decode('utf-8')
        return metrics_text, CONTENT_TYPE_LATEST
