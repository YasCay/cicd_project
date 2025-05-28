#!/usr/bin/env python3
"""
Step 10 Validation: Alerting and Monitoring Setup
Validates comprehensive alerting and monitoring configuration for the Reddit Sentiment Pipeline.
"""

import os
import sys
import json
import yaml
import subprocess
from pathlib import Path

def validate_alertmanager_config():
    """Validate Alertmanager configuration"""
    print("🔍 Validating Alertmanager Configuration...")
    
    # Check alertmanager config file
    config_file = Path("monitoring/alertmanager_config.yml")
    if not config_file.exists():
        print("❌ Missing alertmanager_config.yml")
        return False
    
    try:
        with open(config_file) as f:
            config = yaml.safe_load(f)
        
        # Validate structure
        required_sections = ['global', 'route', 'receivers']
        for section in required_sections:
            if section not in config:
                print(f"❌ Missing {section} section in alertmanager config")
                return False
        
        # Check GitHub webhook configuration
        github_receiver = None
        for receiver in config.get('receivers', []):
            if 'webhook_configs' in receiver:
                for webhook in receiver['webhook_configs']:
                    if 'github' in webhook.get('url', '').lower():
                        github_receiver = receiver
                        break
        
        if not github_receiver:
            print("❌ No GitHub webhook receiver configured")
            return False
        
        print("✅ Alertmanager configuration valid")
        return True
        
    except Exception as e:
        print(f"❌ Error validating alertmanager config: {e}")
        return False

def validate_grafana_alerting():
    """Validate Grafana alerting configuration"""
    print("🔍 Validating Grafana Alerting Configuration...")
    
    # Check grafana alerting rules
    alert_rules_file = Path("grafana/alert_rules.json")
    if not alert_rules_file.exists():
        print("❌ Missing grafana alert_rules.json")
        return False
    
    try:
        with open(alert_rules_file) as f:
            rules = json.load(f)
        
        # Validate structure
        if not isinstance(rules, dict) or 'rules' not in rules:
            print("❌ Invalid alert rules structure")
            return False
        
        rules_list = rules['rules']
        if len(rules_list) < 3:
            print("❌ Insufficient alert rules (need at least 3)")
            return False
        
        # Check for essential alert types
        alert_types = [rule.get('title', '').lower() for rule in rules_list]
        required_alerts = ['service down', 'high error rate', 'resource usage']
        
        for required in required_alerts:
            if not any(required in alert_type for alert_type in alert_types):
                print(f"❌ Missing {required} alert rule")
                return False
        
        print("✅ Grafana alerting configuration valid")
        return True
        
    except Exception as e:
        print(f"❌ Error validating grafana alerts: {e}")
        return False

def validate_notification_channels():
    """Validate notification channels configuration"""
    print("🔍 Validating Notification Channels...")
    
    # Check notification channels config
    channels_file = Path("monitoring/notification_channels.yml")
    if not channels_file.exists():
        print("❌ Missing notification_channels.yml")
        return False
    
    try:
        with open(channels_file) as f:
            channels = yaml.safe_load(f)
        
        # Validate GitHub notification channel
        if 'github' not in channels:
            print("❌ Missing GitHub notification channel")
            return False
        
        github_config = channels['github']
        required_fields = ['webhook_url', 'token', 'repository']
        
        for field in required_fields:
            if field not in github_config:
                print(f"❌ Missing {field} in GitHub notification config")
                return False
        
        # Check if repository matches the expected format
        repo = github_config['repository']
        if not repo.startswith('YasCay/'):
            print(f"❌ Repository should be YasCay/cicd_project, got: {repo}")
            return False
        
        print("✅ Notification channels configuration valid")
        return True
        
    except Exception as e:
        print(f"❌ Error validating notification channels: {e}")
        return False

def validate_alert_webhook_handler():
    """Validate alert webhook handler"""
    print("🔍 Validating Alert Webhook Handler...")
    
    # Check webhook handler script
    handler_file = Path("scripts/alert_webhook_handler.py")
    if not handler_file.exists():
        print("❌ Missing alert_webhook_handler.py")
        return False
    
    try:
        with open(handler_file) as f:
            content = f.read()
        
        # Check for essential functions
        required_functions = [
            'handle_webhook',
            'create_github_issue',
            'update_github_issue',
            'send_notification'
        ]
        
        for func in required_functions:
            if f"def {func}" not in content:
                print(f"❌ Missing function: {func}")
                return False
        
        # Check for GitHub API integration
        if 'github.com/api' not in content and 'api.github.com' not in content:
            print("❌ Missing GitHub API integration")
            return False
        
        print("✅ Alert webhook handler valid")
        return True
        
    except Exception as e:
        print(f"❌ Error validating webhook handler: {e}")
        return False

