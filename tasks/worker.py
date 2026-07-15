"""
Minervini Screener v1.0 - Background Task Worker
Scheduled tasks for data update, screening, and notification.
"""
import asyncio
import os
from datetime import datetime
from typing import Optional

from config.loader import settings
from core.logging_setup import get_logger

logger = get_logger(__name__)


class TaskWorker:
    """Background task scheduler and executor.

    Manages periodic tasks:
    - Daily data update (after market close)
    - Screening scan execution
    - Notification dispatch
    - Report generation
    """

    def __init__(self):
        self.running = False
        self.tasks: dict[str, dict] = {
            "daily_update": {
                "name": "数据每日更新",
                "enabled": True,
                "schedule": "30 15 * * 1-5",  # Mon-Fri 15:30
                "last_run": None,
                "task": self._daily_update,
            },
            "screening_scan": {
                "name": "筛选扫描",
                "enabled": True,
                "schedule": "0 16 * * 1-5",  # Mon-Fri 16:00
                "last_run": None,
                "task": self._run_screening,
            },
            "report_generate": {
                "name": "报告生成",
                "enabled": True,
                "schedule": "0 17 * * 1-5",  # Mon-Fri 17:00
                "last_run": None,
                "task": self._generate_report,
            },
        }

    async def start(self):
        """Start the task worker loop."""
        self.running = True
        logger.info("任务调度器已启动")

        while self.running:
            now = datetime.now()
            for task_id, task in self.tasks.items():
                if not task["enabled"]:
                    continue
                if self._should_run(task, now):
                    logger.info(f"执行任务: {task['name']}")
                    try:
                        await task["task"]()
                        task["last_run"] = now
                        logger.info(f"任务完成: {task['name']}")
                    except Exception as e:
                        logger.error(f"任务失败 [{task['name']}]: {e}", exc_info=True)

            # Sleep 1 minute between checks
            await asyncio.sleep(60)

    def stop(self):
        """Stop the task worker."""
        self.running = False
        logger.info("任务调度器已停止")

    def _should_run(self, task: dict, now: datetime) -> bool:
        """Check if a task should run now based on its cron schedule."""
        last_run = task.get("last_run")
        if last_run is None:
            # Check if current time matches schedule
            return self._match_cron(task["schedule"], now)

        # Don't run if already ran today
        if last_run.date() == now.date():
            return False

        return self._match_cron(task["schedule"], now)

    def _match_cron(self, expression: str, dt: datetime) -> bool:
        """Simple cron expression matcher (minute hour day-of-week)."""
        parts = expression.strip().split()
        if len(parts) < 2:
            return False

        if not self._cron_match(parts[0], dt.minute):
            return False
        if not self._cron_match(parts[1], dt.hour):
            return False

        # Check day-of-week if specified (5th field)
        if len(parts) >= 5 and parts[4] != "*":
            # Python weekday: Mon=0, Tue=1, ..., Sun=6
            # Cron DOW:      Sun=0, Mon=1, ..., Sat=6  (Sun also =7)
            cron_dow = (dt.weekday() + 1) % 7  # Mon→1, Tue→2, ..., Sun→0
            if not self._cron_match(parts[4], cron_dow):
                return False

        return True

    def _cron_match(self, pattern: str, value: int) -> bool:
        """Match a value against a cron field pattern."""
        if pattern == "*":
            return True
        if "/" in pattern:
            base, step = pattern.split("/")
            base_val = 0 if base == "*" else int(base)
            return (value - base_val) % int(step) == 0 and value >= base_val
        if "," in pattern:
            return value in [int(p) for p in pattern.split(",")]
        if "-" in pattern:
            lo, hi = pattern.split("-")
            return int(lo) <= value <= int(hi)
        return int(pattern) == value

    async def _daily_update(self):
        """Update daily stock data from data sources."""
        logger.info("开始每日数据更新...")
        try:
            from data.downloader import DataDownloader
            downloader = DataDownloader()
            count = await downloader.update_all()
            logger.info(f"数据更新完成: {count}只")
        except Exception as e:
            logger.error(f"数据更新异常: {e}")
            raise

    async def _run_screening(self):
        """Run screening scan and dispatch results."""
        logger.info("开始筛选扫描...")
        try:
            from data.downloader import DataDownloader
            downloader = DataDownloader()
            results = await downloader.screen_all()

            # Dispatch notifications
            if results:
                buy_signals = [r for r in results if r.get("signal") == "buy"]
                watch_signals = [r for r in results if r.get("signal") == "watch"]

                logger.info(f"扫描完成: {len(buy_signals)}买入 {len(watch_signals)}关注")

                # Send notifications (wrap sync I/O calls to avoid blocking event loop)
                if settings.notifications.channels.email.enabled:
                    from notify.email_notify import send_screening_alert
                    await asyncio.to_thread(send_screening_alert, results, f"{len(buy_signals)}买入 {len(watch_signals)}关注")

                if os.environ.get("WECHAT_PUSH_TOKEN"):
                    from notify.wechat_push import send_screening_summary
                    await asyncio.to_thread(send_screening_summary, results)

                if os.environ.get("DINGTALK_WEBHOOK_URL"):
                    from notify.dingtalk_notify import send_dingtalk_screening
                    await asyncio.to_thread(send_dingtalk_screening, results)
            else:
                logger.info("扫描完成: 无结果")

        except Exception as e:
            logger.error(f"筛选扫描异常: {e}")
            raise

    async def _generate_report(self):
        """Generate daily report."""
        logger.info("开始生成报告...")
        try:
            from data.downloader import DataDownloader
            from ai.report_generator import generate_daily_report

            downloader = DataDownloader()
            results = await downloader.screen_all()

            report = generate_daily_report(results, format="markdown")

            # Save report
            # Save report
            report_path = "reports"
            import os
            os.makedirs(report_path, exist_ok=True)
            today = datetime.now().strftime("%Y%m%d")
            filepath = os.path.join(report_path, f"daily_report_{today}.md")
            with open(filepath, "w", encoding="utf-8") as f:
                f.write(report)
            logger.info(f"报告已保存: {filepath}")

        except Exception as e:
            logger.error(f"报告生成异常: {e}")
            raise

    def get_status(self) -> dict:
        """Get worker status."""
        now = datetime.now()
        task_status = []
        for tid, t in self.tasks.items():
            last = t.get("last_run")
            task_status.append({
                "id": tid,
                "name": t["name"],
                "enabled": t["enabled"],
                "schedule": t["schedule"],
                "last_run": last.isoformat() if last else None,
                "next_run": self._next_run(t["schedule"], now),
            })

        return {
            "running": self.running,
            "tasks": task_status,
        }

    def _next_run(self, expression: str, from_time: datetime) -> Optional[str]:
        """Calculate next run time (simplified)."""
        if self._match_cron(expression, from_time):
            return from_time.isoformat()
        # Simplified: return tomorrow same time
        from datetime import timedelta
        next_time = from_time + timedelta(days=1)
        return next_time.replace(second=0, microsecond=0).isoformat()
