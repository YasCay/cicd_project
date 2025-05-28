#!/usr/bin/env python3
"""
Test Docker collector functionality directly (without building image).
"""

import os
import sys
import tempfile
import time
from pathlib import Path

# Add the apps directory to Python path
sys.path.insert(0, str(Path(__file__).parent / "apps"))

from collector.collector import CollectorManager
from collector.metrics import get_metrics
import threading
import requests

def test_collector_service_mode():
    """Test collector in service mode with metrics."""
    print("Testing collector service mode...")
    
    # Set environment for testing
    os.environ.update({
        "RUN_MODE": "service",
        "ENABLE_METRICS": "true",
        "METRICS_PORT": "8002",
        "ENABLE_SENTIMENT": "false",
        "FETCH_LIMIT": "3",
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
        response = requests.get("http://localhost:8002/metrics", timeout=5)
        if response.status_code == 200:
            print("✅ Metrics endpoint working")
            
            # Check for expected metrics
            metrics_text = response.text
            if "reddit_posts_fetched_total" in metrics_text:
                print("✅ Metrics contain expected data")
                return True
            else:
                print("❌ Missing expected metrics")
                return False
        else:
            print(f"❌ Metrics endpoint returned {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Failed to connect to metrics: {e}")
        return False
    
    finally:
        # Signal shutdown
        manager.running = False

def test_collector_once_mode():
    """Test collector in once mode (CronJob)."""
    print("Testing collector once mode...")
    
    with tempfile.TemporaryDirectory() as temp_dir:
        # Set environment for testing
        os.environ.update({
            "RUN_MODE": "once",
            "ENABLE_METRICS": "true",
            "METRICS_PORT": "8003",
            "ENABLE_SENTIMENT": "false",
            "FETCH_LIMIT": "2",
            "OUTPUT_PATH": f"{temp_dir}/reddit_sentiment.csv",
            "DEDUP_DB_PATH": f"{temp_dir}/dupes.db"
        })
        
        try:
            manager = CollectorManager()
            manager.run_once()
            
            # Check if output file was created
            output_file = Path(temp_dir) / "reddit_sentiment.csv"
            if output_file.exists() and output_file.stat().st_size > 0:
                print("✅ Output file created successfully")
                return True
            else:
                print("❌ Output file not created or empty")
                return False
                
        except Exception as e:
            print(f"❌ Collector failed: {e}")
            return False

def main():
    """Run Docker preparation tests."""
    print("🧪 Testing Docker-ready collector functionality")
    print("=" * 50)
    
    tests = [
        ("Collector Once Mode", test_collector_once_mode),
        ("Collector Service Mode", test_collector_service_mode),
    ]
    
    results = {}
    
    for test_name, test_func in tests:
        print(f"\n--- {test_name} ---")
        try:
            results[test_name] = test_func()
        except Exception as e:
            print(f"❌ Test failed with exception: {e}")
            results[test_name] = False
    
    # Summary
    print("\n" + "=" * 50)
    print("Summary")
    print("=" * 50)
    
    passed = sum(results.values())
    total = len(tests)
    
    for test_name, passed_test in results.items():
        status = "✅ PASS" if passed_test else "❌ FAIL"
        print(f"{test_name:<25} {status}")
    
    print(f"\nTests passed: {passed}/{total}")
    
    if passed == total:
        print("✅ All tests passed! Ready for Docker build.")
        return True
    else:
        print("❌ Some tests failed.")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
