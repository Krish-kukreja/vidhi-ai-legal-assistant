"""
Data Refresh Scheduler for VIDHI
Schedules periodic data pipeline runs to keep knowledge base current.

Features:
- Cron-like scheduling
- Incremental updates
- Change detection
- Manual refresh trigger
- Refresh notifications
"""

import os
import logging
import subprocess
import json
from datetime import datetime
from typing import Dict, Any, Optional
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger

logger = logging.getLogger(__name__)


class DataRefreshScheduler:
    """Scheduler for periodic data refresh"""

    def __init__(self):
        self.scheduler = BackgroundScheduler()
        self.last_refresh = None
        self.refresh_history = []
        self.is_running = False

    def start(self):
        """Start the scheduler"""
        if self.is_running:
            logger.warning("Scheduler already running")
            return

        # Schedule daily refresh at 2 AM
        self.scheduler.add_job(
            self.refresh_all_data,
            CronTrigger(hour=2, minute=0),
            id="daily_refresh",
            name="Daily Data Refresh",
            replace_existing=True,
        )

        # Schedule weekly full refresh on Sunday at 3 AM
        self.scheduler.add_job(
            self.full_refresh,
            CronTrigger(day_of_week="sun", hour=3, minute=0),
            id="weekly_full_refresh",
            name="Weekly Full Refresh",
            replace_existing=True,
        )

        self.scheduler.start()
        self.is_running = True
        logger.info("Data refresh scheduler started")

    def stop(self):
        """Stop the scheduler"""
        if not self.is_running:
            return

        self.scheduler.shutdown()
        self.is_running = False
        logger.info("Data refresh scheduler stopped")

    def refresh_all_data(self):
        """Run incremental data refresh"""
        logger.info("Starting incremental data refresh...")

        start_time = datetime.now()

        try:
            # Run data pipeline
            result = subprocess.run(
                ["python", "data_pipeline/run_pipeline.py"],
                cwd=os.path.join(os.path.dirname(__file__), ".."),
                capture_output=True,
                text=True,
                timeout=3600,  # 1 hour timeout
            )

            success = result.returncode == 0

            # Record refresh
            refresh_record = {
                "timestamp": start_time.isoformat(),
                "type": "incremental",
                "success": success,
                "duration_seconds": (datetime.now() - start_time).total_seconds(),
                "stdout": (
                    result.stdout[-1000:] if result.stdout else ""
                ),  # Last 1000 chars
                "stderr": result.stderr[-1000:] if result.stderr else "",
            }

            self.refresh_history.append(refresh_record)
            self.last_refresh = start_time

            # Keep only last 30 refreshes
            if len(self.refresh_history) > 30:
                self.refresh_history = self.refresh_history[-30:]

            if success:
                logger.info(
                    f"Data refresh completed successfully in {refresh_record['duration_seconds']:.1f}s"
                )
            else:
                logger.error(f"Data refresh failed: {result.stderr}")

            return refresh_record

        except subprocess.TimeoutExpired:
            logger.error("Data refresh timed out after 1 hour")
            return {
                "timestamp": start_time.isoformat(),
                "type": "incremental",
                "success": False,
                "error": "Timeout after 1 hour",
            }
        except Exception as e:
            logger.error(f"Data refresh failed: {e}")
            return {
                "timestamp": start_time.isoformat(),
                "type": "incremental",
                "success": False,
                "error": str(e),
            }

    def full_refresh(self):
        """Run full data refresh (re-scrape everything)"""
        logger.info("Starting full data refresh...")

        start_time = datetime.now()

        try:
            # Run data pipeline without skipping anything
            result = subprocess.run(
                ["python", "data_pipeline/run_pipeline.py"],
                cwd=os.path.join(os.path.dirname(__file__), ".."),
                capture_output=True,
                text=True,
                timeout=7200,  # 2 hour timeout for full refresh
            )

            success = result.returncode == 0

            # Record refresh
            refresh_record = {
                "timestamp": start_time.isoformat(),
                "type": "full",
                "success": success,
                "duration_seconds": (datetime.now() - start_time).total_seconds(),
                "stdout": result.stdout[-1000:] if result.stdout else "",
                "stderr": result.stderr[-1000:] if result.stderr else "",
            }

            self.refresh_history.append(refresh_record)
            self.last_refresh = start_time

            if success:
                logger.info(
                    f"Full data refresh completed successfully in {refresh_record['duration_seconds']:.1f}s"
                )
            else:
                logger.error(f"Full data refresh failed: {result.stderr}")

            return refresh_record

        except subprocess.TimeoutExpired:
            logger.error("Full data refresh timed out after 2 hours")
            return {
                "timestamp": start_time.isoformat(),
                "type": "full",
                "success": False,
                "error": "Timeout after 2 hours",
            }
        except Exception as e:
            logger.error(f"Full data refresh failed: {e}")
            return {
                "timestamp": start_time.isoformat(),
                "type": "full",
                "success": False,
                "error": str(e),
            }

    def trigger_manual_refresh(
        self, refresh_type: str = "incremental"
    ) -> Dict[str, Any]:
        """Manually trigger a data refresh"""
        logger.info(f"Manual {refresh_type} refresh triggered")

        if refresh_type == "full":
            return self.full_refresh()
        else:
            return self.refresh_all_data()

    def get_status(self) -> Dict[str, Any]:
        """Get scheduler status"""
        return {
            "is_running": self.is_running,
            "last_refresh": (
                self.last_refresh.isoformat() if self.last_refresh else None
            ),
            "next_scheduled_refresh": self._get_next_run_time(),
            "refresh_history_count": len(self.refresh_history),
            "recent_refreshes": self.refresh_history[-5:],  # Last 5
        }

    def _get_next_run_time(self) -> Optional[str]:
        """Get next scheduled run time"""
        if not self.is_running:
            return None

        jobs = self.scheduler.get_jobs()
        if not jobs:
            return None

        next_run = min(job.next_run_time for job in jobs if job.next_run_time)
        return next_run.isoformat() if next_run else None


# Global scheduler instance
data_scheduler = DataRefreshScheduler()


def start_scheduler():
    """Start the data refresh scheduler"""
    data_scheduler.start()


def stop_scheduler():
    """Stop the data refresh scheduler"""
    data_scheduler.stop()


def trigger_refresh(refresh_type: str = "incremental") -> Dict[str, Any]:
    """Trigger a manual data refresh"""
    return data_scheduler.trigger_manual_refresh(refresh_type)


def get_scheduler_status() -> Dict[str, Any]:
    """Get scheduler status"""
    return data_scheduler.get_status()
