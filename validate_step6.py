#!/usr/bin/env python3
"""
Step 6 Validation Script - Docker Containerization

Tests Docker build, container functionality, metrics endpoint,
and signal handling for production deployment.
"""

import json
import os
import requests
import subprocess
import sys
import time
from pathlib import Path

def run_command(cmd, check=True, capture_output=True):
    """Run shell command and return result."""
    print(f"Running: {cmd}")
    if isinstance(cmd, str):
        cmd = cmd.split()
    
    result = subprocess.run(cmd, capture_output=capture_output, text=True, check=False)
    
    if capture_output:
        print(f"STDOUT: {result.stdout}")
        if result.stderr:
            print(f"STDERR: {result.stderr}")
    
    if check and result.returncode != 0:
        print(f"Command failed with return code {result.returncode}")
        sys.exit(1)
    
    return result

def test_docker_build():
    """Test Docker image building."""
    print("\n=== Testing Docker Build ===")
    
    # Build the Docker image
    cmd = ["docker", "build", "-t", "reddit-finbert-collector:test", "."]
    result = run_command(cmd, capture_output=False)
    
    if result.returncode != 0:
        print("❌ Docker build failed")
        return False
    
    print("✅ Docker build successful")
    return True

def test_docker_run_once():
    """Test running container in CronJob mode (run once)."""
    print("\n=== Testing Docker Run Once (CronJob Mode) ===")
    
    # Create data directory
    data_dir = Path("/tmp/reddit_test_data")
    data_dir.mkdir(exist_ok=True)
    
    # Run container once
    cmd = [
        "docker", "run", "--rm",
        "-v", f"{data_dir}:/data",
        "-e", "RUN_MODE=once",
        "-e", "ENABLE_METRICS=true",
        "-e", "ENABLE_SENTIMENT=false",  # Disable to speed up test
        "-e", "FETCH_LIMIT=5",
        "reddit-finbert-collector:test"
    ]
    
    result = run_command(cmd, check=False, capture_output=False)
    
    if result.returncode != 0:
        print("❌ Container run failed")
        return False
    
    # Check if output file was created
    output_file = data_dir / "reddit_sentiment.csv"
    if output_file.exists():
        print(f"✅ Output file created: {output_file}")
        print(f"File size: {output_file.stat().st_size} bytes")
        return True
    else:
        print("❌ Output file not created")
        return False

def test_docker_metrics_service():
    """Test running container in service mode with metrics."""
    print("\n=== Testing Docker Service Mode with Metrics ===")
    
    container_name = "reddit-collector-test"
    
    try:
        # Remove any existing container
        run_command(f"docker rm -f {container_name}", check=False)
        
        # Start container in service mode
        cmd = [
            "docker", "run", "-d",
            "--name", container_name,
            "-p", "8000:8000",
            "-e", "RUN_MODE=service",
            "-e", "ENABLE_METRICS=true",
            "-e", "ENABLE_SENTIMENT=false",
            "reddit-finbert-collector:test"
        ]
        
        result = run_command(cmd)
        container_id = result.stdout.strip()
        print(f"Container started: {container_id[:12]}")
        
        # Wait for container to start
        time.sleep(5)
        
        # Check if container is running
        result = run_command(f"docker ps --filter name={container_name} --format json", check=False)
        if result.returncode != 0:
            print("❌ Container not running")
            return False
        
        # Test metrics endpoint
        try:
            response = requests.get("http://localhost:8000/metrics", timeout=10)
            if response.status_code == 200:
                print("✅ Metrics endpoint accessible")
                
                # Check for key metrics
                metrics_text = response.text
                expected_metrics = [
                    "reddit_posts_fetched_total",
                    "pipeline_status",
                    "pipeline_build_info"
                ]
                
                for metric in expected_metrics:
                    if metric in metrics_text:
                        print(f"✅ Found metric: {metric}")
                    else:
                        print(f"❌ Missing metric: {metric}")
                        return False
                
                return True
            else:
                print(f"❌ Metrics endpoint returned {response.status_code}")
                return False
                
        except requests.RequestException as e:
            print(f"❌ Failed to connect to metrics endpoint: {e}")
            return False
    
    finally:
        # Clean up container
        run_command(f"docker rm -f {container_name}", check=False)

