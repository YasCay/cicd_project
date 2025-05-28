#!/usr/bin/env python3
"""
Alert Testing Script for Reddit Sentiment Pipeline
Tests various alert scenarios to ensure alerting system is working correctly.
"""

import os
import sys
import json
import time
import requests
import subprocess
from datetime import datetime, timedelta
import logging
from pathlib import Path

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('/tmp/alert_test.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class AlertTester:
    """Test alert system functionality"""
    
    def __init__(self):
        self.webhook_url = os.getenv('WEBHOOK_URL', 'http://localhost:5000/webhook')
        self.prometheus_url = os.getenv('PROMETHEUS_URL', 'http://localhost:9090')
        self.alertmanager_url = os.getenv('ALERTMANAGER_URL', 'http://localhost:9093')
        self.github_token = os.getenv('GITHUB_TOKEN')
        self.github_repo = os.getenv('GITHUB_REPO', 'YasCay/cicd_project')
        
    def test_service_down_alert(self):
        """Test service down alert scenario"""
        logger.info("🔥 Testing Service Down Alert...")
        
        # Simulate service down by creating a test alert
        alert_data = {
            "receiver": "github-webhook",
            "status": "firing",
            "alerts": [
                {
                    "status": "firing",
                    "labels": {
                        "alertname": "ServiceDown",
                        "instance": "reddit-collector:8080",
                        "job": "reddit-sentiment-pipeline",
                        "severity": "critical"
                    },
                    "annotations": {
                        "summary": "Reddit Collector service is down",
                        "description": "The Reddit Collector service has been down for more than 5 minutes",
                        "runbook_url": "https://github.com/YasCay/cicd_project/blob/main/docs/monitoring-runbook.md#service-down-alert"
                    },
                    "startsAt": datetime.utcnow().isoformat() + "Z",
                    "generatorURL": f"{self.prometheus_url}/graph"
                }
            ],
            "groupLabels": {
                "alertname": "ServiceDown"
            },
            "commonLabels": {
                "alertname": "ServiceDown",
                "severity": "critical"
            },
            "commonAnnotations": {
                "summary": "Reddit Collector service is down"
            }
        }
        
        return self._send_test_alert(alert_data, "Service Down Alert")
    
    def test_high_error_rate_alert(self):
        """Test high error rate alert scenario"""
        logger.info("⚠️ Testing High Error Rate Alert...")
        
        alert_data = {
            "receiver": "github-webhook",
            "status": "firing",
            "alerts": [
                {
                    "status": "firing",
                    "labels": {
                        "alertname": "HighErrorRate",
                        "instance": "reddit-collector:8080",
                        "job": "reddit-sentiment-pipeline",
                        "severity": "warning"
                    },
                    "annotations": {
                        "summary": "High error rate detected in Reddit API calls",
                        "description": "Error rate is 15.2% over the last 5 minutes (threshold: 10%)",
                        "runbook_url": "https://github.com/YasCay/cicd_project/blob/main/docs/monitoring-runbook.md#high-error-rate"
                    },
                    "startsAt": datetime.utcnow().isoformat() + "Z",
                    "generatorURL": f"{self.prometheus_url}/graph"
                }
            ],
            "groupLabels": {
                "alertname": "HighErrorRate"
            },
            "commonLabels": {
                "alertname": "HighErrorRate",
                "severity": "warning"
            }
        }
        
        return self._send_test_alert(alert_data, "High Error Rate Alert")
    
    def test_resource_usage_alert(self):
        """Test resource usage alert scenario"""
        logger.info("📊 Testing Resource Usage Alert...")
        
        alert_data = {
            "receiver": "github-webhook",
            "status": "firing",
            "alerts": [
                {
                    "status": "firing",
                    "labels": {
                        "alertname": "HighCPUUsage",
                        "instance": "reddit-collector:8080",
                        "job": "reddit-sentiment-pipeline",
                        "severity": "warning"
                    },
                    "annotations": {
                        "summary": "High CPU usage detected",
                        "description": "CPU usage is 87% over the last 10 minutes (threshold: 80%)",
                        "runbook_url": "https://github.com/YasCay/cicd_project/blob/main/docs/monitoring-runbook.md#resource-usage"
                    },
                    "startsAt": datetime.utcnow().isoformat() + "Z",
                    "generatorURL": f"{self.prometheus_url}/graph"
                }
            ]
        }
        
        return self._send_test_alert(alert_data, "Resource Usage Alert")
    
    def test_github_notification(self):
        """Test GitHub integration and issue creation"""
        logger.info("🐙 Testing GitHub Notification...")
        
        if not self.github_token:
            logger.warning("GitHub token not configured, skipping GitHub test")
            return False
        
        # Test GitHub API connectivity
        headers = {
            'Authorization': f'token {self.github_token}',
            'Accept': 'application/vnd.github.v3+json'
        }
        
        try:
            response = requests.get(
                f'https://api.github.com/repos/{self.github_repo}',
                headers=headers,
                timeout=10
            )
            
            if response.status_code == 200:
                logger.info("✅ GitHub API connectivity test passed")
                
                # Test creating a test issue
                issue_data = {
                    "title": "[TEST] Alert System Test Issue",
                    "body": "This is a test issue created by the alert testing system.\n\n"
                           "**Alert Details:**\n"
                           "- Test Type: GitHub Integration Test\n"
                           f"- Timestamp: {datetime.utcnow().isoformat()}Z\n"
                           "- Status: Testing\n\n"
                           "This issue should be automatically closed by the alert system.",
                    "labels": ["test", "alert", "automated"]
                }
                
                create_response = requests.post(
                    f'https://api.github.com/repos/{self.github_repo}/issues',
                    headers=headers,
                    json=issue_data,
                    timeout=10
                )
                
                if create_response.status_code == 201:
                    issue = create_response.json()
                    logger.info(f"✅ Test issue created: #{issue['number']}")
                    
                    # Close the test issue
                    time.sleep(2)
                    close_response = requests.patch(
                        f"https://api.github.com/repos/{self.github_repo}/issues/{issue['number']}",
                        headers=headers,
                        json={"state": "closed"},
                        timeout=10
                    )
                    
                    if close_response.status_code == 200:
                        logger.info("✅ Test issue closed successfully")
                        return True
                    else:
                        logger.error(f"Failed to close test issue: {close_response.status_code}")
                        return False
                else:
                    logger.error(f"Failed to create test issue: {create_response.status_code}")
                    return False
            else:
                logger.error(f"GitHub API test failed: {response.status_code}")
                return False
                
        except Exception as e:
            logger.error(f"GitHub notification test failed: {e}")
            return False
    
    def test_alert_resolution(self):
        """Test alert resolution scenario"""
        logger.info("✅ Testing Alert Resolution...")
        
        alert_data = {
            "receiver": "github-webhook",
            "status": "resolved",
            "alerts": [
                {
                    "status": "resolved",
                    "labels": {
                        "alertname": "ServiceDown",
                        "instance": "reddit-collector:8080",
                        "job": "reddit-sentiment-pipeline",
                        "severity": "critical"
                    },
                    "annotations": {
                        "summary": "Reddit Collector service is back online",
                        "description": "The Reddit Collector service has recovered and is responding normally"
                    },
                    "startsAt": (datetime.utcnow() - timedelta(minutes=10)).isoformat() + "Z",
                    "endsAt": datetime.utcnow().isoformat() + "Z",
                    "generatorURL": f"{self.prometheus_url}/graph"
                }
            ]
        }
        
        return self._send_test_alert(alert_data, "Alert Resolution")
    
    def test_webhook_handler_availability(self):
        """Test if webhook handler is running and accessible"""
        logger.info("🌐 Testing Webhook Handler Availability...")
        
        try:
            response = requests.get(f"{self.webhook_url}/health", timeout=5)
            if response.status_code == 200:
                logger.info("✅ Webhook handler is accessible")
                return True
            else:
                logger.error(f"Webhook handler returned {response.status_code}")
                return False
        except requests.exceptions.RequestException as e:
            logger.error(f"Webhook handler not accessible: {e}")
            return False
    
    def test_prometheus_connectivity(self):
        """Test Prometheus connectivity"""
        logger.info("📈 Testing Prometheus Connectivity...")
        
        try:
            response = requests.get(f"{self.prometheus_url}/api/v1/query?query=up", timeout=10)
            if response.status_code == 200:
                data = response.json()
                if data.get('status') == 'success':
                    logger.info("✅ Prometheus is accessible and responding")
                    return True
            logger.error(f"Prometheus test failed: {response.status_code}")
            return False
        except Exception as e:
            logger.error(f"Prometheus connectivity test failed: {e}")
            return False
    
    def test_alertmanager_connectivity(self):
        """Test Alertmanager connectivity"""
        logger.info("🚨 Testing Alertmanager Connectivity...")
        
        try:
            response = requests.get(f"{self.alertmanager_url}/api/v1/status", timeout=10)
            if response.status_code == 200:
                logger.info("✅ Alertmanager is accessible and responding")
                return True
            logger.error(f"Alertmanager test failed: {response.status_code}")
            return False
        except Exception as e:
            logger.error(f"Alertmanager connectivity test failed: {e}")
            return False
    
    def _send_test_alert(self, alert_data, test_name):
        """Send test alert to webhook handler"""
        try:
            response = requests.post(
                self.webhook_url,
                json=alert_data,
                headers={'Content-Type': 'application/json'},
                timeout=10
            )
            
            if response.status_code in [200, 201, 202]:
                logger.info(f"✅ {test_name} sent successfully")
                return True
            else:
                logger.error(f"❌ {test_name} failed: {response.status_code}")
                logger.error(f"Response: {response.text}")
                return False
                
        except Exception as e:
            logger.error(f"❌ {test_name} failed: {e}")
            return False
    
    def run_all_tests(self):
        """Run comprehensive alert testing suite"""
        logger.info("🚀 Starting Alert System Test Suite...")
        print("=" * 60)
        print("🧪 Alert System Testing Suite")
        print("=" * 60)
        
        tests = [
            ("Infrastructure Tests", [
                ("Webhook Handler Availability", self.test_webhook_handler_availability),
                ("Prometheus Connectivity", self.test_prometheus_connectivity),
                ("Alertmanager Connectivity", self.test_alertmanager_connectivity),
            ]),
            ("Alert Functionality Tests", [
                ("Service Down Alert", self.test_service_down_alert),
                ("High Error Rate Alert", self.test_high_error_rate_alert),
                ("Resource Usage Alert", self.test_resource_usage_alert),
                ("Alert Resolution", self.test_alert_resolution),
            ]),
            ("Integration Tests", [
                ("GitHub Notification", self.test_github_notification),
            ])
        ]
        
        total_tests = sum(len(test_group[1]) for test_group in tests)
        passed_tests = 0
        
        for group_name, test_list in tests:
            print(f"\n📋 {group_name}")
            print("-" * 40)
            
            for test_name, test_func in test_list:
                print(f"Running: {test_name}...")
                try:
                    if test_func():
                        print(f"✅ {test_name} - PASSED")
                        passed_tests += 1
                    else:
                        print(f"❌ {test_name} - FAILED")
                except Exception as e:
                    print(f"❌ {test_name} - ERROR: {e}")
                
                # Small delay between tests
                time.sleep(1)
        
        print("\n" + "=" * 60)
        print(f"📊 Test Results: {passed_tests}/{total_tests} tests passed")
        
        if passed_tests == total_tests:
            print("🎉 All alert tests passed successfully!")
            logger.info("✅ Alert system test suite completed successfully")
            return True
        else:
            print(f"⚠️  {total_tests - passed_tests} tests failed")
            logger.warning(f"❌ Alert system test suite completed with {total_tests - passed_tests} failures")
            return False

def main():
    """Main test execution"""
    # Load environment variables
    if os.path.exists('.env'):
        with open('.env') as f:
            for line in f:
                if line.strip() and not line.startswith('#'):
                    key, value = line.strip().split('=', 1)
                    os.environ[key] = value
    
    tester = AlertTester()
    success = tester.run_all_tests()
    
    return 0 if success else 1

if __name__ == "__main__":
    sys.exit(main())
