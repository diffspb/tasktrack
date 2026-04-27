import uuid

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.project import Project, ProjectMember, ProjectMemberRole, ProjectVisibility
from app.models.user import User


async def test_create_project(client: AsyncClient):
    response = await client.post("/api/v1/projects", json={
        "name": "My Project",
        "key": "my-proj",
        "visibility": "public",
    })
    assert response.status_code == 201
    data = response.json()
    assert data["key"] == "MY-PROJ"  # нормализован в uppercase
    assert data["name"] == "My Project"
    assert data["is_archived"] is False
    assert data["version"] == 1
    assert len(data["members"]) == 1  # owner добавлен как admin
    assert data["members"][0]["role"] == "admin"


async def test_create_project_key_uppercase(client: AsyncClient):
    response = await client.post("/api/v1/projects", json={
        "name": "Test",
        "key": "  abc  ",
    })
    assert response.status_code == 201
    assert response.json()["key"] == "ABC"


async def test_list_projects_returns_public(client: AsyncClient):
    await client.post("/api/v1/projects", json={"name": "Public", "key": "PUB1", "visibility": "public"})

    response = await client.get("/api/v1/projects")
    assert response.status_code == 200
    keys = [p["key"] for p in response.json()]
    assert "PUB1" in keys


async def test_list_projects_restricted_not_accessible(
    client: AsyncClient, db_session: AsyncSession
):
    other_user = User(
        id=uuid.uuid4(),
        email="other@test.com",
        display_name="Other",
        keycloak_id="other-kc-id",
        is_active=True,
    )
    db_session.add(other_user)

    private = Project(
        name="Private",
        key="PRIV99",
        visibility=ProjectVisibility.restricted,
        owner_id=other_user.id,
    )
    db_session.add(private)
    await db_session.commit()

    response = await client.get("/api/v1/projects")
    assert response.status_code == 200
    ids = [p["id"] for p in response.json()]
    assert str(private.id) not in ids


async def test_list_projects_restricted_accessible_if_member(
    client: AsyncClient, db_session: AsyncSession, stub_user: User
):
    other_user = User(
        id=uuid.uuid4(),
        email="owner2@test.com",
        display_name="Owner2",
        keycloak_id="owner2-kc-id",
        is_active=True,
    )
    db_session.add(other_user)

    project = Project(
        name="Restricted but joined",
        key="RJOIN",
        visibility=ProjectVisibility.restricted,
        owner_id=other_user.id,
    )
    db_session.add(project)
    await db_session.flush()

    db_session.add(ProjectMember(
        project_id=project.id,
        user_id=stub_user.id,
        role=ProjectMemberRole.member,
    ))
    await db_session.commit()

    response = await client.get("/api/v1/projects")
    assert response.status_code == 200
    ids = [p["id"] for p in response.json()]
    assert str(project.id) in ids


async def test_add_member(client: AsyncClient, db_session: AsyncSession):
    new_user = User(
        id=uuid.uuid4(),
        email="newmember@test.com",
        display_name="New Member",
        keycloak_id="newmember-kc-id",
        is_active=True,
    )
    db_session.add(new_user)
    await db_session.commit()

    create_resp = await client.post("/api/v1/projects", json={
        "name": "For Members Test",
        "key": "MEMTEST",
    })
    assert create_resp.status_code == 201
    project_id = create_resp.json()["id"]

    add_resp = await client.post(f"/api/v1/projects/{project_id}/members", json={
        "user_id": str(new_user.id),
        "role": "member",
    })
    assert add_resp.status_code == 201
    assert add_resp.json()["role"] == "member"

    get_resp = await client.get(f"/api/v1/projects/{project_id}")
    assert get_resp.status_code == 200
    member_ids = [m["user_id"] for m in get_resp.json()["members"]]
    assert str(new_user.id) in member_ids


async def test_add_member_duplicate(client: AsyncClient, stub_user: User):
    create_resp = await client.post("/api/v1/projects", json={"name": "Dup", "key": "DUPTEST"})
    project_id = create_resp.json()["id"]

    response = await client.post(f"/api/v1/projects/{project_id}/members", json={
        "user_id": str(stub_user.id),
        "role": "member",
    })
    assert response.status_code == 409
    assert response.json()["detail"]["code"] == "PROJECT_MEMBER_ALREADY_EXISTS"


async def test_archive_project(client: AsyncClient):
    create_resp = await client.post("/api/v1/projects", json={
        "name": "To Archive",
        "key": "ARCH1",
        "visibility": "public",
    })
    project_id = create_resp.json()["id"]

    archive_resp = await client.post(f"/api/v1/projects/{project_id}/archive")
    assert archive_resp.status_code == 200
    assert archive_resp.json()["is_archived"] is True

    list_resp = await client.get("/api/v1/projects")
    ids = [p["id"] for p in list_resp.json()]
    assert project_id not in ids

    get_resp = await client.get(f"/api/v1/projects/{project_id}")
    assert get_resp.status_code == 200
    assert get_resp.json()["is_archived"] is True


async def test_update_project_version_conflict(client: AsyncClient):
    create_resp = await client.post("/api/v1/projects", json={"name": "Versioned", "key": "VER1"})
    project_id = create_resp.json()["id"]

    response = await client.patch(f"/api/v1/projects/{project_id}", json={
        "name": "Updated",
        "version": 99,
    })
    assert response.status_code == 409
    assert response.json()["detail"]["code"] == "VERSION_CONFLICT"


async def test_get_restricted_project_without_access(
    client: AsyncClient, db_session: AsyncSession
):
    other = User(id=uuid.uuid4(), email="x@x.com", display_name="X", keycloak_id="x-kc")
    db_session.add(other)
    project = Project(name="Secret", key="SECRET9", visibility=ProjectVisibility.restricted, owner_id=other.id)
    db_session.add(project)
    await db_session.commit()

    response = await client.get(f"/api/v1/projects/{project.id}")
    assert response.status_code == 404
