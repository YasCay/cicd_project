#!/usr/bin/env python3
"""
Simplified Step 8 Validation Script - Kubernetes Helm Charts & GitOps Integration

This script validates the successful completion of Step 8.
"""

import os
import sys
import json
import yaml
from pathlib import Path


def validate_file_exists(file_path, description):
    """Validate that a file exists"""
    path = Path(file_path)
    exists = path.exists()
    status = "✅ PASS" if exists else "❌ FAIL"
    print(f"{status}: {description} - {'Found' if exists else 'Missing'}")
    return exists


def validate_yaml_file(file_path, description):
    """Validate that a file exists and is valid YAML"""
    if not validate_file_exists(file_path, f"{description} exists"):
        return False
    
    try:
        with open(file_path, 'r') as f:
            yaml.safe_load(f)
        print(f"✅ PASS: {description} is valid YAML")
        return True
    except Exception as e:
        print(f"❌ FAIL: {description} invalid YAML - {e}")
        return False


def validate_json_file(file_path, description):
    """Validate that a file exists and is valid JSON"""
    if not validate_file_exists(file_path, f"{description} exists"):
        return False
    
    try:
        with open(file_path, 'r') as f:
            json.load(f)
        print(f"✅ PASS: {description} is valid JSON")
        return True
    except Exception as e:
        print(f"❌ FAIL: {description} invalid JSON - {e}")
        return False


def validate_helm_template(file_path, description, expected_kind):
    """Validate that a Helm template file contains expected content"""
    if not validate_file_exists(file_path, f"{description} exists"):
        return False
    
    try:
        with open(file_path, 'r') as f:
            content = f.read()
        
        # Check for basic Helm template structure
        has_kind = f"kind: {expected_kind}" in content
        has_templates = "{{" in content and "}}" in content
        has_apiversion = "apiVersion:" in content
        
        all_checks = [
            (has_kind, f"{description} has correct kind ({expected_kind})"),
            (has_templates, f"{description} has Helm templating"),
            (has_apiversion, f"{description} has apiVersion")
        ]
        
        all_passed = True
        for check_passed, check_description in all_checks:
            status = "✅ PASS" if check_passed else "❌ FAIL"
            print(f"{status}: {check_description}")
            if not check_passed:
                all_passed = False
        
        return all_passed
        
    except Exception as e:
        print(f"❌ FAIL: {description} read error - {e}")
        return False


def main():
    """Main validation function"""
    print("🚀 Starting Step 8 Validation - Kubernetes Helm Charts & GitOps Integration")
    print("=" * 80)
    
    project_root = "/home/yasar/cicd_project"
    
    if not os.path.exists(project_root):
        print(f"❌ Project directory not found: {project_root}")
        sys.exit(1)
    
    results = []
    
    # 1. Helm Chart Structure
    print("\n🔍 Validating Helm Chart Structure...")
    helm_base = f"{project_root}/helm/reddit-sentiment-pipeline"
    
    results.append(validate_yaml_file(f"{helm_base}/Chart.yaml", "Chart.yaml"))
    results.append(validate_yaml_file(f"{helm_base}/values.yaml", "values.yaml"))
    results.append(validate_file_exists(f"{helm_base}/README.md", "Helm README"))
    
    # 2. Kubernetes Templates
    print("\n🔍 Validating Kubernetes Templates...")
    templates_base = f"{helm_base}/templates"
    
    template_validations = [
        ("cronjob.yaml", "CronJob template", "CronJob"),
        ("serviceaccount.yaml", "ServiceAccount template", "ServiceAccount"),
        ("configmap.yaml", "ConfigMap template", "ConfigMap"),
        ("secret.yaml", "Secret template", "Secret"),
        ("pvc.yaml", "PVC template", "PersistentVolumeClaim"),
        ("servicemonitor.yaml", "ServiceMonitor template", "ServiceMonitor"),
        ("networkpolicy.yaml", "NetworkPolicy template", "NetworkPolicy"),
        ("pdb.yaml", "PodDisruptionBudget template", "PodDisruptionBudget"),
        ("prometheusrule.yaml", "PrometheusRule template", "PrometheusRule")
    ]
    
    for filename, description, kind in template_validations:
        results.append(validate_helm_template(f"{templates_base}/{filename}", description, kind))
    
    results.append(validate_file_exists(f"{templates_base}/_helpers.tpl", "Helm helpers template"))
    
    # 3. Argo CD Integration
    print("\n🔍 Validating Argo CD Integration...")
    argocd_base = f"{project_root}/argocd"
    
    results.append(validate_yaml_file(f"{argocd_base}/application.yaml", "Argo CD Application"))
    results.append(validate_yaml_file(f"{argocd_base}/appproject.yaml", "Argo CD AppProject"))
    
    # 4. Grafana Dashboard
    print("\n🔍 Validating Grafana Dashboard...")
    grafana_base = f"{project_root}/grafana"
    
    results.append(validate_json_file(f"{grafana_base}/dashboard.json", "Grafana Dashboard JSON"))
    results.append(validate_yaml_file(f"{grafana_base}/configmap.yaml", "Grafana ConfigMap"))
    
    # 5. Deployment Script
    print("\n🔍 Validating Deployment Script...")
    script_path = f"{project_root}/scripts/deploy_production.sh"
    script_exists = validate_file_exists(script_path, "Production deployment script")
    results.append(script_exists)
    
    if script_exists:
        is_executable = os.access(script_path, os.X_OK)
        status = "✅ PASS" if is_executable else "❌ FAIL"
        print(f"{status}: Deployment script is executable")
        results.append(is_executable)
    
    # 6. Documentation
    print("\n🔍 Validating Documentation...")
    results.append(validate_file_exists(f"{project_root}/docs/gitops-workflow.yaml", "GitOps workflow documentation"))
    
    # Summary
    print("\n" + "=" * 80)
    print("📊 STEP 8 VALIDATION SUMMARY")
    print("=" * 80)
    
    total_tests = len(results)
    passed_tests = sum(results)
    failed_tests = total_tests - passed_tests
    success_rate = (passed_tests / total_tests) * 100
    
    print(f"Total Tests: {total_tests}")
    print(f"Passed: {passed_tests}")
    print(f"Failed: {failed_tests}")
    print(f"Success Rate: {success_rate:.1f}%")
    
    all_passed = all(results)
    
    if all_passed:
        print("\n🎉 STEP 8 VALIDATION PASSED!")
        print("\n✅ Kubernetes Helm Charts & GitOps Integration completed successfully!")
        print("\nKey achievements:")
        print("  ✓ Complete Helm chart with all Kubernetes resources")
        print("  ✓ Argo CD integration for GitOps deployment")
        print("  ✓ Grafana dashboard for monitoring")
        print("  ✓ Production deployment automation")
        print("  ✓ Comprehensive documentation")
    else:
        print("\n❌ STEP 8 VALIDATION FAILED!")
        print("\nSome components are missing or invalid. Please check the failed tests above.")
    
    print("\n" + "=" * 80)
    
    # Exit with appropriate code
    sys.exit(0 if all_passed else 1)


if __name__ == "__main__":
    main()
