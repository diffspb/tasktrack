"""
Полный сброс и наполнение БД. Запуск из backend/: python scripts/reset_db.py
Подключение: DATABASE_URL из .env.dev или переменных окружения.
"""
import asyncio
import uuid

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.config import settings
from app.models import (
    Assignment, AssigneeRole, Base, GlobalStatus,
    Project, ProjectMember, ProjectMemberRole, ProjectVisibility,
    Resolution, Status, StatusCategory, Task, TaskPriority, TaskType,
    Transition, User, Workflow,
)


async def reset() -> None:
    engine = create_async_engine(settings.database_url)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)

    Session = async_sessionmaker(engine, expire_on_commit=False)
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
        name="Демо-проект", key="DEMO",
        description="Демонстрационный проект для исследовательского запуска",
        visibility=ProjectVisibility.restricted, owner_id=admin_id,
    )
    session.add(demo)
    await session.flush()

    session.add_all([
        ProjectMember(project_id=demo.id, user_id=admin_id, role=ProjectMemberRole.admin),
        ProjectMember(project_id=demo.id, user_id=manager_id, role=ProjectMemberRole.manager),
        ProjectMember(project_id=demo.id, user_id=dev1_id, role=ProjectMemberRole.member),
    ])

    wf = Workflow(project_id=demo.id, name="Базовый", is_default=True)
    session.add(wf)
    await session.flush()

    todo = Status(workflow_id=wf.id, name="To Do", category=StatusCategory.initial, is_default=True, position=0)
    inprog = Status(workflow_id=wf.id, name="In Progress", category=StatusCategory.intermediate, position=1)
    review = Status(workflow_id=wf.id, name="Review", category=StatusCategory.intermediate, position=2)
    done = Status(workflow_id=wf.id, name="Done", category=StatusCategory.final, position=3)
    session.add_all([todo, inprog, review, done])
    await session.flush()

    session.add_all([
        Transition(workflow_id=wf.id, from_status_id=todo.id, to_status_id=inprog.id),
        Transition(workflow_id=wf.id, from_status_id=inprog.id, to_status_id=review.id),
        Transition(workflow_id=wf.id, from_status_id=review.id, to_status_id=done.id),
        Transition(workflow_id=wf.id, from_status_id=todo.id, to_status_id=done.id),
    ])

    res_done = Resolution(project_id=demo.id, name="Done", is_default=True, position=0)
    session.add_all([
        res_done,
        Resolution(project_id=demo.id, name="Won't Fix", position=1),
        Resolution(project_id=demo.id, name="Duplicate", position=2),
        Resolution(project_id=demo.id, name="Cannot Reproduce", position=3),
    ])
    await session.flush()

    # 8 задач в разных состояниях
    def task(n, title, priority=TaskPriority.medium, gs=GlobalStatus.open):
        return Task(
            project_id=demo.id, workflow_id=wf.id, reporter_id=admin_id,
            key=f"DEMO-{n}", title=title, priority=priority, global_status=gs,
        )

    t1 = task(1, "Настроить CI/CD", TaskPriority.high)
    t2 = task(2, "Написать документацию", TaskPriority.medium)
    t3 = task(3, "Исправить баг в авторизации", TaskPriority.critical)
    t4 = task(4, "Реализовать Kanban", TaskPriority.high, GlobalStatus.in_progress)
    t5 = task(5, "Оптимизировать запросы", TaskPriority.medium, GlobalStatus.in_progress)
    t6 = task(6, "Добавить тесты", TaskPriority.low, GlobalStatus.closed)
    t7 = task(7, "Деплой на стейджинг", TaskPriority.high, GlobalStatus.closed)
    t8 = task(8, "Решение с двумя исполнителями", TaskPriority.medium, GlobalStatus.in_progress)
    session.add_all([t1, t2, t3, t4, t5, t6, t7, t8])
    await session.flush()

    session.add_all([
        Assignment(task_id=t4.id, user_id=dev1_id, role=AssigneeRole.lead, current_status_id=inprog.id),
        Assignment(task_id=t5.id, user_id=dev1_id, role=AssigneeRole.lead, current_status_id=inprog.id),
        Assignment(task_id=t6.id, user_id=dev1_id, role=AssigneeRole.lead, current_status_id=done.id, resolution_id=res_done.id),
        Assignment(task_id=t7.id, user_id=admin_id, role=AssigneeRole.lead, current_status_id=done.id, resolution_id=res_done.id),
        Assignment(task_id=t8.id, user_id=admin_id, role=AssigneeRole.lead, current_status_id=inprog.id),
        Assignment(task_id=t8.id, user_id=dev1_id, role=AssigneeRole.lead, current_status_id=todo.id),
    ])
    await session.commit()
    print(f"  → 3 пользователя, проект DEMO, воркфлоу «Базовый», 8 задач")


if __name__ == "__main__":
    asyncio.run(reset())
