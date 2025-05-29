#!/usr/bin/env python3
"""
Reddit Sentiment Pipeline - Backup Manager

This script handles backup and recovery operations for the sentiment analysis pipeline.

Features:
- Automated daily and weekly backups
- Database backup with integrity checks
- Configuration and log backup
- Backup rotation and cleanup
- Recovery procedures
- Backup verification

Author: GitHub Copilot
Date: 2024
"""

import argparse
import hashlib
import json
import logging
import shutil
import sqlite3
import subprocess
import sys
import tarfile
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional


class BackupManager:
    """Comprehensive backup and recovery system"""

    def __init__(self, project_root: str = "/home/cayir/cicd_project"):
        self.project_root = Path(project_root)
        self.backup_root = self.project_root / "backups"
        self.config_path = self.project_root / "config"
        self.data_path = self.project_root / "data"
        self.log_path = Path("/var/log/reddit-sentiment-pipeline")

        # Backup configuration
        self.backup_config = {
            "daily_retention_days": 7,
            "weekly_retention_weeks": 4,
            "monthly_retention_months": 12,
            "compression_level": 6,
            "verify_backups": True,
            "backup_database": True,
            "backup_config": True,
            "backup_logs": True,
        }

        # Setup logging
        self.setup_logging()

        # Ensure backup directory exists
        self.backup_root.mkdir(parents=True, exist_ok=True)

        # Load configuration
        self.load_configuration()

    def setup_logging(self):
        """Setup logging configuration"""
        log_file = self.log_path / "backup.log"
        log_file.parent.mkdir(parents=True, exist_ok=True)

        logging.basicConfig(
            level=logging.INFO,
            format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
            handlers=[logging.FileHandler(log_file), logging.StreamHandler(sys.stdout)],
        )
        self.logger = logging.getLogger(__name__)

    def load_configuration(self):
        """Load backup configuration"""
        try:
            config_file = self.config_path / "backup.yml"
            if config_file.exists():
                import yaml

                with open(config_file, "r") as f:
                    config = yaml.safe_load(f)
                    self.backup_config.update(config.get("backup", {}))
                self.logger.info("Backup configuration loaded")
            else:
                self.logger.info("Using default backup configuration")
        except Exception as e:
            self.logger.error(f"Error loading backup configuration: {e}")

    def calculate_checksum(self, file_path: Path) -> str:
        """Calculate MD5 checksum for file verification"""
        hash_md5 = hashlib.md5()
        try:
            with open(file_path, "rb") as f:
                for chunk in iter(lambda: f.read(4096), b""):
                    hash_md5.update(chunk)
            return hash_md5.hexdigest()
        except Exception as e:
            self.logger.error(f"Error calculating checksum for {file_path}: {e}")
            return ""

    def backup_database(self, backup_dir: Path) -> bool:
        """Backup SQLite database with integrity check"""
        try:
            self.logger.info("Starting database backup...")

            db_path = self.data_path / "reddit_posts.db"
            if not db_path.exists():
                self.logger.warning("Database file not found, skipping database backup")
                return True

            # Create database backup directory
            db_backup_dir = backup_dir / "database"
            db_backup_dir.mkdir(parents=True, exist_ok=True)

            # Check database integrity before backup
            try:
                with sqlite3.connect(str(db_path)) as conn:
                    cursor = conn.cursor()
                    cursor.execute("PRAGMA integrity_check")
                    integrity_result = cursor.fetchone()[0]

                    if integrity_result != "ok":
                        self.logger.error(
                            f"Database integrity check failed: {integrity_result}"
                        )
                        return False
            except Exception as e:
                self.logger.error(f"Database integrity check error: {e}")
                return False

            # Create database backup
            backup_db_path = db_backup_dir / "reddit_posts.db"
            shutil.copy2(db_path, backup_db_path)

            # Create database dump for additional safety
            dump_path = db_backup_dir / "reddit_posts_dump.sql"
            try:
                with open(dump_path, "w") as f:
                    subprocess.run(
                        ["sqlite3", str(db_path), ".dump"], stdout=f, check=True
                    )
            except Exception as e:
                self.logger.warning(f"Database dump creation failed: {e}")

            # Calculate checksums
            db_checksum = self.calculate_checksum(backup_db_path)

            # Save backup metadata
            metadata = {
                "type": "database",
                "timestamp": datetime.now().isoformat(),
                "files": {
                    "reddit_posts.db": {
                        "size": backup_db_path.stat().st_size,
                        "checksum": db_checksum,
                    }
                },
                "integrity_check": "passed",
            }

            metadata_path = db_backup_dir / "metadata.json"
            with open(metadata_path, "w") as f:
                json.dump(metadata, f, indent=2)

            self.logger.info("Database backup completed successfully")
            return True

        except Exception as e:
            self.logger.error(f"Database backup failed: {e}")
            return False

    def backup_configuration(self, backup_dir: Path) -> bool:
        """Backup configuration files"""
        try:
            self.logger.info("Starting configuration backup...")

            if not self.config_path.exists():
                self.logger.warning(
                    "Configuration directory not found, skipping config backup"
                )
                return True

            config_backup_dir = backup_dir / "config"
            config_backup_dir.mkdir(parents=True, exist_ok=True)

            # Copy all configuration files
            for config_file in self.config_path.iterdir():
                if config_file.is_file():
                    dest_file = config_backup_dir / config_file.name
                    shutil.copy2(config_file, dest_file)

            # Create metadata
            metadata = {
                "type": "configuration",
                "timestamp": datetime.now().isoformat(),
                "files": {},
            }

            for config_file in config_backup_dir.iterdir():
                if config_file.is_file() and config_file.name != "metadata.json":
                    metadata["files"][config_file.name] = {
                        "size": config_file.stat().st_size,
                        "checksum": self.calculate_checksum(config_file),
                    }

            metadata_path = config_backup_dir / "metadata.json"
            with open(metadata_path, "w") as f:
                json.dump(metadata, f, indent=2)

            self.logger.info("Configuration backup completed successfully")
            return True

        except Exception as e:
            self.logger.error(f"Configuration backup failed: {e}")
            return False

    def backup_logs(self, backup_dir: Path) -> bool:
        """Backup recent log files"""
        try:
            self.logger.info("Starting logs backup...")

            if not self.log_path.exists():
                self.logger.warning("Log directory not found, skipping logs backup")
                return True

            logs_backup_dir = backup_dir / "logs"
            logs_backup_dir.mkdir(parents=True, exist_ok=True)

            # Backup recent log files (last 7 days)
            cutoff_date = datetime.now() - timedelta(days=7)

            metadata = {
                "type": "logs",
                "timestamp": datetime.now().isoformat(),
                "files": {},
            }

            for log_file in self.log_path.iterdir():
                if log_file.is_file():
                    file_mtime = datetime.fromtimestamp(log_file.stat().st_mtime)

                    if file_mtime > cutoff_date:
                        dest_file = logs_backup_dir / log_file.name
                        shutil.copy2(log_file, dest_file)

                        metadata["files"][log_file.name] = {
                            "size": dest_file.stat().st_size,
                            "checksum": self.calculate_checksum(dest_file),
                            "modified": file_mtime.isoformat(),
                        }

            metadata_path = logs_backup_dir / "metadata.json"
            with open(metadata_path, "w") as f:
                json.dump(metadata, f, indent=2)

            self.logger.info("Logs backup completed successfully")
            return True

        except Exception as e:
            self.logger.error(f"Logs backup failed: {e}")
            return False

    def create_backup(self, backup_type: str = "daily") -> bool:
        """Create a complete backup"""
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_name = f"{backup_type}_{timestamp}"
            backup_dir = self.backup_root / backup_name

            self.logger.info(f"Starting {backup_type} backup: {backup_name}")

            # Create backup directory
            backup_dir.mkdir(parents=True, exist_ok=True)

            # Track backup results
            backup_results = {
                "type": backup_type,
                "timestamp": datetime.now().isoformat(),
                "status": "in_progress",
                "components": {},
            }

            # Backup components
            if self.backup_config["backup_database"]:
                backup_results["components"]["database"] = self.backup_database(
                    backup_dir
                )

            if self.backup_config["backup_config"]:
                backup_results["components"]["configuration"] = (
                    self.backup_configuration(backup_dir)
                )

            if self.backup_config["backup_logs"]:
                backup_results["components"]["logs"] = self.backup_logs(backup_dir)

            # Check if all components succeeded
            all_success = all(backup_results["components"].values())
            backup_results["status"] = "completed" if all_success else "partial_failure"

            # Create compressed archive
            if all_success:
                archive_path = self.backup_root / f"{backup_name}.tar.gz"

                self.logger.info(f"Creating compressed archive: {archive_path}")

                with tarfile.open(
                    archive_path,
                    "w:gz",
                    compresslevel=self.backup_config["compression_level"],
                ) as tar:
                    tar.add(backup_dir, arcname=backup_name)

                # Remove uncompressed backup directory
                shutil.rmtree(backup_dir)

                # Update backup results with archive info
                backup_results["archive"] = {
                    "path": str(archive_path),
                    "size": archive_path.stat().st_size,
                    "checksum": self.calculate_checksum(archive_path),
                }

                # Verify backup if configured
                if self.backup_config["verify_backups"]:
                    backup_results["verification"] = self.verify_backup(archive_path)

            # Save backup manifest
            manifest_path = self.backup_root / f"{backup_name}_manifest.json"
            with open(manifest_path, "w") as f:
                json.dump(backup_results, f, indent=2)

            if all_success:
                self.logger.info(f"Backup {backup_name} completed successfully")
            else:
                self.logger.error(f"Backup {backup_name} completed with failures")

            return all_success

        except Exception as e:
            self.logger.error(f"Backup creation failed: {e}")
            return False

    def verify_backup(self, archive_path: Path) -> Dict:
        """Verify backup integrity"""
        try:
            self.logger.info(f"Verifying backup: {archive_path}")

            verification_result = {
                "status": "unknown",
                "checks": {},
                "timestamp": datetime.now().isoformat(),
            }

            # Check if archive exists and is readable
            if not archive_path.exists():
                verification_result["status"] = "failed"
                verification_result["checks"]["file_exists"] = False
                return verification_result

            verification_result["checks"]["file_exists"] = True

            # Test archive integrity
            try:
                with tarfile.open(archive_path, "r:gz") as tar:
                    # List contents without extracting
                    members = tar.getmembers()
                    verification_result["checks"]["archive_integrity"] = True
                    verification_result["checks"]["file_count"] = len(members)
            except Exception as e:
                verification_result["checks"]["archive_integrity"] = False
                verification_result["checks"]["error"] = str(e)
                verification_result["status"] = "failed"
                return verification_result

            # Check file size is reasonable (not empty, not too small)
            file_size = archive_path.stat().st_size
            verification_result["checks"]["file_size"] = file_size
            verification_result["checks"]["size_check"] = (
                file_size > 1024
            )  # At least 1KB

            # Overall verification status
            all_checks_passed = all(
                check
                for check in verification_result["checks"].values()
                if isinstance(check, bool)
            )

            verification_result["status"] = "passed" if all_checks_passed else "failed"

            return verification_result

        except Exception as e:
            self.logger.error(f"Backup verification failed: {e}")
            return {
                "status": "error",
                "error": str(e),
                "timestamp": datetime.now().isoformat(),
            }

    def restore_backup(
        self, backup_name: str, restore_path: Optional[Path] = None
    ) -> bool:
        """Restore from backup"""
        try:
            if restore_path is None:
                restore_path = self.project_root / "restore"

            self.logger.info(f"Starting restore from backup: {backup_name}")

            # Find backup archive
            archive_path = self.backup_root / f"{backup_name}.tar.gz"

            if not archive_path.exists():
                self.logger.error(f"Backup archive not found: {archive_path}")
                return False

            # Verify backup before restore
            verification = self.verify_backup(archive_path)
            if verification["status"] != "passed":
                self.logger.error("Backup verification failed, aborting restore")
                return False

            # Create restore directory
            restore_path.mkdir(parents=True, exist_ok=True)

            # Extract backup
            self.logger.info(f"Extracting backup to: {restore_path}")

            with tarfile.open(archive_path, "r:gz") as tar:
                tar.extractall(path=restore_path)

            self.logger.info("Backup restore completed successfully")
            return True

        except Exception as e:
            self.logger.error(f"Backup restore failed: {e}")
            return False

    def cleanup_old_backups(self) -> bool:
        """Clean up old backups based on retention policy"""
        try:
            self.logger.info("Starting backup cleanup...")

            now = datetime.now()
            deleted_count = 0

            # Get all backup files
            backup_files = []
            for file_path in self.backup_root.glob("*.tar.gz"):
                try:
                    # Parse timestamp from filename
                    parts = file_path.stem.split("_")
                    if len(parts) >= 3:
                        backup_type = parts[0]
                        date_str = parts[1]
                        time_str = parts[2]

                        timestamp = datetime.strptime(
                            f"{date_str}_{time_str}", "%Y%m%d_%H%M%S"
                        )

                        backup_files.append(
                            {
                                "path": file_path,
                                "type": backup_type,
                                "timestamp": timestamp,
                            }
                        )
                except Exception as e:
                    self.logger.warning(
                        f"Could not parse backup filename: {file_path}: {e}"
                    )

            # Sort by timestamp (newest first)
            backup_files.sort(key=lambda x: x["timestamp"], reverse=True)

            # Apply retention policy
            for backup in backup_files:
                should_delete = False
                age = now - backup["timestamp"]

                if backup["type"] == "daily":
                    should_delete = (
                        age.days > self.backup_config["daily_retention_days"]
                    )
                elif backup["type"] == "weekly":
                    should_delete = age.days > (
                        self.backup_config["weekly_retention_weeks"] * 7
                    )
                elif backup["type"] == "monthly":
                    should_delete = age.days > (
                        self.backup_config["monthly_retention_months"] * 30
                    )

                if should_delete:
                    try:
                        backup["path"].unlink()

                        # Also delete manifest file
                        manifest_path = (
                            backup["path"].parent
                            / f"{backup['path'].stem}_manifest.json"
                        )
                        if manifest_path.exists():
                            manifest_path.unlink()

                        deleted_count += 1
                        self.logger.info(f"Deleted old backup: {backup['path'].name}")

                    except Exception as e:
                        self.logger.error(
                            f"Error deleting backup {backup['path']}: {e}"
                        )

            self.logger.info(
                f"Backup cleanup completed. Deleted {deleted_count} old backups."
            )
            return True

        except Exception as e:
            self.logger.error(f"Backup cleanup failed: {e}")
            return False

    def list_backups(self) -> List[Dict]:
        """List available backups"""
        backups = []

        try:
            for archive_path in self.backup_root.glob("*.tar.gz"):
                manifest_path = self.backup_root / f"{archive_path.stem}_manifest.json"

                backup_info = {
                    "name": archive_path.stem,
                    "path": str(archive_path),
                    "size": archive_path.stat().st_size,
                    "created": datetime.fromtimestamp(
                        archive_path.stat().st_ctime
                    ).isoformat(),
                }

                # Load manifest if available
                if manifest_path.exists():
                    try:
                        with open(manifest_path, "r") as f:
                            manifest = json.load(f)
                            backup_info.update(manifest)
                    except Exception as e:
                        self.logger.warning(
                            f"Could not load manifest for {archive_path}: {e}"
                        )

                backups.append(backup_info)

        except Exception as e:
            self.logger.error(f"Error listing backups: {e}")

        return sorted(backups, key=lambda x: x["created"], reverse=True)


