"""
Полный сброс и наполнение БД. Запуск из backend/: python scripts/reset_db.py
Подключение: DATABASE_URL из .env.dev или переменных окружения.
"""
import asyncio
import uuid

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.config import settings
from app.models import (
    Base, BoardColumn, BoardColumnStatus, LinkType, Notification, NotificationEntityType, NotificationEventType,
    Project, ProjectMember, ProjectMemberRole, ProjectVisibility, ProjectTaskTypeConfig,
    Status, StatusCategory, Task, TaskPriority, TaskType,
    Transition, User, View, ViewType, Workflow,
)
from app.models.comment import Comment


async def reset() -> None:
    from sqlalchemy import text
    from app.core.db import _FTS_DDL

    engine = create_async_engine(settings.database_url)
    async with engine.begin() as conn:
        # Terminate other connections so DROP SCHEMA doesn't deadlock
        await conn.execute(text(
            "SELECT pg_terminate_backend(pid) FROM pg_stat_activity "
            "WHERE datname = current_database() AND pid <> pg_backend_pid()"
        ))
        await conn.execute(text("DROP SCHEMA public CASCADE"))
        await conn.execute(text("CREATE SCHEMA public"))
        await conn.run_sync(Base.metadata.create_all)
        for stmt in _FTS_DDL:
            await conn.execute(text(stmt))

    Session = async_sessionmaker(engine, expire_on_commit=False)
    async with Session() as session:
        await seed(session)

    async with engine.begin() as conn:
        await conn.execute(text("UPDATE tasks SET title = title"))

    await engine.dispose()
    print("✓ Database reset and seeded")


