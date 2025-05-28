#!/usr/bin/env python3
"""
Alert Webhook Handler for Reddit Sentiment Pipeline
Handles incoming alerts from Prometheus/Alertmanager and creates GitHub issues
"""

import os
import sys
import json
import logging
import requests
import hashlib
from datetime import datetime
from typing import Dict, List, Optional, Any
from pathlib import Path
from flask import Flask, request, jsonify

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler("/home/cayir/cicd_project/logs/alert_webhook.log"),
        logging.StreamHandler(),
    ],
)
logger = logging.getLogger(__name__)


class GitHubIssueManager:
    """Manages GitHub issue creation and updates for alerts"""

    def __init__(self, token: str, repository: str):
        self.token = token
        self.repository = repository
        self.api_base = "https://api.github.com"
        self.headers = {
            "Authorization": f"Bearer {token}",
            "Accept": "application/vnd.github.v3+json",
            "Content-Type": "application/json",
        }

    def create_github_issue(self, alert_data: Dict[str, Any]) -> Optional[int]:
        """Create a new GitHub issue for an alert"""
        try:
            # Generate issue title and body
            title = self._generate_issue_title(alert_data)
            body = self._generate_issue_body(alert_data)
            labels = self._get_issue_labels(alert_data)

            # Check if issue already exists
            existing_issue = self._find_existing_issue(alert_data)
            if existing_issue:
                logger.info(f"Issue already exists: #{existing_issue}")
                return existing_issue

            # Create new issue
            issue_data = {
                "title": title,
                "body": body,
                "labels": labels,
                "assignees": ["YasCay"],
            }

            url = f"{self.api_base}/repos/{self.repository}/issues"
            response = requests.post(url, headers=self.headers, json=issue_data)

            if response.status_code == 201:
                issue_number = response.json()["number"]
                logger.info(f"Created GitHub issue #{issue_number}")
                return issue_number
            else:
                logger.error(
                    f"Failed to create issue: {response.status_code} - {response.text}"
                )
                return None

        except Exception as e:
            logger.error(f"Error creating GitHub issue: {e}")
            return None

    def update_github_issue(
        self, issue_number: int, alert_data: Dict[str, Any]
    ) -> bool:
        """Update an existing GitHub issue with new alert information"""
        try:
            # Generate update comment
            comment = self._generate_update_comment(alert_data)

            # Add comment to issue
            comment_data = {"body": comment}
            url = f"{self.api_base}/repos/{self.repository}/issues/{issue_number}/comments"

            response = requests.post(url, headers=self.headers, json=comment_data)

            if response.status_code == 201:
                logger.info(f"Updated GitHub issue #{issue_number}")
                return True
            else:
                logger.error(
                    f"Failed to update issue: {response.status_code} - {response.text}"
                )
                return False

        except Exception as e:
            logger.error(f"Error updating GitHub issue: {e}")
            return False

    def close_resolved_issue(
        self, issue_number: int, alert_data: Dict[str, Any]
    ) -> bool:
        """Close a GitHub issue when alert is resolved"""
        try:
            # Add resolution comment
            resolution_comment = self._generate_resolution_comment(alert_data)
            self._add_comment(issue_number, resolution_comment)

            # Close the issue
            issue_data = {"state": "closed"}
            url = f"{self.api_base}/repos/{self.repository}/issues/{issue_number}"

            response = requests.patch(url, headers=self.headers, json=issue_data)

            if response.status_code == 200:
                logger.info(f"Closed GitHub issue #{issue_number}")
                return True
            else:
                logger.error(
                    f"Failed to close issue: {response.status_code} - {response.text}"
                )
                return False

        except Exception as e:
            logger.error(f"Error closing GitHub issue: {e}")
            return False

    def _generate_issue_title(self, alert_data: Dict[str, Any]) -> str:
        """Generate issue title from alert data"""
        alert_name = alert_data.get("alertname", "Unknown Alert")
        severity = alert_data.get("severity", "unknown").upper()
        service = alert_data.get("service", "unknown-service")

        return f"{severity}: {alert_name} - {service}"

    def _generate_issue_body(self, alert_data: Dict[str, Any]) -> str:
        """Generate issue body from alert data"""
        alert_name = alert_data.get("alertname", "Unknown Alert")
        severity = alert_data.get("severity", "unknown")
        service = alert_data.get("service", "unknown-service")
        description = alert_data.get("description", "No description provided")
        runbook_url = alert_data.get("runbook_url", "")

        # Severity emoji
        severity_emoji = {"critical": "🚨", "warning": "⚠️", "info": "ℹ️"}.get(
            severity.lower(), "❓"
        )

        body = f"""## {severity_emoji} Alert: {alert_name}

**Severity:** {severity.upper()}  
**Service:** {service}  
**Status:** FIRING  
**Started:** {datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC")}

### Description
{description}

### Alert Details
"""

        # Add instance details if available
        if "instances" in alert_data:
            body += "\n**Affected Instances:**\n"
            for instance in alert_data["instances"]:
                body += f"- {instance.get('instance', 'unknown')}\n"

        # Add metrics if available
        if "value" in alert_data:
            body += f"\n**Current Value:** {alert_data['value']}\n"

        # Add runbook link
        if runbook_url:
            body += f"\n### 📚 Runbook\n[Resolution Guide]({runbook_url})\n"

        # Add resolution steps
        body += f"""
### 🔧 Resolution Steps

1. **Check Service Status**
   ```bash
   systemctl status {service}
   journalctl -u {service} -f
   ```

2. **Monitor Metrics**
   - [Grafana Dashboard](http://localhost:3000/d/reddit-sentiment-pipeline)
   - [Prometheus Targets](http://localhost:9090/targets)

3. **Follow Runbook**
   {runbook_url if runbook_url else "See monitoring runbook for detailed procedures"}

4. **Update This Issue**
   - Add investigation findings
   - Document resolution steps
   - Close when resolved

### 📊 Monitoring Links
- [Grafana Dashboard](http://localhost:3000/d/reddit-sentiment-pipeline)
- [Prometheus Alerts](http://localhost:9090/alerts)
- [Service Logs](http://localhost:3000/explore)

---
**Alert ID:** {self._generate_alert_id(alert_data)}  
**Auto-created by monitoring system**
"""

        return body

    def _generate_update_comment(self, alert_data: Dict[str, Any]) -> str:
        """Generate update comment for existing issue"""
        status = alert_data.get("status", "unknown")
        timestamp = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC")

        if status.lower() == "firing":
            return f"""## 🔥 Alert Still Firing

**Updated:** {timestamp}  
**Status:** {status}

The alert is still active. Please continue investigation.

**Current Metrics:**
- Value: {alert_data.get("value", "N/A")}
- Instance: {alert_data.get("instance", "N/A")}
"""
        else:
            return f"""## ✅ Alert Status Update

**Updated:** {timestamp}  
**Status:** {status}

Alert status has changed. Please verify resolution.
"""

    def _generate_resolution_comment(self, alert_data: Dict[str, Any]) -> str:
        """Generate resolution comment when alert is resolved"""
        timestamp = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC")

        return f"""## ✅ Alert Resolved

**Resolved:** {timestamp}  
**Status:** RESOLVED

This alert has been automatically resolved by the monitoring system.

The issue appears to have been resolved. Please verify that the service is functioning normally and add any additional resolution notes if needed.

---
*Auto-resolved by monitoring system*
"""

    def _get_issue_labels(self, alert_data: Dict[str, Any]) -> List[str]:
        """Get appropriate labels for the issue"""
        labels = ["alert", "monitoring", "automated"]

        severity = alert_data.get("severity", "").lower()
        if severity:
            labels.append(f"severity-{severity}")

        service = alert_data.get("service", "")
        if service:
            labels.append(f"service-{service}")

        component = alert_data.get("component", "")
        if component:
            labels.append(f"component-{component}")

        return labels

    def _find_existing_issue(self, alert_data: Dict[str, Any]) -> Optional[int]:
        """Find existing issue for the same alert"""
        try:
            alert_id = self._generate_alert_id(alert_data)

            # Search for issues with the alert ID
            url = f"{self.api_base}/repos/{self.repository}/issues"
            params = {"state": "open", "labels": "alert,monitoring", "per_page": 100}

            response = requests.get(url, headers=self.headers, params=params)

            if response.status_code == 200:
                issues = response.json()
                for issue in issues:
                    if alert_id in issue.get("body", ""):
                        return issue["number"]

            return None

        except Exception as e:
            logger.error(f"Error finding existing issue: {e}")
            return None

    def _generate_alert_id(self, alert_data: Dict[str, Any]) -> str:
        """Generate unique alert ID"""
        alert_name = alert_data.get("alertname", "")
        service = alert_data.get("service", "")
        instance = alert_data.get("instance", "")

        combined = f"{alert_name}-{service}-{instance}"
        return hashlib.md5(combined.encode()).hexdigest()[:8]

    def _add_comment(self, issue_number: int, comment: str) -> bool:
        """Add comment to issue"""
        try:
            comment_data = {"body": comment}
            url = f"{self.api_base}/repos/{self.repository}/issues/{issue_number}/comments"

            response = requests.post(url, headers=self.headers, json=comment_data)
            return response.status_code == 201

        except Exception as e:
            logger.error(f"Error adding comment: {e}")
            return False


