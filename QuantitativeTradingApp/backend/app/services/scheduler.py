"""调度层：APScheduler + Redis 分布式锁 + 交易日判断。

职责（§5.3）：步骤 0（交易日判断）/1（锁）/2（创建 strategy_runs）/8（状态更新）/9（释放锁）。
纯计算交给 run_pipeline_core；为未来迁移 Celery 预留（状态更新职责随 Worker 迁移）。
"""

from __future__ import annotations

from datetime import date
from typing import Optional

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger

from app.core.config import get_settings
from app.core.database import SessionLocal
from app.core.redis_client import acquire_lock, release_lock
from app.models import StrategyRun
from app.services.market_data import TradingCalendar
from app.services.pipeline import run_pipeline_core
from app.utils.dates import SHANGHAI_TZ, now_shanghai, today_shanghai
from app.utils.logging import get_logger

logger = get_logger("scheduler")

LOCK_KEY = "daily_pipeline_lock"
STRATEGIES = ("turtle", "bollinger_mean_reversion")


class PipelineScheduler:
    def __init__(self) -> None:
        self._scheduler: BackgroundScheduler | None = None

    # ---- 生命周期 ----

    def start(self) -> None:
        settings = get_settings()
        if self._scheduler is not None and self._scheduler.running:
            return
        self._scheduler = BackgroundScheduler(timezone=SHANGHAI_TZ)
        # 重试机制：misfire_grace_time=3600（1 小时内补跑）+ coalesce=True（多次触发合并单次）
        self._scheduler.add_job(
            self.job,
            CronTrigger(
                hour=settings.schedule_cron_hour,
                minute=settings.schedule_cron_minute,
                timezone=SHANGHAI_TZ,
            ),
            id="daily_pipeline",
            misfire_grace_time=3600,
            coalesce=True,
            replace_existing=True,
        )
        self._scheduler.start()
        logger.info(
            "调度器已启动",
            cron=f"{settings.schedule_cron_hour}:{settings.schedule_cron_minute}",
            timezone=str(SHANGHAI_TZ),
        )

    def stop(self) -> None:
        if self._scheduler is not None:
            self._scheduler.shutdown(wait=False)
            self._scheduler = None

    # ---- 执行 ----

    def run_once(self, run_date: Optional[date] = None) -> dict | None:
        """手动触发一次（M1 验收「手动触发流水线」）。"""
        return self.job(run_date)

    def job(self, run_date: Optional[date] = None) -> dict | None:
        run_date = run_date or today_shanghai()
        settings = get_settings()
        started = now_shanghai()

        # 步骤 0：交易日判断（非交易日 → 记录并退出，不报错、不拉数据）
        if not TradingCalendar().is_trading_day(run_date):
            db = SessionLocal()
            try:
                db.add(
                    StrategyRun(
                        strategy="pipeline",
                        run_date=run_date,
                        status="success",
                        started_at=started,
                        finished_at=now_shanghai(),
                        note="非交易日，跳过",
                    )
                )
                db.commit()
            finally:
                db.close()
            logger.info("非交易日，跳过", run_date=run_date.isoformat())
            return None

        # 步骤 1：获取分布式锁（失败则本轮跳过，另一实例已执行）
        token = acquire_lock(LOCK_KEY, settings.lock_ttl)
        if token is None:
            logger.info("分布式锁获取失败，本轮跳过", run_date=run_date.isoformat())
            return None

        db = SessionLocal()
        run_ids: dict[str, int] = {}
        try:
            # 步骤 2：创建 strategy_runs（每条策略一个 run_id）
            for strategy in STRATEGIES:
                run = StrategyRun(
                    strategy=strategy,
                    run_date=run_date,
                    status="running",
                    started_at=started,
                )
                db.add(run)
                db.flush()
                run_ids[strategy] = run.id
            db.commit()

            # 步骤 3-7：纯计算
            summary = run_pipeline_core(run_date, run_ids, session=db)

            # 步骤 8：更新状态（success，记录数量/失败清单/耗时）
            for rid in run_ids.values():
                run = db.get(StrategyRun, rid)
                if run is not None:
                    run.status = "success"
                    run.finished_at = now_shanghai()
                    run.stock_count = summary["stock_count"]
                    run.note = summary["note"]
            db.commit()
            logger.info("流水线成功", run_date=run_date.isoformat(), **summary)
            return summary
        except Exception as e:  # noqa: BLE001
            db.rollback()
            for rid in run_ids.values():
                run = db.get(StrategyRun, rid)
                if run is not None:
                    run.status = "failed"
                    run.finished_at = now_shanghai()
                    run.note = f"异常：{e}"
            db.commit()
            logger.exception("流水线失败", run_date=run_date.isoformat(), error=str(e))
            return {"status": "failed", "error": str(e)}
        finally:
            # 步骤 9：Lua 原子释放锁
            released = release_lock(LOCK_KEY, token)
            logger.info("释放锁", released=released)
            db.close()


# 命令行手动触发：python -m app.services.scheduler
if __name__ == "__main__":
    from app.utils.logging import setup_logging

    setup_logging()
    result = PipelineScheduler().run_once()
    print(result)