async def seed(session: AsyncSession) -> None:
    admin_id   = uuid.UUID("00000000-0000-0000-0000-000000000001")
    manager_id = uuid.UUID("00000000-0000-0000-0000-000000000002")
    dev1_id    = uuid.UUID("00000000-0000-0000-0000-000000000003")

    admin   = User(id=admin_id,   email="admin@localhost",   display_name="Admin",   keycloak_id=str(admin_id),   is_superuser=True)
    manager = User(id=manager_id, email="manager@localhost", display_name="Manager", keycloak_id=str(manager_id))
    dev1    = User(id=dev1_id,    email="dev1@localhost",    display_name="Dev 1",   keycloak_id=str(dev1_id))
    session.add_all([admin, manager, dev1])
    await session.flush()

    # Global link types
    session.add_all([
        LinkType(name="blocks",     outward_name="blocks",     inward_name="is blocked by",     is_directed=True,  color="#ef4444", constraint={"type": "blocking"},                             position=0),
        LinkType(name="depends_on", outward_name="depends on", inward_name="is dependency of",  is_directed=True,  color="#f59e0b", constraint={"type": "sequential", "mode": "finish_to_start"}, position=1),
        LinkType(name="relates_to", outward_name="relates to", inward_name="relates to",        is_directed=False, color="#6366f1", constraint=None,                                             position=2),
        LinkType(name="duplicates", outward_name="duplicates", inward_name="is duplicated by",  is_directed=True,  color="#8b5cf6", constraint=None,                                             position=3),
        LinkType(name="clones",     outward_name="clones",     inward_name="is cloned by",      is_directed=True,  color="#10b981", constraint=None,                                             position=4),
    ])
    await session.flush()

    # System workflows (project_id = NULL)
    wf_task_story = Workflow(name="Task/Story", is_default=False)
    wf_bug        = Workflow(name="Bug",        is_default=False)
    wf_epic       = Workflow(name="Epic",       is_default=False)
    wf_decision   = Workflow(name="Decision Process", is_default=False)
    session.add_all([wf_task_story, wf_bug, wf_epic, wf_decision])
    await session.flush()

    # Statuses for system workflows
    _i, _m, _f = StatusCategory.initial, StatusCategory.intermediate, StatusCategory.final

    # Task/Story: To Do → In Progress → Review → Done
    st_ts = [
        Status(workflow_id=wf_task_story.id, name="To Do",       category=_i, is_default=True,  position=0),
        Status(workflow_id=wf_task_story.id, name="In Progress", category=_m, is_default=False, position=1),
        Status(workflow_id=wf_task_story.id, name="Review",      category=_m, is_default=False, position=2),
        Status(workflow_id=wf_task_story.id, name="Done",        category=_f, is_default=False, position=3),
    ]
    # Bug: Open → In Progress → Review → Verified → Closed
    st_bug = [
        Status(workflow_id=wf_bug.id, name="Open",        category=_i, is_default=True,  position=0),
        Status(workflow_id=wf_bug.id, name="In Progress", category=_m, is_default=False, position=1),
        Status(workflow_id=wf_bug.id, name="Review",      category=_m, is_default=False, position=2),
        Status(workflow_id=wf_bug.id, name="Verified",    category=_m, is_default=False, position=3),
        Status(workflow_id=wf_bug.id, name="Closed",      category=_f, is_default=False, position=4),
    ]
    # Epic: Planning → Active → Done
    st_epic = [
        Status(workflow_id=wf_epic.id, name="Planning", category=_i, is_default=True,  position=0),
        Status(workflow_id=wf_epic.id, name="Active",   category=_m, is_default=False, position=1),
        Status(workflow_id=wf_epic.id, name="Done",     category=_f, is_default=False, position=2),
    ]
    # Decision Process: Open → Collecting → Awaiting Decision → Decided
    st_dec = [
        Status(workflow_id=wf_decision.id, name="Open",              category=_i, is_default=True,  position=0),
        Status(workflow_id=wf_decision.id, name="Collecting",        category=_m, is_default=False, position=1),
        Status(workflow_id=wf_decision.id, name="Awaiting Decision", category=_m, is_default=False, position=2),
        Status(workflow_id=wf_decision.id, name="Decided",           category=_f, is_default=False, position=3),
    ]
    session.add_all(st_ts + st_bug + st_epic + st_dec)
    await session.flush()

    # Transitions for system workflows
    def _linear_transitions(wf_id, statuses):
        return [Transition(workflow_id=wf_id, from_status_id=statuses[i].id, to_status_id=statuses[i+1].id)
                for i in range(len(statuses) - 1)]

    session.add_all(
        _linear_transitions(wf_task_story.id, st_ts) +
        [Transition(workflow_id=wf_task_story.id, from_status_id=st_ts[1].id, to_status_id=st_ts[0].id)] +
        _linear_transitions(wf_bug.id, st_bug) +
        [Transition(workflow_id=wf_bug.id, from_status_id=st_bug[1].id, to_status_id=st_bug[0].id)] +
        _linear_transitions(wf_epic.id, st_epic) +
        _linear_transitions(wf_decision.id, st_dec)
    )

    # System task types (project_id = NULL) — linked to system workflows
    tt_task     = TaskType(key="task",     name="Задача",   is_system=True, icon="check-square", color="#6366f1", default_workflow_id=wf_task_story.id)
    tt_bug      = TaskType(key="bug",      name="Баг",      is_system=True, icon="bug",          color="#ef4444", default_workflow_id=wf_bug.id)
    tt_story    = TaskType(key="story",    name="История",  is_system=True, icon="book-open",    color="#10b981", default_workflow_id=wf_task_story.id)
    tt_epic     = TaskType(key="epic",     name="Эпик",     is_system=True, icon="zap",          color="#f59e0b", default_workflow_id=wf_epic.id)
    tt_decision = TaskType(key="decision", name="Decision", is_system=True, icon="git-branch",   color="#8b5cf6", default_workflow_id=wf_decision.id)
    session.add_all([tt_task, tt_bug, tt_story, tt_epic, tt_decision])
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

    todo   = Status(workflow_id=wf.id, name="To Do",       category=StatusCategory.initial,       is_default=True,  position=0)
    inprog = Status(workflow_id=wf.id, name="In Progress", category=StatusCategory.intermediate,  is_default=False, position=1)
    review = Status(workflow_id=wf.id, name="Review",      category=StatusCategory.intermediate,  is_default=False, position=2)
    done   = Status(workflow_id=wf.id, name="Done",        category=StatusCategory.final,         is_default=False, position=3)
    session.add_all([todo, inprog, review, done])
    await session.flush()

    session.add_all([
        Transition(workflow_id=wf.id, from_status_id=todo.id,   to_status_id=inprog.id),
        Transition(workflow_id=wf.id, from_status_id=inprog.id, to_status_id=review.id),
        Transition(workflow_id=wf.id, from_status_id=review.id, to_status_id=done.id),
        Transition(workflow_id=wf.id, from_status_id=todo.id,   to_status_id=done.id),
        Transition(workflow_id=wf.id, from_status_id=inprog.id, to_status_id=todo.id),
        Transition(workflow_id=wf.id, from_status_id=review.id, to_status_id=inprog.id),
    ])

    # ProjectTaskTypeConfig: all types in DEMO → project «Базовый» workflow
    # (ensures tasks appear on the board; can be overridden in settings)
    for tt in [tt_task, tt_bug, tt_story, tt_epic, tt_decision]:
        session.add(ProjectTaskTypeConfig(
            project_id=demo.id, task_type_id=tt.id, workflow_id=wf.id,
        ))
    await session.flush()

    # Views for DEMO project
    kanban_view = View(project_id=demo.id, name="Board",   type=ViewType.kanban,  position=0, is_default=True)
    backlog_view = View(project_id=demo.id, name="Backlog", type=ViewType.backlog, position=1)
    session.add_all([kanban_view, backlog_view])
    await session.flush()

    # Board columns for the kanban view
    bc1 = BoardColumn(view_id=kanban_view.id, name="To Do",       position=0)
    bc2 = BoardColumn(view_id=kanban_view.id, name="In Progress", position=1)
    bc3 = BoardColumn(view_id=kanban_view.id, name="Review",      position=2)
    bc4 = BoardColumn(view_id=kanban_view.id, name="Done",        position=3)
    session.add_all([bc1, bc2, bc3, bc4])
    await session.flush()
    session.add_all([
        BoardColumnStatus(board_column_id=bc1.id, status_id=todo.id),
        BoardColumnStatus(board_column_id=bc2.id, status_id=inprog.id),
        BoardColumnStatus(board_column_id=bc3.id, status_id=review.id),
        BoardColumnStatus(board_column_id=bc4.id, status_id=done.id),
    ])


    def task(n, title, type_=None, assignee=None, status=None, priority=TaskPriority.medium,
             description=None, parent=None, meta=None, start=None, due=None):
        return Task(
            project_id=demo.id, workflow_id=wf.id, reporter_id=admin_id,
            task_type_id=(type_ or tt_task).id,
            assignee_id=assignee,
            parent_task_id=parent.id if parent else None,
            current_status_id=(status or todo).id,
            key=f"DEMO-{n}", title=title, priority=priority,
            description=description,
            start_date=start, due_date=due,
            meta=meta or {},
        )

    # Solution comments on each subtask
    from datetime import UTC, date, datetime
    now = datetime.now(UTC)
    today = date.today()

    def d(offset): return date(today.year, today.month, 1) if offset == 0 else \
        date.fromordinal(date(today.year, today.month, 1).toordinal() + offset)

    # Regular tasks assigned to admin
    t1  = task(1,  "Настроить CI/CD pipeline",            assignee=admin_id,   priority=TaskPriority.high,
               description="Настроить GitHub Actions: lint → test → build → deploy on merge to main",
               start=d(-14), due=d(0))
    t2  = task(2,  "Написать документацию API",           assignee=admin_id,
               description="Покрыть все публичные эндпоинты, добавить примеры запросов/ответов",
               start=d(-7), due=d(7))
    t3  = task(3,  "Исправить баг с авторизацией",        type_=tt_bug, assignee=admin_id, priority=TaskPriority.critical,
               description="При истечении токена редиректит на 404 вместо /login",
               start=d(-3), due=d(2))
    t4  = task(4,  "Реализовать поиск по задачам",        assignee=admin_id, status=inprog,
               description="FTS через PostgreSQL tsvector, поиск по заголовку и описанию",
               start=d(0), due=d(14))
    t5  = task(5,  "Ревью дизайна онбординга",            assignee=admin_id, status=inprog, priority=TaskPriority.low,
               description="Пройти прототип, оставить комментарии в Figma",
               start=d(3), due=d(10))
    t6  = task(6,  "Обновить зависимости",                assignee=admin_id, status=review, priority=TaskPriority.low,
               start=d(-5), due=d(-1))
    t7  = task(7,  "Code review: модуль уведомлений",     assignee=admin_id, status=review, priority=TaskPriority.high,
               start=d(5), due=d(12))
    t8  = task(8,  "Деплой на стейджинг",                 assignee=admin_id, status=done,  priority=TaskPriority.high,
               start=d(-20), due=d(-10))
    t9  = task(9,  "Добавить тесты для task_service",     assignee=admin_id, status=done,
               start=d(-10), due=d(-5))

    # Decision task — manager is the DM (assignee), blocked until subtasks are ready
    t10 = task(10, "Выбрать подход к авторизации",
               type_=tt_decision, assignee=manager_id, status=todo, priority=TaskPriority.high,
               description="Два варианта: Keycloak или собственный OAuth. Каждый исполнитель исследует и подаёт Solution.",
               start=d(-7), due=d(21),
               meta={"criteria": [
                   {"description": "Простота интеграции с существующим стеком", "position": 0},
                   {"description": "Минимальный объём поддержки на стороне приложения",  "position": 1},
                   {"description": "Стоимость внедрения (часы разработчика)",              "position": 2},
               ]})

    # dev1 tasks
    t11 = task(11, "Оптимизировать запросы к БД",         assignee=dev1_id, status=inprog,
               start=d(0), due=d(10))
    t12 = task(12, "Добавить индексы на tasks.project_id", assignee=dev1_id, status=done, priority=TaskPriority.low,
               start=d(-15), due=d(-8))

    session.add_all([t1, t2, t3, t4, t5, t6, t7, t8, t9, t10, t11, t12])
    await session.flush()

    # Subtasks of t10 — one per lead assignee
    t10_admin = task(13, "Исследовать Keycloak",
                     assignee=admin_id, status=review, parent=t10,
                     description="Realm для приложения, JWKS-валидация на бэке, встроенный UI для логина.")
    t10_dev1  = task(14, "Исследовать собственный OAuth",
                     assignee=dev1_id,  status=review, parent=t10,
                     description="FastAPI + python-jose. Полный контроль над флоу, нет зависимости от внешнего сервиса.")
    session.add_all([t10_admin, t10_dev1])
    await session.flush()

    now = datetime.now(UTC)

    # Solution comments on each subtask
    sol_admin = Comment(
        task_id=t10_admin.id, author_id=admin_id,
        content="Предлагаю Keycloak: realm для приложения, JWKS-валидация на бэке, "
                "встроенный UI для логина. Минимум кода в приложении, готовый OAuth-флоу. "
                "Часы внедрения: ~16ч (настройка + интеграция).",
        labels=["solution"],
    )
    sol_dev1 = Comment(
        task_id=t10_dev1.id, author_id=dev1_id,
        content="Свой OAuth-провайдер на FastAPI + python-jose. Полный контроль над флоу, "
                "нет зависимости от внешнего сервиса. Часы внедрения: ~40ч "
                "(пользователи, токены, сессии, refresh, recovery).",
        labels=["solution"],
    )
    session.add_all([sol_admin, sol_dev1])
    await session.flush()

    # Mark solution comments in subtask meta
    t10_admin.meta = {"solution_comment_id": str(sol_admin.id)}
    t10_dev1.meta  = {"solution_comment_id": str(sol_dev1.id)}

    # Notifications
    session.add_all([
        Notification(
            recipient_id=manager_id,
            event_type=NotificationEventType.awaiting_decision,
            entity_type=NotificationEntityType.task,
            entity_id=t10.id, task_id=t10.id,
            message=f"Все решения поданы по {t10.key}: {t10.title} — требуется Decision",
        ),
        Notification(
            recipient_id=admin_id,
            event_type=NotificationEventType.task_assigned,
            entity_type=NotificationEntityType.task,
            entity_id=t10_admin.id, task_id=t10_admin.id,
            message=f"Вас назначили на задачу {t10_admin.key}: {t10_admin.title}",
        ),
        Notification(
            recipient_id=dev1_id,
            event_type=NotificationEventType.task_assigned,
            entity_type=NotificationEntityType.task,
            entity_id=t10_dev1.id, task_id=t10_dev1.id,
            message=f"Вас назначили на задачу {t10_dev1.key}: {t10_dev1.title}",
        ),
    ])

    await session.commit()
    print("  → 3 пользователя, 4 системных воркфлоу (Task/Story, Bug, Epic, Decision Process)")
    print("  → 5 системных типов задач, привязанных к системным воркфлоу")
    print("  → проект DEMO, воркфлоу «Базовый», 4 BoardColumn")
    print("  → 12 обычных задач + 2 подзадачи DEMO-13/14 для Decision-задачи DEMO-10")
    print("  → Solution-комментарии на подзадачах, уведомления для демонстрации колокольчика")


if __name__ == "__main__":
    asyncio.run(reset())
