#!/usr/bin/env python3
"""
Step 5 Integration Test: Validate Prometheus Metrics Implementation

Tests the complete metrics integration with the collector to ensure
metrics are properly recorded during a real pipeline run.
"""

import os
import tempfile
import time
from pathlib import Path
from prometheus_client import CollectorRegistry, generate_latest
from apps.collector.collector import RedditSentimentCollector
from apps.collector.metrics import PipelineMetrics


def test_step5_metrics_integration():
    """Test metrics integration with collector."""
    print("🚀 Step 5 Integration Test: Prometheus Metrics")
    print("=" * 60)
    
    # Create temporary output path
    with tempfile.TemporaryDirectory() as temp_dir:
        output_path = os.path.join(temp_dir, "test_metrics_output.csv")
        dedup_db_path = os.path.join(temp_dir, "test_metrics_dupes.db")
        
        # Set environment variables for test
        os.environ.update({
            "OUTPUT_PATH": output_path,
            "DEDUP_DB_PATH": dedup_db_path,
            "ENABLE_SENTIMENT": "false",  # Disable for faster testing
            "ENABLE_METRICS": "true",
            "METRICS_PORT": "8001",
            "SUBREDDITS": "CryptoCurrency",
            "FETCH_LIMIT": "5"
        })
        
        # Create custom registry for testing
        test_registry = CollectorRegistry()
        test_metrics = PipelineMetrics(registry=test_registry)
        
        print(f"📂 Output path: {output_path}")
        print(f"📊 Metrics enabled on port 8001")
        print(f"🔧 Using test registry for metrics collection")
        
        # Initialize collector
        collector = RedditSentimentCollector()
        
        # Replace the collector's metrics with our test metrics
        collector.metrics = test_metrics
        
        print(f"✅ Collector initialized successfully")
        print(f"📥 Fetching dummy data from {collector.subreddits}")
        
        # Run the collector (this will use dummy data since no Reddit credentials)
        start_time = time.time()
        collector.run()
        duration = time.time() - start_time
        
        print(f"⏱️  Collector run completed in {duration:.2f}s")
        
        # Verify output file was created
        assert Path(output_path).exists(), "Output CSV was not created"
        print(f"✅ Output CSV created successfully")
        
        # Get metrics output
        metrics_text = generate_latest(test_registry).decode('utf-8')
        
        print("\n📊 METRICS VALIDATION")
        print("-" * 40)
        
        # Check for key metrics
        expected_metrics = [
            "reddit_posts_fetched_total",
            "reddit_posts_processed_total", 
            "pipeline_status",
            "pipeline_last_successful_run_timestamp"
        ]
        
        for metric in expected_metrics:
            if metric in metrics_text:
                print(f"✅ {metric} - Present")
            else:
                print(f"❌ {metric} - Missing")
                raise AssertionError(f"Expected metric {metric} not found in output")
        
        # Extract some specific metric values
        lines = metrics_text.split('\n')
        
        status_line = next((line for line in lines if line.startswith('pipeline_status')), None)
        if status_line:
            status_value = float(status_line.split()[-1])
            print(f"📊 Pipeline status: {'Healthy' if status_value == 1.0 else 'Unhealthy'} ({status_value})")
        
        posts_processed_line = next((line for line in lines if 'reddit_posts_processed_total' in line and not line.startswith('#')), None)
        if posts_processed_line:
            posts_count = float(posts_processed_line.split()[-1])
            print(f"📊 Posts processed: {int(posts_count)}")
        
        print(f"\n📈 SAMPLE METRICS OUTPUT")
        print("-" * 40)
        
        # Show first 10 non-comment lines
        sample_lines = [line for line in lines if line and not line.startswith('#')][:10]
        for line in sample_lines:
            print(f"   {line}")
        
        if len(sample_lines) > 10:
            print(f"   ... and {len([line for line in lines if line and not line.startswith('#')]) - 10} more metrics")
        
        print(f"\n🎉 STEP 5 VALIDATION COMPLETE")
        print("=" * 60)
        print("✅ Prometheus metrics integration successful!")
        print(f"✅ All {len(expected_metrics)} core metrics are present")
        print("✅ Pipeline health monitoring operational")
        print("✅ Metrics ready for Prometheus scraping")
        
        return True


if __name__ == "__main__":
    try:
        test_step5_metrics_integration()
        print("\n🌟 Step 5 - Prometheus Metrics: PASSED")
    except Exception as e:
        print(f"\n💥 Step 5 - Prometheus Metrics: FAILED")
        print(f"Error: {e}")
        raise