class AlertWebhookHandler:
    """Main webhook handler for processing alerts"""

    def __init__(self):
        self.github_manager = None
        self._initialize_github_manager()

    def _initialize_github_manager(self):
        """Initialize GitHub issue manager"""
        try:
            # Load environment variables
            github_token = os.getenv("GITHUB_TOKEN_PAT")
            repository = "YasCay/cicd_project"

            if not github_token:
                logger.error("GITHUB_TOKEN_PAT not found in environment")
                return

            self.github_manager = GitHubIssueManager(github_token, repository)
            logger.info("GitHub issue manager initialized")

        except Exception as e:
            logger.error(f"Failed to initialize GitHub manager: {e}")

    def handle_webhook(self, webhook_data: Dict[str, Any]) -> Dict[str, Any]:
        """Handle incoming webhook from Alertmanager"""
        try:
            logger.info(f"Received webhook: {json.dumps(webhook_data, indent=2)}")

            # Process each alert in the webhook
            results = []

            alerts = webhook_data.get("alerts", [])
            for alert in alerts:
                result = self._process_alert(alert)
                results.append(result)

            return {
                "status": "success",
                "processed_alerts": len(alerts),
                "results": results,
            }

        except Exception as e:
            logger.error(f"Error handling webhook: {e}")
            return {"status": "error", "error": str(e)}

    def _process_alert(self, alert: Dict[str, Any]) -> Dict[str, Any]:
        """Process individual alert"""
        try:
            status = alert.get("status", "unknown")
            labels = alert.get("labels", {})
            annotations = alert.get("annotations", {})

            # Extract alert data
            alert_data = {
                "alertname": labels.get("alertname", "Unknown"),
                "severity": labels.get("severity", "unknown"),
                "service": labels.get("service", "unknown"),
                "instance": labels.get("instance", "unknown"),
                "component": labels.get("component", ""),
                "description": annotations.get("description", ""),
                "runbook_url": annotations.get("runbook_url", ""),
                "value": annotations.get("value", ""),
                "status": status,
            }

            if not self.github_manager:
                return {"status": "error", "error": "GitHub manager not initialized"}

            if status.lower() == "firing":
                # Create or update issue for firing alert
                issue_number = self.github_manager.create_github_issue(alert_data)
                if issue_number:
                    return {
                        "status": "success",
                        "action": "created_issue",
                        "issue_number": issue_number,
                    }
                else:
                    return {"status": "error", "error": "Failed to create issue"}

            elif status.lower() == "resolved":
                # Find and close resolved alert issue
                existing_issue = self.github_manager._find_existing_issue(alert_data)
                if existing_issue:
                    success = self.github_manager.close_resolved_issue(
                        existing_issue, alert_data
                    )
                    if success:
                        return {
                            "status": "success",
                            "action": "closed_issue",
                            "issue_number": existing_issue,
                        }
                    else:
                        return {"status": "error", "error": "Failed to close issue"}
                else:
                    return {
                        "status": "info",
                        "message": "No existing issue found to close",
                    }

            return {
                "status": "info",
                "message": f"No action taken for status: {status}",
            }

        except Exception as e:
            logger.error(f"Error processing alert: {e}")
            return {"status": "error", "error": str(e)}


