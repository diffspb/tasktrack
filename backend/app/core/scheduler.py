import logging

from apscheduler.schedulers.asyncio import AsyncIOScheduler

logger = logging.getLogger(__name__)

scheduler = AsyncIOScheduler()


async def purge_expired_idempotency_keys() -> None:
    """Idempotency keys live 24 h (ADR-019); expired rows only take space."""
    from app.core.db import SessionLocal
    from app.services.idempotency_service import purge_expired

    async with SessionLocal() as session:
        removed = await purge_expired(session)
    if removed:
        logger.info("Purged %d expired idempotency keys", removed)


scheduler.add_job(purge_expired_idempotency_keys, "interval", hours=1, id="purge_idempotency_keys")