def validate_escalation_policies():
    """Validate alert escalation policies"""
    print("🔍 Validating Escalation Policies...")
    
    # Check escalation config
    escalation_file = Path("monitoring/escalation_policies.yml")
    if not escalation_file.exists():
        print("❌ Missing escalation_policies.yml")
        return False
    
    try:
        with open(escalation_file) as f:
            policies = yaml.safe_load(f)
        
        # Validate structure
        if 'policies' not in policies:
            print("❌ Missing policies section")
            return False
        
        policies_list = policies['policies']
        if len(policies_list) < 2:
            print("❌ Need at least 2 escalation policies (critical and warning)")
            return False
        
        # Check for severity-based escalation
        severities = [policy.get('severity') for policy in policies_list]
        if 'critical' not in severities or 'warning' not in severities:
            print("❌ Missing critical or warning severity policies")
            return False
        
        print("✅ Escalation policies configuration valid")
        return True
        
    except Exception as e:
        print(f"❌ Error validating escalation policies: {e}")
        return False

def validate_monitoring_dashboard_alerts():
    """Validate monitoring dashboard has alert panels"""
    print("🔍 Validating Monitoring Dashboard Alerts...")
    
    # Check main dashboard
    dashboard_file = Path("grafana/dashboard.json")
    if not dashboard_file.exists():
        print("❌ Missing main dashboard.json")
        return False
    
    try:
        with open(dashboard_file) as f:
            dashboard = json.load(f)
        
        # Check for alert-related panels
        panels = dashboard.get('panels', [])
        alert_panels = [p for p in panels if 'alert' in str(p).lower()]
        
        if len(alert_panels) < 2:
            print("❌ Dashboard needs at least 2 alert-related panels")
            return False
        
        # Check for alert list panel
        alert_list_panel = any('alertlist' in str(p).lower() for p in panels)
        if not alert_list_panel:
            print("❌ Missing alert list panel in dashboard")
            return False
        
        print("✅ Monitoring dashboard alerts valid")
        return True
        
    except Exception as e:
        print(f"❌ Error validating dashboard alerts: {e}")
        return False

def validate_alert_testing():
    """Validate alert testing configuration"""
    print("🔍 Validating Alert Testing Configuration...")
    
    # Check test script
    test_file = Path("scripts/test_alerts.py")
    if not test_file.exists():
        print("❌ Missing test_alerts.py")
        return False
    
    try:
        with open(test_file) as f:
            content = f.read()
        
        # Check for test functions
        test_functions = [
            'test_service_down_alert',
            'test_high_error_rate_alert',
            'test_resource_usage_alert',
            'test_github_notification'
        ]
        
        for func in test_functions:
            if f"def {func}" not in content:
                print(f"❌ Missing test function: {func}")
                return False
        
        print("✅ Alert testing configuration valid")
        return True
        
    except Exception as e:
        print(f"❌ Error validating alert testing: {e}")
        return False

def validate_runbook_integration():
    """Validate runbook integration with alerts"""
    print("🔍 Validating Runbook Integration...")
    
    # Check monitoring runbook
    runbook_file = Path("docs/monitoring-runbook.md")
    if not runbook_file.exists():
        print("❌ Missing monitoring runbook")
        return False
    
    try:
        with open(runbook_file) as f:
            content = f.read()
        
        # Check for alert resolution procedures
        required_sections = [
            'Service Down Alert',
            'High Error Rate',
            'Resource Usage',
            'Alert Escalation',
            'GitHub Issue Management'
        ]
        
        for section in required_sections:
            if section.lower() not in content.lower():
                print(f"❌ Missing runbook section: {section}")
                return False
        
        # Check for runbook URLs in alerting rules
        alerting_file = Path("monitoring/alerting_rules.yml")
        if alerting_file.exists():
            with open(alerting_file) as f:
                alert_content = f.read()
            
            if 'runbook_url' not in alert_content:
                print("❌ Missing runbook_url in alerting rules")
                return False
        
        print("✅ Runbook integration valid")
        return True
        
    except Exception as e:
        print(f"❌ Error validating runbook integration: {e}")
        return False

def main():
    """Main validation function"""
    print("=" * 60)
    print("🚀 Step 10 Validation: Alerting and Monitoring Setup")
    print("=" * 60)
    
    # Change to project directory
    os.chdir('/home/yasar/cicd_project')
    
    validations = [
        validate_alertmanager_config,
        validate_grafana_alerting,
        validate_notification_channels,
        validate_alert_webhook_handler,
        validate_escalation_policies,
        validate_monitoring_dashboard_alerts,
        validate_alert_testing,
        validate_runbook_integration
    ]
    
    passed = 0
    total = len(validations)
    
    for validation in validations:
        try:
            if validation():
                passed += 1
            print()
        except Exception as e:
            print(f"❌ Validation error: {e}")
            print()
    
    print("=" * 60)
    print(f"📊 Step 10 Validation Results: {passed}/{total} checks passed")
    
    if passed == total:
        print("🎉 Step 10: Alerting and Monitoring Setup - COMPLETE!")
        print("✅ All alerting and monitoring components validated successfully")
    else:
        print(f"⚠️  Step 10: {total - passed} components need attention")
        print("❌ Please address the failed validations above")
    
    print("=" * 60)
    
    # Return success/failure
    return passed == total

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
