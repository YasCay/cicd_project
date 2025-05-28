#!/usr/bin/env python3
"""
Test the simplified Docker approach for CPU-only builds.
"""

import subprocess
import time
import sys
from pathlib import Path

def test_simple_docker_build():
    """Test the simplified Docker build."""
    print("🚀 Testing Simplified CPU-Only Docker Build")
    print("=" * 50)
    
    try:
        # Build with the simple Dockerfile
        print("🔨 Building Docker image with simplified approach...")
        start_time = time.time()
        
        result = subprocess.run([
            "docker", "build", 
            "-f", "Dockerfile.simple",
            "-t", "reddit-finbert-simple",
            "."
        ], capture_output=True, text=True, timeout=300)  # 5 minute timeout
        
        build_duration = time.time() - start_time
        
        if result.returncode == 0:
            print(f"✅ Simple Docker build successful in {build_duration:.1f}s")
            
            # Test the image works
            print("🧪 Testing container functionality...")
            test_result = subprocess.run([
                "docker", "run", "--rm",
                "-e", "ENABLE_SENTIMENT=false",
                "-e", "ENABLE_METRICS=false", 
                "reddit-finbert-simple",
                "python", "-c", "print('✅ Container works!')"
            ], capture_output=True, text=True, timeout=30)
            
            if test_result.returncode == 0:
                print("✅ Container test passed!")
                print(f"   Output: {test_result.stdout.strip()}")
                
                # Test imports
                print("🔍 Testing Python imports...")
                import_test = subprocess.run([
                    "docker", "run", "--rm",
                    "reddit-finbert-simple",
                    "python", "-c", 
                    "import torch; import transformers; import pandas; print(f'✅ PyTorch: {torch.__version__}, Transformers: {transformers.__version__}')"
                ], capture_output=True, text=True, timeout=30)
                
                if import_test.returncode == 0:
                    print("✅ All imports working!")
                    print(f"   {import_test.stdout.strip()}")
                    return True
                else:
                    print("❌ Import test failed:")
                    print(import_test.stderr)
                    return False
            else:
                print("❌ Container test failed:")
                print(test_result.stderr)
                return False
        else:
            print(f"❌ Docker build failed after {build_duration:.1f}s")
            print("Build errors:")
            print(result.stderr)
            return False
            
    except subprocess.TimeoutExpired:
        print("❌ Build timed out - still too slow!")
        return False
    except Exception as e:
        print(f"❌ Build error: {e}")
        return False

def main():
    """Run the simplified Docker test."""
    if test_simple_docker_build():
        print("\n🎉 SUCCESS: Simplified Docker build working!")
        print("✅ Fast CPU-only build completed")
        print("✅ Container functionality verified")
        print("🚀 Ready to proceed with Step 6!")
        return True
    else:
        print("\n💥 FAILED: Docker build issues remain")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