def main():
    """Main function"""
    parser = argparse.ArgumentParser(
        description="Reddit Sentiment Pipeline Backup Manager"
    )
    parser.add_argument("--daily", action="store_true", help="Create daily backup")
    parser.add_argument("--weekly", action="store_true", help="Create weekly backup")
    parser.add_argument("--monthly", action="store_true", help="Create monthly backup")
    parser.add_argument("--cleanup", action="store_true", help="Clean up old backups")
    parser.add_argument("--list", action="store_true", help="List available backups")
    parser.add_argument(
        "--restore", type=str, help="Restore from backup (provide backup name)"
    )
    parser.add_argument(
        "--verify", type=str, help="Verify backup integrity (provide backup name)"
    )
    parser.add_argument(
        "--project-root",
        type=str,
        default="/home/cayir/cicd_project",
        help="Project root directory",
    )

    args = parser.parse_args()

    # Create backup manager
    backup_manager = BackupManager(project_root=args.project_root)

    success = True

    if args.daily:
        success = backup_manager.create_backup("daily")
    elif args.weekly:
        success = backup_manager.create_backup("weekly")
    elif args.monthly:
        success = backup_manager.create_backup("monthly")
    elif args.cleanup:
        success = backup_manager.cleanup_old_backups()
    elif args.list:
        backups = backup_manager.list_backups()
        print(f"Found {len(backups)} backups:")
        for backup in backups:
            print(f"  {backup['name']} - {backup['created']} ({backup['size']} bytes)")
    elif args.restore:
        success = backup_manager.restore_backup(args.restore)
    elif args.verify:
        archive_path = backup_manager.backup_root / f"{args.verify}.tar.gz"
        result = backup_manager.verify_backup(archive_path)
        print(f"Verification result: {result['status']}")
        if result["status"] != "passed":
            print(f"Details: {json.dumps(result, indent=2)}")
    else:
        parser.print_help()
        success = False

    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
