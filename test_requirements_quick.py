#!/usr/bin/env python3
"""
Quick test to verify CPU-only requirements work.
"""

import subprocess
import tempfile
import os

def test_requirements_install():
    """Test installing our requirements in a temporary environment."""
    print("🧪 Testing CPU-only requirements installation...")
    
    # Create a temporary requirements file with just the problematic packages
    test_requirements = """
torch==2.2.0+cpu
transformers==4.30.2
"""
    
    with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
        f.write(test_requirements)
        temp_req_file = f.name
    
    try:
        print(f"📋 Testing requirements: {test_requirements.strip()}")
        
        # Test what pip would install (dry run)
        result = subprocess.run([
            "pip", "install", "--dry-run", 
            "-r", temp_req_file,
            "-f", "https://download.pytorch.org/whl/torch_stable.html"
        ], capture_output=True, text=True, timeout=60)
        
        if result.returncode == 0:
            print("✅ CPU-only requirements look good!")
            
            # Check what would be installed
            output = result.stdout + result.stderr
            if "nvidia" in output.lower() or "cuda" in output.lower():
                print("❌ Still trying to install CUDA packages:")
                print(output)
                return False
            else:
                print("✅ No CUDA packages detected in dry run")
                return True
        else:
            print("❌ Requirements test failed:")
            print(result.stderr)
            return False
            
    except subprocess.TimeoutExpired:
        print("❌ Requirements test timed out")
        return False
    except Exception as e:
        print(f"❌ Requirements test error: {e}")
        return False
    finally:
        os.unlink(temp_req_file)

if __name__ == "__main__":
    test_requirements_install()
