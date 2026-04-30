"""
Полный сброс и наполнение БД. Запуск из backend/: python scripts/reset_db.py
Подключение: DATABASE_URL из .env.dev или переменных окружения.
"""
import asyncio
import uuid

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.config import settings
from app.models import (
    Assignment, AssigneeRole, Base, DecisionCriteria, GlobalStatus,
    Project, ProjectMember, ProjectMemberRole, ProjectVisibility,
    Resolution, Solution, SolutionStatus, Status, StatusCategory,
    Task, TaskPriority, TaskType, Transition, User, Workflow,
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
    admin_id   = uuid.UUID("00000000-0000-0000-0000-000000000001")
    manager_id = uuid.UUID("00000000-0000-0000-0000-000000000002")
    dev1_id    = uuid.UUID("00000000-0000-0000-0000-000000000003")

    admin   = User(id=admin_id,   email="admin@localhost",   display_name="Admin",   keycloak_id=str(admin_id))
    manager = User(id=manager_id, email="manager@localhost", display_name="Manager", keycloak_id=str(manager_id))
    dev1    = User(id=dev1_id,    email="dev1@localhost",    display_name="Dev 1",   keycloak_id=str(dev1_id))
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
        ProjectMember(project_id=demo.id, user_id=admin_id,   role=ProjectMemberRole.admin),
        ProjectMember(project_id=demo.id, user_id=manager_id, role=ProjectMemberRole.manager),
        ProjectMember(project_id=demo.id, user_id=dev1_id,    role=ProjectMemberRole.member),
    ])

    wf = Workflow(project_id=demo.id, name="Базовый", is_default=True)
    session.add(wf)
    await session.flush()

    todo   = Status(workflow_id=wf.id, name="To Do",       category=StatusCategory.initial,       is_default=True, position=0)
    inprog = Status(workflow_id=wf.id, name="In Progress", category=StatusCategory.intermediate,   is_default=False, position=1)
    review = Status(workflow_id=wf.id, name="Review",      category=StatusCategory.intermediate,   is_default=False, position=2)
    done   = Status(workflow_id=wf.id, name="Done",        category=StatusCategory.final,          is_default=False, position=3)
    session.add_all([todo, inprog, review, done])
    await session.flush()

    session.add_all([
        # Forward
        Transition(workflow_id=wf.id, from_status_id=todo.id,   to_status_id=inprog.id),
        Transition(workflow_id=wf.id, from_status_id=inprog.id, to_status_id=review.id),
        Transition(workflow_id=wf.id, from_status_id=review.id, to_status_id=done.id),
        Transition(workflow_id=wf.id, from_status_id=todo.id,   to_status_id=done.id),
        # Backward (можно вернуть задачу назад)
        Transition(workflow_id=wf.id, from_status_id=inprog.id, to_status_id=todo.id),
        Transition(workflow_id=wf.id, from_status_id=review.id, to_status_id=inprog.id),
    ])

    res_done = Resolution(project_id=demo.id, name="Done",              is_default=True, position=0)
    session.add_all([
        res_done,
        Resolution(project_id=demo.id, name="Won't Fix",         position=1),
        Resolution(project_id=demo.id, name="Duplicate",         position=2),
        Resolution(project_id=demo.id, name="Cannot Reproduce",  position=3),
    ])
    await session.flush()

    def task(n, title, priority=TaskPriority.medium, gs=GlobalStatus.open, description=None):
        return Task(
            project_id=demo.id, workflow_id=wf.id, reporter_id=admin_id,
            key=f"DEMO-{n}", title=title, priority=priority,
            global_status=gs, description=description,
        )

    # admin (AUTH_STUB) tasks — достаточно для демонстрации всего воркфлоу
    t1  = task(1,  "Настроить CI/CD pipeline",            TaskPriority.high,
               description="Настроить GitHub Actions: lint → test → build → deploy on merge to main")
    t2  = task(2,  "Написать документацию API",           TaskPriority.medium,
               description="Покрыть все публичные эндпоинты, добавить примеры запросов/ответов")
    t3  = task(3,  "Исправить баг с авторизацией",        TaskPriority.critical,
               description="При истечении токена редиректит на 404 вместо /login")
    t4  = task(4,  "Реализовать поиск по задачам",        TaskPriority.medium, GlobalStatus.in_progress,
               description="FTS через PostgreSQL tsvector, поиск по заголовку и описанию")
    t5  = task(5,  "Ревью дизайна онбординга",            TaskPriority.low,   GlobalStatus.in_progress,
               description="Пройти прототип, оставить комментарии в Figma")
    t6  = task(6,  "Обновить зависимости",                TaskPriority.low,   GlobalStatus.in_progress)
    t7  = task(7,  "Code review: модуль уведомлений",     TaskPriority.high,  GlobalStatus.in_progress)
    t8  = task(8,  "Деплой на стейджинг",                 TaskPriority.high,  GlobalStatus.closed)
    t9  = task(9,  "Добавить тесты для task_service",     TaskPriority.medium, GlobalStatus.closed)
    # multi-assignee demo task — both leads have submitted Solutions, awaiting Decision from manager
    t10 = task(10, "Выбрать подход к авторизации",        TaskPriority.high,  GlobalStatus.awaiting_decision,
               description="Два варианта: Keycloak или собственный OAuth. Каждый исполнитель исследует и подаёт Solution.")
    t10.decision_maker_id = manager_id
    # dev1 tasks
    t11 = task(11, "Оптимизировать запросы к БД",         TaskPriority.medium, GlobalStatus.in_progress)
    t12 = task(12, "Добавить индексы на tasks.project_id", TaskPriority.low,  GlobalStatus.closed)

    session.add_all([t1, t2, t3, t4, t5, t6, t7, t8, t9, t10, t11, t12])
    await session.flush()

    session.add_all([
        # admin: To Do (3 задачи)
        Assignment(task_id=t1.id,  user_id=admin_id, role=AssigneeRole.lead, current_status_id=todo.id),
        Assignment(task_id=t2.id,  user_id=admin_id, role=AssigneeRole.lead, current_status_id=todo.id),
        Assignment(task_id=t3.id,  user_id=admin_id, role=AssigneeRole.lead, current_status_id=todo.id),
        # admin: In Progress (2 задачи)
        Assignment(task_id=t4.id,  user_id=admin_id, role=AssigneeRole.lead, current_status_id=inprog.id),
        Assignment(task_id=t5.id,  user_id=admin_id, role=AssigneeRole.lead, current_status_id=inprog.id),
        # admin: Review (2 задачи)
        Assignment(task_id=t6.id,  user_id=admin_id, role=AssigneeRole.lead, current_status_id=review.id),
        Assignment(task_id=t7.id,  user_id=admin_id, role=AssigneeRole.lead, current_status_id=review.id),
        # admin: Done (2 задачи)
        Assignment(task_id=t8.id,  user_id=admin_id, role=AssigneeRole.lead, current_status_id=done.id, resolution_id=res_done.id),
        Assignment(task_id=t9.id,  user_id=admin_id, role=AssigneeRole.lead, current_status_id=done.id, resolution_id=res_done.id),
        # multi-assignee: admin + dev1 оба lead, оба в Done со submitted Solution
        Assignment(task_id=t10.id, user_id=admin_id, role=AssigneeRole.lead, current_status_id=done.id, resolution_id=res_done.id),
        Assignment(task_id=t10.id, user_id=dev1_id,  role=AssigneeRole.lead, current_status_id=done.id, resolution_id=res_done.id),
        # dev1 tasks
        Assignment(task_id=t11.id, user_id=dev1_id,  role=AssigneeRole.lead, current_status_id=inprog.id),
        Assignment(task_id=t12.id, user_id=dev1_id,  role=AssigneeRole.lead, current_status_id=done.id, resolution_id=res_done.id),
    ])
    await session.flush()

    # Decision Process artefacts for t10 (multi-lead, awaiting_decision)
    from datetime import UTC, datetime
    a_admin_t10 = next(
        a for a in (await session.execute(
            __import__('sqlalchemy').select(Assignment).where(
                Assignment.task_id == t10.id, Assignment.user_id == admin_id,
            )
        )).scalars()
    )
    a_dev1_t10 = next(
        a for a in (await session.execute(
            __import__('sqlalchemy').select(Assignment).where(
                Assignment.task_id == t10.id, Assignment.user_id == dev1_id,
            )
        )).scalars()
    )
    now = datetime.now(UTC)
    session.add_all([
        DecisionCriteria(task_id=t10.id, description="Простота интеграции с существующим стеком", position=0, is_locked=True),
        DecisionCriteria(task_id=t10.id, description="Минимальный объём поддержки на стороне приложения", position=1, is_locked=True),
        DecisionCriteria(task_id=t10.id, description="Стоимость внедрения (часы разработчика)", position=2, is_locked=True),
        Solution(
            assignment_id=a_admin_t10.id,
            content="Предлагаю Keycloak: realm для приложения, JWKS-валидация на бэке, "
                    "встроенный UI для логина. Минимум кода в приложении, готовый OAuth-флоу. "
                    "Часы внедрения: ~16ч (настройка + интеграция).",
            status=SolutionStatus.submitted, submitted_at=now,
        ),
        Solution(
            assignment_id=a_dev1_t10.id,
            content="Свой OAuth-провайдер на FastAPI + python-jose. Полный контроль над флоу, "
                    "нет зависимости от внешнего сервиса. Часы внедрения: ~40ч "
                    "(пользователи, токены, сессии, refresh, recovery).",
            status=SolutionStatus.submitted, submitted_at=now,
        ),
    ])
    await session.commit()
    print("  → 3 пользователя, проект DEMO, воркфлоу «Базовый», 12 задач")
    print("  → DEMO-10: multi-lead Decision Process (2 submitted Solutions, awaiting Manager's Decision)")


if __name__ == "__main__":
    asyncio.run(reset())
