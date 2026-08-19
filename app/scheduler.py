import logging

from apscheduler.schedulers.asyncio import AsyncIOScheduler

from app.database import AsyncSessionLocal
from app.services.cleanup import (
    cleanup_expired_idempotency_keys,
    cleanup_old_webhook_events,
    expire_stale_pending_transactions,
)

logger = logging.getLogger(__name__)

scheduler = AsyncIOScheduler()


async def run_cleanup_job() -> None:
    async with AsyncSessionLocal() as db:
        try:
            deleted_keys = await cleanup_expired_idempotency_keys(db)
            deleted_events = await cleanup_old_webhook_events(db)
            expired_tx = await expire_stale_pending_transactions(db)
            logger.info(
                "Cleanup job: %s idempotency keys removed, %s webhook events removed, "
                "%s pending transactions expired",
                deleted_keys,
                deleted_events,
                expired_tx,
            )
        except Exception:
            logger.exception("Cleanup job failed")


def start_scheduler() -> None:
    scheduler.add_job(run_cleanup_job, "interval", hours=1, id="cleanup_job", replace_existing=True)
    scheduler.start()


def shutdown_scheduler() -> None:
    scheduler.shutdown(wait=False)