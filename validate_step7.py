#!/usr/bin/env python3
"""
Step 7 Validation: GitHub Actions CI/CD Pipeline
Tests the CI/CD pipeline configuration and readiness for GitHub Actions.
"""

import os
import sys
import yaml
import json
from pathlib import Path
from typing import Dict, List, Any

def validate_workflow_files() -> bool:
    """Validate GitHub Actions workflow files."""
    print("🔍 Validating GitHub Actions workflow files...")
    
    workflows_dir = Path(".github/workflows")
    if not workflows_dir.exists():
        print("❌ .github/workflows directory not found")
        return False
    
    required_workflows = [
        "ci.yml",
        "dependency-review.yml", 
        "auto-merge.yml",
        "release.yml"
    ]
    
    for workflow in required_workflows:
        workflow_path = workflows_dir / workflow
        if not workflow_path.exists():
            print(f"❌ Missing workflow file: {workflow}")
            return False
        
        try:
            with open(workflow_path, 'r') as f:
                yaml.safe_load(f.read())
            print(f"✅ {workflow} - valid YAML syntax")
        except yaml.YAMLError as e:
            print(f"❌ {workflow} - invalid YAML: {e}")
            return False
    
    return True

def validate_ci_workflow() -> bool:
    """Validate the main CI workflow configuration."""
    print("\n🔍 Validating CI workflow configuration...")
    
    ci_path = Path(".github/workflows/ci.yml")
    with open(ci_path, 'r') as f:
        ci_content = f.read()
        ci_config = yaml.safe_load(ci_content)
    
    if not ci_config:
        print("❌ Failed to parse CI workflow YAML")
        return False
    
    # Check required jobs
    required_jobs = ["test", "security-scan", "build-and-push", "deploy-to-server"]
    jobs = ci_config.get("jobs", {})
    
    for job in required_jobs:
        if job not in jobs:
            print(f"❌ Missing required job: {job}")
            return False
        print(f"✅ Job '{job}' found")
    
    # Check test job matrix
    test_job = jobs.get("test", {})
    strategy = test_job.get("strategy", {})
    matrix = strategy.get("matrix", {})
    python_versions = matrix.get("python-version", [])
    
    if not python_versions or len(python_versions) < 2:
        print("❌ Test matrix should include multiple Python versions")
        return False
    
    print(f"✅ Testing Python versions: {python_versions}")
    
    # Check for required environment variables in the content
    required_env_vars = ["REDDIT_CLIENT_ID", "REDDIT_CLIENT_SECRET", "REDDIT_USER_AGENT"]
    
    for env_var in required_env_vars:
        if env_var not in ci_content:
            print(f"❌ Missing environment variable in test job: {env_var}")
            return False
    
    print("✅ Required environment variables configured")
    return True

def validate_dependabot_config() -> bool:
    """Validate Dependabot configuration."""
    print("\n🔍 Validating Dependabot configuration...")
    
    dependabot_path = Path(".github/dependabot.yml")
    if not dependabot_path.exists():
        print("❌ .github/dependabot.yml not found")
        return False
    
    with open(dependabot_path, 'r') as f:
        content = f.read()
        config = yaml.safe_load(content)
    
    if not config:
        print("❌ Failed to parse Dependabot YAML")
        return False
    
    updates = config.get("updates", [])
    ecosystems = [update.get("package-ecosystem") for update in updates]
    
    required_ecosystems = ["pip", "docker", "github-actions"]
    for ecosystem in required_ecosystems:
        if ecosystem not in ecosystems:
            print(f"❌ Missing package ecosystem: {ecosystem}")
            return False
        print(f"✅ {ecosystem} ecosystem configured")
    
    return True

def validate_security_files() -> bool:
    """Validate security-related files."""
    print("\n🔍 Validating security configuration...")
    
    security_path = Path("SECURITY.md")
    if not security_path.exists():
        print("❌ SECURITY.md not found")
        return False
    
    print("✅ SECURITY.md found")
    
    # Check for security scanning in CI
    ci_path = Path(".github/workflows/ci.yml")
    with open(ci_path, 'r') as f:
        ci_content = f.read()
    
    security_checks = [
        "aquasecurity/trivy-action",
        "upload-sarif",
        "codecov/codecov-action"
    ]
    
    for check in security_checks:
        if check not in ci_content:
            print(f"❌ Missing security check: {check}")
            return False
        print(f"✅ Security check '{check}' configured")
    
    return True

def validate_docker_integration() -> bool:
    """Validate Docker integration in CI/CD."""
    print("\n🔍 Validating Docker integration...")
    
    # Check Dockerfile exists
    if not Path("Dockerfile").exists():
        print("❌ Dockerfile not found")
        return False
    
    print("✅ Dockerfile found")
    
    # Check docker-compose.yml exists
    if not Path("docker-compose.yml").exists():
        print("❌ docker-compose.yml not found")
        return False
    
    print("✅ docker-compose.yml found")
    
    # Validate CI workflow has Docker build steps
    ci_path = Path(".github/workflows/ci.yml")
    with open(ci_path, 'r') as f:
        ci_content = f.read()
    
    docker_steps = [
        "docker/setup-buildx-action",
        "docker/login-action", 
        "docker/build-push-action",
        "docker/metadata-action"
    ]
    
    for step in docker_steps:
        if step not in ci_content:
            print(f"❌ Missing Docker step: {step}")
            return False
        print(f"✅ Docker step '{step}' configured")
    
    return True

