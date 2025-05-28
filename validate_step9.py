#!/usr/bin/env python3
"""
Step 9 Validation Script - Production Server Deployment Automation

This script validates the successful completion of Step 9, which includes:
1. Enhanced production deployment automation
2. Systemd service configuration and management
3. Health monitoring and automatic restart capabilities
4. Backup and recovery procedures
5. Production environment setup validation

Author: GitHub Copilot
Date: 2024
"""

import os
import sys
import json
import subprocess
from pathlib import Path
from typing import Dict, List, Tuple, Any


class Step9Validator:
    """Validates Step 9 completion - Production Server Deployment Automation"""
    
    def __init__(self, project_root: str = "/home/yasar/cicd_project"):
        self.project_root = Path(project_root)
        self.validation_results = []
        self.errors = []
        
    def log_result(self, test_name: str, passed: bool, message: str = ""):
        """Log validation result"""
        status = "✅ PASS" if passed else "❌ FAIL"
        result = f"{status}: {test_name}"
        if message:
            result += f" - {message}"
        
        self.validation_results.append(result)
        if not passed:
            self.errors.append(f"{test_name}: {message}")
        print(result)
    
    def validate_deployment_scripts(self) -> bool:
        """Validate enhanced deployment scripts and automation"""
        print("\n🔍 Validating Deployment Scripts...")
        
        scripts_path = self.project_root / "scripts"
        required_scripts = [
            "deploy_production.sh",
            "setup_production_env.sh",
            "health_check.py",
            "backup_manager.py"
        ]
        
        all_scripts_present = True
        
        for script in required_scripts:
            script_path = scripts_path / script
            exists = script_path.exists()
            self.log_result(
                f"Deployment script exists: {script}",
                exists,
                f"Found at {script_path}" if exists else f"Missing: {script_path}"
            )
            if not exists:
                all_scripts_present = False
            elif script.endswith('.sh'):
                # Check if shell script is executable
                is_executable = os.access(script_path, os.X_OK)
                self.log_result(
                    f"Script is executable: {script}",
                    is_executable,
                    "Has execute permissions" if is_executable else "Missing execute permissions"
                )
                if not is_executable:
                    all_scripts_present = False
        
        return all_scripts_present
    
    def validate_systemd_service(self) -> bool:
        """Validate systemd service configuration"""
        print("\n🔍 Validating Systemd Service Configuration...")
        
        systemd_path = self.project_root / "systemd"
        service_files = [
            "reddit-sentiment-pipeline.service",
            "reddit-sentiment-pipeline.timer",
            "reddit-sentiment-monitor.service"
        ]
        
        all_services_valid = True
        
        # Check if systemd directory exists
        exists = systemd_path.exists()
        self.log_result(
            "Systemd directory exists",
            exists,
            f"Found at {systemd_path}" if exists else f"Missing: {systemd_path}"
        )
        if not exists:
            return False
        
        for service_file in service_files:
            service_path = systemd_path / service_file
            exists = service_path.exists()
            self.log_result(
                f"Systemd file exists: {service_file}",
                exists,
                f"Found at {service_path}" if exists else f"Missing: {service_path}"
            )
            if not exists:
                all_services_valid = False
                continue
            
            # Validate service file content
            try:
                with open(service_path, 'r') as f:
                    content = f.read()
                
                # Check for required sections in service files
                if service_file.endswith('.service'):
                    required_sections = ['[Unit]', '[Service]', '[Install]']
                    for section in required_sections:
                        if section in content:
                            self.log_result(
                                f"Service {service_file} has {section}",
                                True,
                                "Section found"
                            )
                        else:
                            self.log_result(
                                f"Service {service_file} has {section}",
                                False,
                                f"Missing section: {section}"
                            )
                            all_services_valid = False
                
                elif service_file.endswith('.timer'):
                    required_sections = ['[Unit]', '[Timer]', '[Install]']
                    for section in required_sections:
                        if section in content:
                            self.log_result(
                                f"Timer {service_file} has {section}",
                                True,
                                "Section found"
                            )
                        else:
                            self.log_result(
                                f"Timer {service_file} has {section}",
                                False,
                                f"Missing section: {section}"
                            )
                            all_services_valid = False
                
            except Exception as e:
                self.log_result(
                    f"Service file validation: {service_file}",
                    False,
                    f"Error reading file: {e}"
                )
                all_services_valid = False
        
        return all_services_valid
    
    def validate_monitoring_setup(self) -> bool:
        """Validate monitoring and health check setup"""
        print("\n🔍 Validating Monitoring Setup...")
        
        monitoring_path = self.project_root / "monitoring"
        required_files = [
            "health_dashboard.json",
            "alerting_rules.yml",
            "prometheus_config.yml"
        ]
        
        all_monitoring_valid = True
        
        # Check if monitoring directory exists
        exists = monitoring_path.exists()
        self.log_result(
            "Monitoring directory exists",
            exists,
            f"Found at {monitoring_path}" if exists else f"Missing: {monitoring_path}"
        )
        
        if exists:
            for file in required_files:
                file_path = monitoring_path / file
                exists = file_path.exists()
                self.log_result(
                    f"Monitoring file exists: {file}",
                    exists,
                    f"Found at {file_path}" if exists else f"Missing: {file_path}"
                )
                if not exists:
                    all_monitoring_valid = False
        else:
            all_monitoring_valid = False
        
        return all_monitoring_valid
    
    def validate_backup_system(self) -> bool:
        """Validate backup and recovery system"""
        print("\n🔍 Validating Backup System...")
        
        backup_script = self.project_root / "scripts" / "backup_manager.py"
        
        if not backup_script.exists():
            self.log_result("Backup manager script", False, "backup_manager.py not found")
            return False
        
        try:
            with open(backup_script, 'r') as f:
                content = f.read()
            
            # Check for key backup functions
            backup_functions = [
                'create_backup',
                'restore_backup',
                'cleanup_old_backups',
                'verify_backup'
            ]
            
            all_functions_present = True
            for func in backup_functions:
                if f"def {func}" in content:
                    self.log_result(
                        f"Backup function exists: {func}",
                        True,
                        "Function found"
                    )
                else:
                    self.log_result(
                        f"Backup function exists: {func}",
                        False,
                        f"Missing function: {func}"
                    )
                    all_functions_present = False
            
            return all_functions_present
            
        except Exception as e:
            self.log_result("Backup script validation", False, f"Error reading file: {e}")
            return False
    
    def validate_configuration_management(self) -> bool:
        """Validate configuration management and environment setup"""
        print("\n🔍 Validating Configuration Management...")
        
        config_path = self.project_root / "config"
        required_configs = [
            "production.env",
            "logging.conf",
            "monitoring.yml"
        ]
        
        all_configs_valid = True
        
        # Check if config directory exists
        exists = config_path.exists()
        self.log_result(
            "Config directory exists",
            exists,
            f"Found at {config_path}" if exists else f"Missing: {config_path}"
        )
        
        if exists:
            for config in required_configs:
                config_file = config_path / config
                exists = config_file.exists()
                self.log_result(
                    f"Config file exists: {config}",
                    exists,
                    f"Found at {config_file}" if exists else f"Missing: {config_file}"
                )
                if not exists:
                    all_configs_valid = False
        else:
            all_configs_valid = False
        
        return all_configs_valid
    
    def validate_production_environment(self) -> bool:
        """Validate production environment setup script"""
        print("\n🔍 Validating Production Environment Setup...")
        
        setup_script = self.project_root / "scripts" / "setup_production_env.sh"
        
        if not setup_script.exists():
            self.log_result("Production setup script", False, "setup_production_env.sh not found")
            return False
        
        try:
            with open(setup_script, 'r') as f:
                content = f.read()
            
            # Check for key setup functions
            setup_functions = [
                'setup_user_environment',
                'install_dependencies',
                'configure_systemd',
                'setup_monitoring',
                'setup_backup_cron'
            ]
            
            all_functions_present = True
            for func in setup_functions:
                if func in content:
                    self.log_result(
                        f"Setup function exists: {func}",
                        True,
                        "Function found"
                    )
                else:
                    self.log_result(
                        f"Setup function exists: {func}",
                        False,
                        f"Missing function: {func}"
                    )
                    all_functions_present = False
            
            # Check if script is executable
            is_executable = os.access(setup_script, os.X_OK)
            self.log_result(
                "Setup script is executable",
                is_executable,
                "Has execute permissions" if is_executable else "Missing execute permissions"
            )
            
            return all_functions_present and is_executable
            
        except Exception as e:
            self.log_result("Setup script validation", False, f"Error reading file: {e}")
            return False
    
    def validate_documentation(self) -> bool:
        """Validate Step 9 documentation"""
        print("\n🔍 Validating Documentation...")
        
        docs_path = self.project_root / "docs"
        required_docs = [
            "production-deployment.md",
            "monitoring-runbook.md",
            "backup-recovery.md"
        ]
        
        all_docs_valid = True
        
        for doc in required_docs:
            doc_path = docs_path / doc
            exists = doc_path.exists()
            self.log_result(
                f"Documentation exists: {doc}",
                exists,
                f"Found at {doc_path}" if exists else f"Missing: {doc_path}"
            )
            if not exists:
                all_docs_valid = False
            else:
                # Check if documentation has sufficient content
                try:
                    with open(doc_path, 'r') as f:
                        content = f.read()
                    
                    has_content = len(content.strip()) > 500  # At least 500 characters
                    self.log_result(
                        f"Documentation has content: {doc}",
                        has_content,
                        f"Content length: {len(content)} characters" if has_content else "Insufficient content"
                    )
                    if not has_content:
                        all_docs_valid = False
                        
                except Exception as e:
                    self.log_result(
                        f"Documentation validation: {doc}",
                        False,
                        f"Error reading file: {e}"
                    )
                    all_docs_valid = False
        
        return all_docs_valid
    
    def run_validation(self) -> bool:
        """Run all Step 9 validations"""
        print("🚀 Starting Step 9 Validation - Production Server Deployment Automation")
        print("=" * 80)
        
        validations = [
            self.validate_deployment_scripts,
            self.validate_systemd_service,
            self.validate_monitoring_setup,
            self.validate_backup_system,
            self.validate_configuration_management,
            self.validate_production_environment,
            self.validate_documentation
        ]
        
        all_passed = True
        for validation in validations:
            try:
                result = validation()
                if not result:
                    all_passed = False
            except Exception as e:
                self.log_result(f"Validation error", False, f"Exception: {e}")
                all_passed = False
        
        # Summary
        print("\n" + "=" * 80)
        print("📊 STEP 9 VALIDATION SUMMARY")
        print("=" * 80)
        
        total_tests = len(self.validation_results)
        passed_tests = sum(1 for result in self.validation_results if "✅ PASS" in result)
        failed_tests = total_tests - passed_tests
        success_rate = (passed_tests / total_tests * 100) if total_tests > 0 else 0
        
        print(f"Total Tests: {total_tests}")
        print(f"Passed: {passed_tests}")
        print(f"Failed: {failed_tests}")
        print(f"Success Rate: {success_rate:.1f}%")
        
        if all_passed and success_rate >= 95:
            print("\n🎉 STEP 9 VALIDATION PASSED!")
            print("\n✅ Production Server Deployment Automation completed successfully!")
            print("\nKey achievements:")
            print("  ✓ Enhanced deployment automation scripts")
            print("  ✓ Systemd service integration with monitoring")
            print("  ✓ Health checks and automatic restart capabilities")
            print("  ✓ Backup and recovery system")
            print("  ✓ Production environment configuration")
            print("  ✓ Comprehensive monitoring and alerting")
        else:
            print(f"\n❌ STEP 9 VALIDATION FAILED!")
            if self.errors:
                print(f"\nErrors found ({len(self.errors)}):")
                for error in self.errors[:10]:  # Show first 10 errors
                    print(f"  • {error}")
                if len(self.errors) > 10:
                    print(f"  ... and {len(self.errors) - 10} more errors")
        
        print("=" * 80)
        return all_passed and success_rate >= 95


if __name__ == "__main__":
    validator = Step9Validator()
    success = validator.run_validation()
    sys.exit(0 if success else 1)