def test_docker_health_check():
    """Test Docker health check functionality."""
    print("\n=== Testing Docker Health Check ===")
    
    container_name = "reddit-collector-health-test"
    
    try:
        # Remove any existing container
        run_command(f"docker rm -f {container_name}", check=False)
        
        # Start container with health check
        cmd = [
            "docker", "run", "-d",
            "--name", container_name,
            "-p", "8001:8000",
            "-e", "RUN_MODE=service",
            "-e", "ENABLE_METRICS=true",
            "reddit-finbert-collector:test"
        ]
        
        result = run_command(cmd)
        print(f"Container started: {result.stdout.strip()[:12]}")
        
        # Wait for health check to stabilize
        time.sleep(30)
        
        # Check health status
        result = run_command(f"docker inspect {container_name} --format='{{{{.State.Health.Status}}}}'")
        health_status = result.stdout.strip().replace("'", "")
        
        if health_status == "healthy":
            print("✅ Container health check passed")
            return True
        else:
            print(f"❌ Container health check failed: {health_status}")
            
            # Show health logs
            result = run_command(f"docker inspect {container_name}", check=False)
            print("Container inspect output for debugging...")
            return False
    
    finally:
        # Clean up container
        run_command(f"docker rm -f {container_name}", check=False)

def test_docker_compose():
    """Test docker-compose functionality."""
    print("\n=== Testing Docker Compose ===")
    
    try:
        # Check if docker-compose is available
        run_command("docker-compose --version")
        
        # Start services
        result = run_command("docker-compose up -d reddit-collector", check=False)
        if result.returncode != 0:
            print("❌ Docker compose up failed")
            return False
        
        # Wait for services to start
        time.sleep(10)
        
        # Test the service
        try:
            response = requests.get("http://localhost:8000/metrics", timeout=10)
            if response.status_code == 200:
                print("✅ Docker Compose service accessible")
                return True
            else:
                print(f"❌ Service returned {response.status_code}")
                return False
        except requests.RequestException as e:
            print(f"❌ Failed to connect to service: {e}")
            return False
    
    except subprocess.CalledProcessError:
        print("⚠️  docker-compose not available, skipping test")
        return True
    
    finally:
        # Clean up
        run_command("docker-compose down", check=False)

def test_security_features():
    """Test security features of the Docker container."""
    print("\n=== Testing Security Features ===")
    
    container_name = "reddit-collector-security-test"
    
    try:
        # Start container
        cmd = [
            "docker", "run", "-d",
            "--name", container_name,
            "-e", "RUN_MODE=service",
            "reddit-finbert-collector:test"
        ]
        
        run_command(cmd)
        
        # Check if running as non-root user
        result = run_command(f"docker exec {container_name} whoami")
        user = result.stdout.strip()
        
        if user == "collector":
            print("✅ Container running as non-root user")
            return True
        else:
            print(f"❌ Container running as {user} (should be collector)")
            return False
    
    finally:
        run_command(f"docker rm -f {container_name}", check=False)

def main():
    """Run all Docker validation tests."""
    print("🐳 Starting Step 6 Docker Validation Tests")
    print("=" * 50)
    
    # Change to project directory
    project_dir = Path(__file__).parent
    os.chdir(project_dir)
    
    tests = [
        ("Docker Build", test_docker_build),
        ("Docker Run Once", test_docker_run_once),
        ("Docker Metrics Service", test_docker_metrics_service),
        ("Docker Health Check", test_docker_health_check),
        ("Docker Compose", test_docker_compose),
        ("Security Features", test_security_features),
    ]
    
    results = {}
    
    for test_name, test_func in tests:
        try:
            results[test_name] = test_func()
        except Exception as e:
            print(f"❌ Test {test_name} failed with exception: {e}")
            results[test_name] = False
    
    # Summary
    print("\n" + "=" * 50)
    print("🐳 Step 6 Docker Validation Summary")
    print("=" * 50)
    
    passed = 0
    total = len(tests)
    
    for test_name, passed_test in results.items():
        status = "✅ PASS" if passed_test else "❌ FAIL"
        print(f"{test_name:<25} {status}")
        if passed_test:
            passed += 1
    
    print(f"\nTests passed: {passed}/{total}")
    
    if passed == total:
        print("🎉 All Docker tests passed! Step 6 completed successfully.")
        return True
    else:
        print("❌ Some tests failed. Please fix issues before proceeding.")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