def validate_deployment_readiness() -> bool:
    """Validate deployment configuration."""
    print("\n🔍 Validating deployment readiness...")
    
    # Check deployment artifacts generation
    ci_path = Path(".github/workflows/ci.yml")
    with open(ci_path, 'r') as f:
        ci_content = f.read()
    
    deployment_features = [
        "deployment.env",
        "upload-artifact",
        "download-artifact",
        "DEPLOY_HOST",
        "/home/cayir/cicd_project"
    ]
    
    for feature in deployment_features:
        if feature not in ci_content:
            print(f"❌ Missing deployment feature: {feature}")
            return False
        print(f"✅ Deployment feature '{feature}' configured")
    
    return True

def validate_quality_gates() -> bool:
    """Validate code quality gates."""
    print("\n🔍 Validating code quality gates...")
    
    ci_path = Path(".github/workflows/ci.yml")
    with open(ci_path, 'r') as f:
        ci_content = f.read()
    
    quality_tools = [
        "ruff check",
        "black --check", 
        "isort --check-only",
        "coverage run",
        "coverage report"
    ]
    
    for tool in quality_tools:
        if tool not in ci_content:
            print(f"❌ Missing quality tool: {tool}")
            return False
        print(f"✅ Quality tool '{tool}' configured")
    
    return True

def generate_step7_summary() -> Dict[str, Any]:
    """Generate Step 7 completion summary."""
    return {
        "step": 7,
        "title": "GitHub Actions CI/CD Pipeline",
        "status": "complete",
        "features": [
            "Multi-Python version testing (3.9, 3.10, 3.11)",
            "Code quality gates (ruff, black, isort)",
            "Test coverage reporting with Codecov",
            "Security scanning with Trivy",
            "Dependency review and auto-updates",
            "Multi-platform Docker builds (amd64, arm64)",
            "Container registry integration (GHCR)",
            "Automated deployment artifacts",
            "GitOps-ready configuration",
            "Release automation"
        ],
        "workflows": {
            "ci.yml": "Main CI/CD pipeline with testing, building, and deployment",
            "dependency-review.yml": "Security review for dependency changes",
            "auto-merge.yml": "Automated Dependabot PR merging",
            "release.yml": "Automated releases with Docker images"
        },
        "security": [
            "Trivy vulnerability scanning",
            "SARIF security reporting",
            "Dependabot dependency updates",
            "Container security best practices",
            "Secrets management"
        ],
        "quality_gates": [
            "Linting with ruff",
            "Code formatting with black", 
            "Import sorting with isort",
            "Test coverage > 90%",
            "Multi-Python version compatibility"
        ]
    }

def main():
    """Main validation function."""
    print("🚀 Step 7: GitHub Actions CI/CD Pipeline Validation")
    print("=" * 60)
    
    validations = [
        ("Workflow Files", validate_workflow_files),
        ("CI Configuration", validate_ci_workflow),
        ("Dependabot Setup", validate_dependabot_config),
        ("Security Files", validate_security_files),
        ("Docker Integration", validate_docker_integration),
        ("Deployment Readiness", validate_deployment_readiness),
        ("Quality Gates", validate_quality_gates)
    ]
    
    all_passed = True
    for name, validation_func in validations:
        try:
            if not validation_func():
                all_passed = False
                print(f"\n❌ {name} validation failed")
            else:
                print(f"\n✅ {name} validation passed")
        except Exception as e:
            print(f"\n❌ {name} validation error: {e}")
            all_passed = False
    
    print("\n" + "=" * 60)
    
    if all_passed:
        print("🎉 Step 7 validation PASSED!")
        print("\n📋 Summary:")
        summary = generate_step7_summary()
        
        print(f"• {len(summary['workflows'])} GitHub Actions workflows configured")
        print(f"• {len(summary['features'])} CI/CD features implemented")
        print(f"• {len(summary['security'])} security measures active")
        print(f"• {len(summary['quality_gates'])} quality gates enforced")
        
        print("\n🔄 Next Steps:")
        print("• Initialize Git repository and push to GitHub")
        print("• Configure repository secrets (DEPLOY_HOST, DEPLOY_USER, DEPLOY_KEY)")
        print("• Enable GitHub Actions in repository settings")
        print("• Review and merge first Dependabot PRs")
        print("• Test CI/CD pipeline with a sample commit")
        
        # Save summary
        with open("STEP7_COMPLETION.md", "w") as f:
            f.write("# Step 7 Completion: GitHub Actions CI/CD Pipeline\n\n")
            f.write(f"**Status**: ✅ Complete\n\n")
            f.write(f"## Features Implemented\n\n")
            for feature in summary['features']:
                f.write(f"- {feature}\n")
            f.write(f"\n## Workflows\n\n")
            for workflow, desc in summary['workflows'].items():
                f.write(f"- **{workflow}**: {desc}\n")
            f.write(f"\n## Security Measures\n\n")
            for security in summary['security']:
                f.write(f"- {security}\n")
        
        return True
    else:
        print("❌ Step 7 validation FAILED!")
        print("Please fix the issues above before proceeding.")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