def send_notification(alert_data: Dict[str, Any], channel: str = "github") -> bool:
    """Send notification through specified channel"""
    try:
        if channel == "github":
            handler = AlertWebhookHandler()
            if handler.github_manager:
                issue_number = handler.github_manager.create_github_issue(alert_data)
                return issue_number is not None

        logger.warning(f"Unsupported notification channel: {channel}")
        return False

    except Exception as e:
        logger.error(f"Error sending notification: {e}")
        return False


# Flask app for webhook endpoint
app = Flask(__name__)
webhook_handler = AlertWebhookHandler()


@app.route("/webhook/github", methods=["POST"])
def github_webhook():
    """GitHub webhook endpoint"""
    try:
        data = request.get_json()
        result = webhook_handler.handle_webhook(data)
        return jsonify(result)

    except Exception as e:
        logger.error(f"Webhook endpoint error: {e}")
        return jsonify({"status": "error", "error": str(e)}), 500


@app.route("/webhook/test", methods=["POST"])
def test_webhook():
    """Test webhook endpoint"""
    try:
        data = request.get_json()
        logger.info(f"Test webhook received: {data}")
        return jsonify({"status": "success", "message": "Test webhook received"})

    except Exception as e:
        logger.error(f"Test webhook error: {e}")
        return jsonify({"status": "error", "error": str(e)}), 500


@app.route("/health", methods=["GET"])
def health_check():
    """Health check endpoint"""
    return jsonify(
        {
            "status": "healthy",
            "github_manager": webhook_handler.github_manager is not None,
            "timestamp": datetime.utcnow().isoformat(),
        }
    )


if __name__ == "__main__":
    # Load environment variables
    import sys

    sys.path.append("/home/yasar/cicd_project")

    # Load .env file
    env_file = Path("/home/yasar/cicd_project/.env")
    if env_file.exists():
        with open(env_file) as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    key, value = line.split("=", 1)
                    os.environ[key] = value

    # Start Flask app
    logger.info("Starting alert webhook handler...")
    app.run(host="0.0.0.0", port=8080, debug=False)
