#!/usr/bin/env python3
"""
Reddit Sentiment Pipeline - Health Check Script

This script monitors the health of the sentiment analysis pipeline and
provides health status information for systemd monitoring.

Features:
- Service health monitoring
- Resource usage tracking
- Database connectivity checks
- API endpoint validation
- Automatic restart capabilities
- Alerting integration

Author: GitHub Copilot
Date: 2024
"""

import argparse
import json
import logging
import sqlite3
import subprocess
import sys
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, Tuple

import psutil
import requests


class HealthCheckMonitor:
    """Health monitoring system for Reddit sentiment pipeline"""

    def __init__(self, config_path: str = "/home/cayir/cicd_project/config"):
        self.config_path = Path(config_path)
        self.project_root = Path("/home/cayir/cicd_project")
        self.service_name = "reddit-sentiment-pipeline"
        self.log_path = Path("/var/log/reddit-sentiment-pipeline")

        # Setup logging
        self.setup_logging()

        # Health check configuration
        self.health_config = {
            "max_memory_mb": 2048,
            "max_cpu_percent": 80,
            "max_disk_usage_percent": 85,
            "max_response_time_ms": 5000,
            "check_interval_seconds": 300,  # 5 minutes
            "restart_threshold": 3,  # Failed checks before restart
            "alert_threshold": 5,  # Failed checks before alerting
        }

        # Health status tracking
        self.health_status = {
            "overall": "unknown",
            "service": "unknown",
            "resources": "unknown",
            "database": "unknown",
            "api": "unknown",
            "last_check": None,
            "consecutive_failures": 0,
            "uptime": None,
        }

        # Load configuration
        self.load_configuration()

    def setup_logging(self):
        """Setup logging configuration"""
        log_file = self.log_path / "health_check.log"
        log_file.parent.mkdir(parents=True, exist_ok=True)

        logging.basicConfig(
            level=logging.INFO,
            format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
            handlers=[logging.FileHandler(log_file), logging.StreamHandler(sys.stdout)],
        )
        self.logger = logging.getLogger(__name__)

    def load_configuration(self):
        """Load health check configuration"""
        try:
            config_file = self.config_path / "monitoring.yml"
            if config_file.exists():
                import yaml

                with open(config_file, "r") as f:
                    config = yaml.safe_load(f)
                    self.health_config.update(config.get("health_check", {}))
                self.logger.info("Health check configuration loaded")
            else:
                self.logger.warning("Monitoring config not found, using defaults")
        except Exception as e:
            self.logger.error(f"Error loading configuration: {e}")

    def check_service_status(self) -> Tuple[bool, str]:
        """Check systemd service status"""
        try:
            result = subprocess.run(
                ["systemctl", "is-active", f"{self.service_name}.service"],
                capture_output=True,
                text=True,
                timeout=10,
            )

            status = result.stdout.strip()
            is_healthy = status == "active"

            if is_healthy:
                # Get service uptime
                uptime_result = subprocess.run(
                    [
                        "systemctl",
                        "show",
                        f"{self.service_name}.service",
                        "--property=ActiveEnterTimestamp",
                    ],
                    capture_output=True,
                    text=True,
                    timeout=10,
                )

                if uptime_result.returncode == 0:
                    timestamp_line = uptime_result.stdout.strip()
                    if "=" in timestamp_line:
                        timestamp_str = timestamp_line.split("=", 1)[1]
                        if timestamp_str and timestamp_str != "n/a":
                            self.health_status["uptime"] = timestamp_str

                return True, "Service is active"
            else:
                return False, f"Service status: {status}"

        except subprocess.TimeoutExpired:
            return False, "Service check timed out"
        except Exception as e:
            return False, f"Service check error: {e}"

    def check_resource_usage(self) -> Tuple[bool, str]:
        """Check system resource usage"""
        try:
            # Check memory usage
            memory = psutil.virtual_memory()
            memory_usage_mb = (memory.total - memory.available) / 1024 / 1024
            memory_percent = memory.percent

            # Check CPU usage
            cpu_percent = psutil.cpu_percent(interval=1)

            # Check disk usage
            disk = psutil.disk_usage("/")
            disk_percent = (disk.used / disk.total) * 100

            # Evaluate health
            issues = []

            if memory_usage_mb > self.health_config["max_memory_mb"]:
                issues.append(f"High memory usage: {memory_usage_mb:.0f}MB")

            if cpu_percent > self.health_config["max_cpu_percent"]:
                issues.append(f"High CPU usage: {cpu_percent:.1f}%")

            if disk_percent > self.health_config["max_disk_usage_percent"]:
                issues.append(f"High disk usage: {disk_percent:.1f}%")

            if issues:
                return False, "; ".join(issues)
            else:
                return (
                    True,
                    f"Resources OK (CPU: {cpu_percent:.1f}%, Memory: {memory_percent:.1f}%, Disk: {disk_percent:.1f}%)",
                )

        except Exception as e:
            return False, f"Resource check error: {e}"

    def check_database_connectivity(self) -> Tuple[bool, str]:
        """Check database connectivity and integrity"""
        try:
            db_path = self.project_root / "data" / "reddit_posts.db"

            if not db_path.exists():
                return False, "Database file does not exist"

            # Test database connection
            with sqlite3.connect(str(db_path), timeout=5) as conn:
                cursor = conn.cursor()

                # Check if main table exists
                cursor.execute("""
                    SELECT name FROM sqlite_master 
                    WHERE type='table' AND name='reddit_posts'
                """)

                if not cursor.fetchone():
                    return False, "Main table 'reddit_posts' not found"

                # Check recent data
                cursor.execute("""
                    SELECT COUNT(*) FROM reddit_posts 
                    WHERE created_at > datetime('now', '-1 day')
                """)

                recent_count = cursor.fetchone()[0]

                return True, f"Database OK ({recent_count} posts in last 24h)"

        except sqlite3.Error as e:
            return False, f"Database error: {e}"
        except Exception as e:
            return False, f"Database check error: {e}"

    def check_api_endpoints(self) -> Tuple[bool, str]:
        """Check API endpoints (metrics, health)"""
        try:
            endpoints = [
                ("http://localhost:8000/metrics", "Metrics endpoint"),
                ("http://localhost:8000/health", "Health endpoint"),
            ]

            results = []
            all_healthy = True

            for url, name in endpoints:
                try:
                    start_time = time.time()
                    response = requests.get(url, timeout=10)
                    response_time = (time.time() - start_time) * 1000

                    if response.status_code == 200:
                        if response_time > self.health_config["max_response_time_ms"]:
                            results.append(
                                f"{name}: Slow response ({response_time:.0f}ms)"
                            )
                            all_healthy = False
                        else:
                            results.append(f"{name}: OK ({response_time:.0f}ms)")
                    else:
                        results.append(f"{name}: HTTP {response.status_code}")
                        all_healthy = False

                except requests.RequestException as e:
                    results.append(f"{name}: Connection failed - {e}")
                    all_healthy = False

            return all_healthy, "; ".join(results)

        except Exception as e:
            return False, f"API check error: {e}"

    def check_log_files(self) -> Tuple[bool, str]:
        """Check log files for errors and recent activity"""
        try:
            log_file = self.log_path / "application.log"

            if not log_file.exists():
                return False, "Application log file not found"

            # Check if log file has been updated recently
            file_mtime = datetime.fromtimestamp(log_file.stat().st_mtime)
            if datetime.now() - file_mtime > timedelta(hours=4):
                return False, f"Log file not updated recently (last: {file_mtime})"

            # Check for recent errors
            try:
                with open(log_file, "r") as f:
                    # Read last 1000 lines
                    lines = f.readlines()[-1000:]

                error_count = 0
                for line in lines:
                    if "ERROR" in line.upper():
                        error_count += 1

                if error_count > 10:  # More than 10 errors in recent logs
                    return False, f"High error count in logs: {error_count} errors"

                return True, f"Logs OK ({error_count} recent errors)"

            except Exception as e:
                return False, f"Error reading log file: {e}"

        except Exception as e:
            return False, f"Log check error: {e}"

    def perform_health_check(self) -> Dict:
        """Perform comprehensive health check"""
        self.logger.info("Starting health check...")

        checks = [
            ("service", self.check_service_status),
            ("resources", self.check_resource_usage),
            ("database", self.check_database_connectivity),
            ("api", self.check_api_endpoints),
            ("logs", self.check_log_files),
        ]

        results = {}
        all_healthy = True

        for check_name, check_func in checks:
            try:
                is_healthy, message = check_func()
                results[check_name] = {
                    "healthy": is_healthy,
                    "message": message,
                    "timestamp": datetime.now().isoformat(),
                }

                if not is_healthy:
                    all_healthy = False
                    self.logger.warning(
                        f"Health check failed for {check_name}: {message}"
                    )
                else:
                    self.logger.info(f"Health check passed for {check_name}: {message}")

            except Exception as e:
                results[check_name] = {
                    "healthy": False,
                    "message": f"Check error: {e}",
                    "timestamp": datetime.now().isoformat(),
                }
                all_healthy = False
                self.logger.error(f"Health check error for {check_name}: {e}")

        # Update overall health status
        self.health_status.update(
            {
                "overall": "healthy" if all_healthy else "unhealthy",
                "last_check": datetime.now().isoformat(),
                "details": results,
            }
        )

        if not all_healthy:
            self.health_status["consecutive_failures"] += 1
        else:
            self.health_status["consecutive_failures"] = 0

        return self.health_status

    def handle_unhealthy_service(self):
        """Handle unhealthy service by attempting restart"""
        if (
            self.health_status["consecutive_failures"]
            >= self.health_config["restart_threshold"]
        ):
            self.logger.warning(
                f"Service unhealthy for {self.health_status['consecutive_failures']} consecutive checks, attempting restart..."
            )

            try:
                # Restart the service
                result = subprocess.run(
                    ["systemctl", "restart", f"{self.service_name}.service"],
                    capture_output=True,
                    text=True,
                    timeout=30,
                )

                if result.returncode == 0:
                    self.logger.info("Service restart successful")
                    self.health_status["consecutive_failures"] = 0

                    # Wait a bit for service to start
                    time.sleep(10)

                    # Re-check health
                    self.perform_health_check()
                else:
                    self.logger.error(f"Service restart failed: {result.stderr}")

            except Exception as e:
                self.logger.error(f"Error restarting service: {e}")

    def send_alert(self, alert_type: str, message: str):
        """Send alert (placeholder for integration with alerting systems)"""
        self.logger.critical(f"ALERT [{alert_type}]: {message}")

        # TODO: Integrate with alerting systems like:
        # - Slack webhook
        # - Email notifications
        # - PagerDuty
        # - Prometheus AlertManager

        # For now, just log to a special alerts file
        alert_file = self.log_path / "alerts.log"
        with open(alert_file, "a") as f:
            f.write(f"{datetime.now().isoformat()} - {alert_type}: {message}\n")

    def save_health_status(self):
        """Save health status to JSON file for monitoring systems"""
        status_file = self.project_root / "data" / "health_status.json"

        try:
            with open(status_file, "w") as f:
                json.dump(self.health_status, f, indent=2)
        except Exception as e:
            self.logger.error(f"Error saving health status: {e}")

    def run_continuous_monitoring(self, interval: int = None):
        """Run continuous health monitoring"""
        if interval is None:
            interval = self.health_config["check_interval_seconds"]

        self.logger.info(f"Starting continuous monitoring (interval: {interval}s)")

        try:
            while True:
                health_status = self.perform_health_check()
                self.save_health_status()

                # Handle unhealthy service
                if health_status["overall"] != "healthy":
                    self.handle_unhealthy_service()

                    # Send alert if threshold reached
                    if (
                        self.health_status["consecutive_failures"]
                        >= self.health_config["alert_threshold"]
                    ):
                        self.send_alert(
                            "SERVICE_UNHEALTHY",
                            f"Service has been unhealthy for {self.health_status['consecutive_failures']} consecutive checks",
                        )

                # Wait for next check
                time.sleep(interval)

        except KeyboardInterrupt:
            self.logger.info("Health monitoring stopped by user")
        except Exception as e:
            self.logger.error(f"Health monitoring error: {e}")
            raise


