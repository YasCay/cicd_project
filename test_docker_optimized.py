#!/usr/bin/env python3
"""
Step 6 Docker Build Test: CPU-Optimized Build Validation

Tests the optimized Docker build process with CPU-only dependencies
to ensure fast build times without GPU/CUDA bloat.
"""

import subprocess
import time
import sys
import os
import tempfile
from pathlib import Path


def run_command(cmd, timeout=300):
    """Run a command with timeout and return result."""
    print(f"🔧 Running: {cmd}")
    start_time = time.time()
    
    try:
        result = subprocess.run(
            cmd, 
            shell=True, 
            capture_output=True, 
            text=True,
            timeout=timeout
        )
        duration = time.time() - start_time
        print(f"⏱️  Completed in {duration:.1f}s")
        
        if result.returncode != 0:
            print(f"❌ Command failed (exit code {result.returncode})")
            print(f"STDOUT: {result.stdout}")
            print(f"STDERR: {result.stderr}")
            return False, result.stdout, result.stderr
        
        return True, result.stdout, result.stderr
    
    except subprocess.TimeoutExpired:
        print(f"⏰ Command timed out after {timeout}s")
        return False, "", "Command timed out"


def check_docker_available():
    """Check if Docker is available."""
    print("🐳 Checking Docker availability...")
    success, stdout, stderr = run_command("docker --version")
    if success:
        print(f"✅ Docker available: {stdout.strip()}")
        return True
    else:
        print("❌ Docker not available")
        return False


def build_test_requirements():
    """Test if requirements can be installed quickly."""
    print("\n📦 Testing CPU-optimized requirements installation...")
    
    with tempfile.TemporaryDirectory() as temp_dir:
        venv_path = os.path.join(temp_dir, "test_venv")
        
        # Create virtual environment
        success, _, _ = run_command(f"python -m venv {venv_path}")
        if not success:
            return False
        
        # Test base requirements (should be fast)
        print("📦 Testing base requirements...")
        pip_cmd = f"{venv_path}/bin/pip install --no-cache-dir -r apps/collector/requirements-base.txt"
        success, stdout, stderr = run_command(pip_cmd, timeout=120)
        
        if not success:
            print("❌ Base requirements installation failed")
            return False
        
        print("✅ Base requirements installed successfully")
        
        # Test ML requirements (CPU-only)
        print("🧠 Testing ML requirements (CPU-only)...")
        ml_cmd = f"{venv_path}/bin/pip install --no-cache-dir -r apps/collector/requirements-ml.txt"
        success, stdout, stderr = run_command(ml_cmd, timeout=180)
        
        if not success:
            print("❌ ML requirements installation failed")
            print(f"Error: {stderr}")
            return False
        
        print("✅ ML requirements (CPU-only) installed successfully")
        
        # Verify no CUDA packages
        print("🔍 Verifying no CUDA packages installed...")
        list_cmd = f"{venv_path}/bin/pip list | grep -i cuda || true"
        success, stdout, stderr = run_command(list_cmd)
        
        if stdout.strip():
            print(f"⚠️  Found CUDA packages: {stdout.strip()}")
            return False
        
        print("✅ No CUDA packages found - CPU-only verified")
        return True


def test_docker_build():
    """Test Docker build process."""
    print("\n🏗️  Testing Docker build process...")
    
    # Build the image
    build_cmd = "docker build -t reddit-sentiment:test ."
    print(f"🔨 Building Docker image...")
    
    success, stdout, stderr = run_command(build_cmd, timeout=600)  # 10 minute timeout
    
    if not success:
        print("❌ Docker build failed")
        print(f"Build output: {stdout}")
        print(f"Build errors: {stderr}")
        return False
    
    print("✅ Docker build completed successfully")
    
    # Test image size
    size_cmd = "docker images reddit-sentiment:test --format 'table {{.Size}}'"
    success, stdout, stderr = run_command(size_cmd)
    
    if success:
        size = stdout.strip().split('\n')[-1] if stdout.strip() else "Unknown"
        print(f"📏 Image size: {size}")
    
    return True


def test_container_run():
    """Test running the container."""
    print("\n🚀 Testing container execution...")
    
    # Create temporary data directory
    with tempfile.TemporaryDirectory() as temp_dir:
        data_dir = os.path.join(temp_dir, "data")
        os.makedirs(data_dir)
        
        # Run container with dummy data
        run_cmd = f"""docker run --rm \
            -v {data_dir}:/data \
            -e ENABLE_SENTIMENT=false \
            -e ENABLE_METRICS=true \
            -e OUTPUT_PATH=/data/test_output.csv \
            reddit-sentiment:test"""
        
        print("🏃 Running container...")
        success, stdout, stderr = run_command(run_cmd, timeout=60)
        
        if not success:
            print("❌ Container run failed")
            print(f"Container output: {stdout}")
            print(f"Container errors: {stderr}")
            return False
        
        print("✅ Container executed successfully")
        
        # Check if output file was created
        output_file = os.path.join(data_dir, "test_output.csv")
        if os.path.exists(output_file):
            print(f"✅ Output file created: {os.path.getsize(output_file)} bytes")
            return True
        else:
            print("❌ Output file not created")
            return False


def cleanup_docker_images():
    """Clean up test Docker images."""
    print("\n🧹 Cleaning up test images...")
    run_command("docker rmi reddit-sentiment:test 2>/dev/null || true")


def main():
    """Run Step 6 Docker build tests."""
    print("🚀 Step 6 Docker Build Test: CPU-Optimized Build")
    print("=" * 60)
    
    # Change to project directory
    os.chdir("/home/yasar/cicd_project")
    
    tests = [
        ("Docker Availability", check_docker_available),
        ("CPU-Only Requirements", build_test_requirements),
        ("Docker Build", test_docker_build),
        ("Container Execution", test_container_run),
    ]
    
    results = {}
    
    for test_name, test_func in tests:
        print(f"\n{'='*20} {test_name} {'='*20}")
        try:
            results[test_name] = test_func()
        except Exception as e:
            print(f"💥 {test_name} failed with exception: {e}")
            results[test_name] = False
    
    # Cleanup
    cleanup_docker_images()
    
    # Results summary
    print("\n🎯 STEP 6 TEST RESULTS")
    print("=" * 60)
    
    all_passed = True
    for test_name, passed in results.items():
        status = "✅ PASSED" if passed else "❌ FAILED"
        print(f"{test_name:30} {status}")
        if not passed:
            all_passed = False
    
    print("=" * 60)
    
    if all_passed:
        print("🎉 Step 6 - CPU-Optimized Docker Build: PASSED")
        print("✅ Fast build times achieved")
        print("✅ No CUDA dependencies bloat")
        print("✅ Container runs successfully")
        return True
    else:
        print("💥 Step 6 - CPU-Optimized Docker Build: FAILED")
        return False


if __name__ == "__main__":
    try:
        success = main()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n⏹️  Test interrupted by user")
        cleanup_docker_images()
        sys.exit(1)
    except Exception as e:
        print(f"\n💥 Unexpected error: {e}")
        cleanup_docker_images()
        sys.exit(1)
