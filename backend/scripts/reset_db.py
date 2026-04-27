"""
Полный сброс и наполнение БД. Запуск из backend/: python scripts/reset_db.py
Подключение: DATABASE_URL из .env.dev или переменных окружения.
"""
import asyncio

from sqlalchemy.ext.asyncio import create_async_engine

from app.core.config import settings
from app.models import Base  # noqa: F401 — регистрирует все модели


async def reset() -> None:
    engine = create_async_engine(settings.database_url)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)
    await engine.dispose()
    print("✓ Database reset complete")
    # Phase 1+: добавить seed-данные (пользователи, демо-проект, воркфлоу, задачи)


if __name__ == "__main__":
    asyncio.run(reset())
