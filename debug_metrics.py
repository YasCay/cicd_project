#!/usr/bin/env python3
"""
Quick test to check metrics content.
"""

import os
import sys
import tempfile
import time
from pathlib import Path
import threading
import requests

# Add the apps directory to Python path
sys.path.insert(0, str(Path(__file__).parent / "apps"))

from collector.collector import CollectorManager

def test_metrics_content():
    """Test what metrics are actually available."""
    print("Testing metrics content...")
    
    # Set environment for testing
    os.environ.update({
        "RUN_MODE": "service",
        "ENABLE_METRICS": "true",
        "METRICS_PORT": "8004",
        "ENABLE_SENTIMENT": "false",
        "FETCH_LIMIT": "1",
        "OUTPUT_PATH": "/tmp/test_reddit_sentiment.csv",
        "DEDUP_DB_PATH": "/tmp/test_dupes.db"
    })
    
    # Start collector in background thread
    manager = CollectorManager()
    
    def run_collector():
        try:
            manager.run_as_service()
        except Exception as e:
            print(f"Collector error: {e}")
    
    collector_thread = threading.Thread(target=run_collector)
    collector_thread.daemon = True
    collector_thread.start()
    
    # Wait for startup
    time.sleep(3)
    
    # Test metrics endpoint
    try:
        response = requests.get("http://localhost:8004/metrics", timeout=5)
        if response.status_code == 200:
            print("✅ Metrics endpoint working")
            print("\n--- Metrics Content ---")
            print(response.text[:1000])  # Print first 1000 chars
            print("\n--- End Metrics ---")
            
            # Check for expected metrics
            metrics_text = response.text
            expected_metrics = [
                "reddit_posts_fetched_total",
                "pipeline_status",
                "pipeline_build_info"
            ]
            
            print("\n--- Checking Expected Metrics ---")
            for metric in expected_metrics:
                if metric in metrics_text:
                    print(f"✅ Found: {metric}")
                else:
                    print(f"❌ Missing: {metric}")
        else:
            print(f"❌ Metrics endpoint returned {response.status_code}")
    
    except Exception as e:
        print(f"❌ Failed to connect to metrics: {e}")
    
    finally:
        # Signal shutdown
        manager.running = False

if __name__ == "__main__":
    test_metrics_content()