def main():
    """Main function"""
    parser = argparse.ArgumentParser(
        description="Reddit Sentiment Pipeline Health Check"
    )
    parser.add_argument(
        "--once", action="store_true", help="Run health check once and exit"
    )
    parser.add_argument(
        "--continuous", action="store_true", help="Run continuous monitoring"
    )
    parser.add_argument(
        "--interval",
        type=int,
        default=300,
        help="Check interval in seconds (default: 300)",
    )
    parser.add_argument(
        "--config",
        type=str,
        default="/home/cayir/cicd_project/config",
        help="Configuration directory",
    )
    parser.add_argument(
        "--json", action="store_true", help="Output results in JSON format"
    )

    args = parser.parse_args()

    # Create health monitor
    monitor = HealthCheckMonitor(config_path=args.config)

    if args.once:
        # Run single health check
        health_status = monitor.perform_health_check()
        monitor.save_health_status()

        if args.json:
            print(json.dumps(health_status, indent=2))
        else:
            print(f"Overall Health: {health_status['overall']}")
            print(f"Last Check: {health_status['last_check']}")
            print(f"Consecutive Failures: {health_status['consecutive_failures']}")

            if "details" in health_status:
                print("\nDetailed Results:")
                for check_name, result in health_status["details"].items():
                    status = "✅" if result["healthy"] else "❌"
                    print(f"  {status} {check_name}: {result['message']}")

        # Exit with appropriate code
        sys.exit(0 if health_status["overall"] == "healthy" else 1)

    elif args.continuous:
        # Run continuous monitoring
        monitor.run_continuous_monitoring(interval=args.interval)
    else:
        # Default: run once
        health_status = monitor.perform_health_check()
        monitor.save_health_status()
        print(f"Health Status: {health_status['overall']}")
        sys.exit(0 if health_status["overall"] == "healthy" else 1)


if __name__ == "__main__":
    main()
