#!/usr/bin/env python3
"""
Simple Step 7 validation for GitHub Actions CI/CD Pipeline
"""

import os
import sys
from pathlib import Path

def check_file_exists(filepath, description):
    """Check if a file exists."""
    if Path(filepath).exists():
        print(f"✅ {description}: {filepath}")
        return True
    else:
        print(f"❌ {description}: {filepath} NOT FOUND")
        return False

def main():
    print("🚀 Step 7: GitHub Actions CI/CD Pipeline Validation")
    print("=" * 60)
    
    # Check required files
    files_to_check = [
        (".github/workflows/ci.yml", "Main CI/CD workflow"),
        (".github/workflows/dependency-review.yml", "Dependency review workflow"),
        (".github/workflows/auto-merge.yml", "Auto-merge workflow"),
        (".github/workflows/release.yml", "Release workflow"),
        (".github/dependabot.yml", "Dependabot configuration"),
        ("SECURITY.md", "Security policy"),
        ("Dockerfile", "Docker container definition"),
        ("docker-compose.yml", "Docker compose configuration")
    ]
    
    all_files_exist = True
    for filepath, description in files_to_check:
        if not check_file_exists(filepath, description):
            all_files_exist = False
    
    print("\n" + "=" * 60)
    
    if all_files_exist:
        print("🎉 Step 7 file validation PASSED!")
        print("\n📋 Summary:")
        print("• 4 GitHub Actions workflows configured")
        print("• Dependabot auto-updates enabled")
        print("• Security policy documented")
        print("• Docker containerization ready")
        
        print("\n🔄 Next Steps:")
        print("• Initialize Git repository and push to GitHub")
        print("• Configure repository secrets (DEPLOY_HOST, DEPLOY_USER, DEPLOY_KEY)")
        print("• Enable GitHub Actions in repository settings")
        print("• Test CI/CD pipeline with a sample commit")
        
        return True
    else:
        print("❌ Step 7 validation FAILED!")
        print("Please fix the missing files above.")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
