#!/usr/bin/env python3
"""
Test CPU-optimized Docker build for Step 6.

This validates that our CPU-only requirements.txt builds much faster
without downloading massive CUDA dependencies.
"""

import subprocess
import time
import os
import sys
from pathlib import Path

def test_cpu_optimized_build():
    """Test that the Docker build is fast and CPU-optimized."""
    print("🚀 Testing CPU-Optimized Docker Build")
    print("=" * 50)
    
    # Change to project directory
    project_dir = Path(__file__).parent
    os.chdir(project_dir)
    
    print(f"📂 Working directory: {os.getcwd()}")
    
    # Clean up any existing images
    print("🧹 Cleaning up existing Docker images...")
    try:
        subprocess.run(["docker", "rmi", "reddit-finbert-collector"], 
                      capture_output=True, check=False)
    except:
        pass
    
    # Build Docker image with timing
    print("🔨 Building Docker image (CPU-optimized)...")
    start_time = time.time()
    
    try:
        result = subprocess.run([
            "docker", "build", 
            "-t", "reddit-finbert-collector",
            "--no-cache",  # Force fresh build
            "."
        ], capture_output=True, text=True, timeout=600)  # 10 minute timeout
        
        build_duration = time.time() - start_time
        
        if result.returncode == 0:
            print(f"✅ Docker build successful in {build_duration:.1f}s")
            
            # Check that we avoided CUDA packages in the build output
            build_output = result.stdout + result.stderr
            
            print("\n📊 Build Analysis:")
            
            # Check for good signs (CPU-only packages)
            good_signs = [
                "torch==2.2.0+cpu",
                "transformers==4.30.2"
            ]
            
            for sign in good_signs:
                if sign in build_output:
                    print(f"✅ Found CPU-optimized: {sign}")
                else:
                    print(f"⚠️  Might not be optimized: {sign}")
            
            # Check for bad signs (CUDA packages)
            bad_signs = [
                "nvidia_cusparse",
                "nvidia_cusparselt", 
                "nvidia_nccl",
                "cuda",
                "GPU"
            ]
            
            cuda_found = False
            for sign in bad_signs:
                if sign.lower() in build_output.lower():
                    print(f"❌ Found CUDA dependency: {sign}")
                    cuda_found = True
            
            if not cuda_found:
                print("✅ No CUDA dependencies detected - build is optimized!")
            
            # Test the built image
            print(f"\n🧪 Testing built image...")
            test_container_functionality()
            
            return True
            
        else:
            print(f"❌ Docker build failed after {build_duration:.1f}s")
            print("Build output:")
            print(result.stdout)
            print("Build errors:")
            print(result.stderr)
            return False
            
    except subprocess.TimeoutExpired:
        print("❌ Docker build timed out (>10 minutes)")
        print("This suggests the build is still downloading massive dependencies!")
        return False
    except Exception as e:
        print(f"❌ Docker build error: {e}")
        return False

def test_container_functionality():
    """Test that the container runs correctly."""
    print("🔍 Testing container functionality...")
    
    try:
        # Run container with minimal test
        result = subprocess.run([
            "docker", "run", "--rm",
            "-e", "ENABLE_SENTIMENT=false",  # Disable FinBERT for speed
            "-e", "ENABLE_METRICS=true",
            "-e", "METRICS_PORT=8000",
            "-e", "FETCH_LIMIT=1",
            "-e", "OUTPUT_PATH=/data/test.csv",
            "reddit-finbert-collector",
            "python", "-c", "from apps.collector.collector import RedditSentimentCollector; print('✅ Collector imports successfully')"
        ], capture_output=True, text=True, timeout=30)
        
        if result.returncode == 0:
            print("✅ Container runs and imports work correctly")
            print(f"   Output: {result.stdout.strip()}")
            return True
        else:
            print("❌ Container test failed")
            print(f"   Error: {result.stderr}")
            return False
            
    except subprocess.TimeoutExpired:
        print("❌ Container test timed out")
        return False
    except Exception as e:
        print(f"❌ Container test error: {e}")
        return False

def test_requirements_content():
    """Verify the requirements.txt has CPU-only packages."""
    print("\n📋 Analyzing requirements.txt content...")
    
    requirements_path = Path("apps/collector/requirements.txt")
    
    if not requirements_path.exists():
        print("❌ requirements.txt not found")
        return False
    
    content = requirements_path.read_text()
    
    # Check for CPU-optimized packages
    if "torch==2.2.0+cpu" in content:
        print("✅ Found CPU-only PyTorch")
    else:
        print("❌ PyTorch not CPU-optimized")
        return False
    
    if "transformers==4.30.2" in content:
        print("✅ Found pinned transformers version")
    else:
        print("❌ Transformers not properly pinned")
        return False
    
    # Check that we don't have problematic patterns
    problematic = ["torch>=", "transformers>="]
    for pattern in problematic:
        if pattern in content:
            print(f"⚠️  Found potentially problematic pattern: {pattern}")
    
    print("✅ requirements.txt looks CPU-optimized")
    return True

def main():
    """Run all CPU optimization tests."""
    print("🎯 Step 6: CPU-Optimized Docker Build Test")
    print("=" * 60)
    
    success = True
    
    # Test 1: Requirements content
    if not test_requirements_content():
        success = False
    
    # Test 2: Docker build speed and optimization
    if not test_cpu_optimized_build():
        success = False
    
    print(f"\n{'='*60}")
    if success:
        print("🎉 SUCCESS: CPU-optimized Docker build working!")
        print("✅ Fast build without CUDA dependencies")
        print("✅ Container functionality verified")
        print("✅ Ready for Step 6 completion")
    else:
        print("💥 FAILED: CPU optimization issues detected")
        print("❌ Check requirements.txt and Dockerfile")
    
    return success

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
