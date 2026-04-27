"""
Полный сброс и наполнение БД. Запуск из backend/: python scripts/reset_db.py
Подключение: DATABASE_URL из .env.dev или переменных окружения.
"""
import asyncio
import uuid

from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

from app.core.config import settings
from app.models import Base, Project, ProjectMember, ProjectMemberRole, ProjectVisibility, User


async def reset() -> None:
    engine = create_async_engine(settings.database_url)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)

    Session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with Session() as session:
        await seed(session)

    await engine.dispose()
    print("✓ Database reset and seeded")


async def seed(session: AsyncSession) -> None:
    admin_id = uuid.UUID("00000000-0000-0000-0000-000000000001")
    manager_id = uuid.UUID("00000000-0000-0000-0000-000000000002")
    dev1_id = uuid.UUID("00000000-0000-0000-0000-000000000003")

    admin = User(id=admin_id, email="admin@localhost", display_name="Admin", keycloak_id=str(admin_id))
    manager = User(id=manager_id, email="manager@localhost", display_name="Manager", keycloak_id=str(manager_id))
    dev1 = User(id=dev1_id, email="dev1@localhost", display_name="Dev 1", keycloak_id=str(dev1_id))
    session.add_all([admin, manager, dev1])
    await session.flush()

    demo = Project(
        name="Демо-проект",
        key="DEMO",
        description="Демонстрационный проект для исследовательского запуска",
        visibility=ProjectVisibility.restricted,
        owner_id=admin_id,
    )
    session.add(demo)
    await session.flush()

    session.add_all([
        ProjectMember(project_id=demo.id, user_id=admin_id, role=ProjectMemberRole.admin),
        ProjectMember(project_id=demo.id, user_id=manager_id, role=ProjectMemberRole.manager),
        ProjectMember(project_id=demo.id, user_id=dev1_id, role=ProjectMemberRole.member),
    ])
    await session.commit()
    print(f"  → 3 пользователя, проект '{demo.name}' (key={demo.key})")


if __name__ == "__main__":
    asyncio.run(reset())
