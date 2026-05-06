import uuid

from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.project import Project, ProjectMember, ProjectMemberRole, ProjectVisibility
from app.models.user import User


async def _make_project_with_member_stub(db_session: AsyncSession, stub_user: User) -> str:
    """Creates a project owned by another user; adds stub_user as plain member (no manager rights)."""
    owner = User(
        id=uuid.uuid4(),
        email=f"owner_{uuid.uuid4().hex[:6]}@test.com",
        display_name="Owner",
        keycloak_id=f"kc-{uuid.uuid4().hex[:8]}",
        is_active=True,
    )
    db_session.add(owner)
    await db_session.flush()

    project = Project(
        name="Restricted Project",
        key=f"R{uuid.uuid4().hex[:5].upper()}",
        visibility=ProjectVisibility.restricted,
        owner_id=owner.id,
    )
    db_session.add(project)
    await db_session.flush()

    db_session.add(ProjectMember(project_id=project.id, user_id=owner.id, role=ProjectMemberRole.admin))
    db_session.add(ProjectMember(project_id=project.id, user_id=stub_user.id, role=ProjectMemberRole.member))
    await db_session.commit()
    return str(project.id)


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


async def test_create_project_duplicate_key(client: AsyncClient):
    await client.post("/api/v1/projects", json={"name": "First", "key": "DUPKEY1"})
    response = await client.post("/api/v1/projects", json={"name": "Second", "key": "DUPKEY1"})
    assert response.status_code == 409
    assert response.json()["detail"]["code"] == "DUPLICATE_PROJECT_KEY"


async def test_create_project_invalid_key(client: AsyncClient):
    response = await client.post("/api/v1/projects", json={"name": "Bad", "key": "??!!"})
    assert response.status_code == 422


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
    await db_session.flush()

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
    await db_session.flush()

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
    await db_session.flush()
    project = Project(name="Secret", key="SECRET9", visibility=ProjectVisibility.restricted, owner_id=other.id)
    db_session.add(project)
    await db_session.commit()

    response = await client.get(f"/api/v1/projects/{project.id}")
    assert response.status_code == 404


async def test_update_project_happy_path(client: AsyncClient):
    create_resp = await client.post("/api/v1/projects", json={"name": "Original", "key": "UPD1"})
    assert create_resp.status_code == 201
    project_id = create_resp.json()["id"]
    version = create_resp.json()["version"]

    r = await client.patch(f"/api/v1/projects/{project_id}", json={
        "name": "Updated Name", "version": version,
    })
    assert r.status_code == 200
    assert r.json()["name"] == "Updated Name"
    assert r.json()["version"] == version + 1


async def test_update_project_as_member_forbidden(
    client: AsyncClient, db_session: AsyncSession, stub_user: User
):
    project_id = await _make_project_with_member_stub(db_session, stub_user)

    get_r = await client.get(f"/api/v1/projects/{project_id}")
    version = get_r.json()["version"]

    r = await client.patch(f"/api/v1/projects/{project_id}", json={
        "name": "Hacked", "version": version,
    })
    assert r.status_code == 403
    assert r.json()["detail"]["code"] == "PERMISSION_DENIED"


async def test_archive_project_as_member_forbidden(
    client: AsyncClient, db_session: AsyncSession, stub_user: User
):
    project_id = await _make_project_with_member_stub(db_session, stub_user)

    r = await client.post(f"/api/v1/projects/{project_id}/archive")
    assert r.status_code == 403
    assert r.json()["detail"]["code"] == "PERMISSION_DENIED"


async def test_add_member_as_member_forbidden(
    client: AsyncClient, db_session: AsyncSession, stub_user: User
):
    project_id = await _make_project_with_member_stub(db_session, stub_user)

    r = await client.post(f"/api/v1/projects/{project_id}/members", json={
        "user_id": str(uuid.uuid4()), "role": "member",
    })
    assert r.status_code == 403
    assert r.json()["detail"]["code"] == "PERMISSION_DENIED"


async def test_remove_member(client: AsyncClient, db_session: AsyncSession):
    new_user = User(
        id=uuid.uuid4(), email="torem@test.com", display_name="To Remove",
        keycloak_id="torem-kc", is_active=True,
    )
    db_session.add(new_user)
    await db_session.commit()

    create_resp = await client.post("/api/v1/projects", json={"name": "RemTest", "key": "RMT1"})
    project_id = create_resp.json()["id"]

    await client.post(f"/api/v1/projects/{project_id}/members", json={
        "user_id": str(new_user.id), "role": "member",
    })

    del_r = await client.delete(f"/api/v1/projects/{project_id}/members/{new_user.id}")
    assert del_r.status_code == 204

    get_r = await client.get(f"/api/v1/projects/{project_id}")
    member_ids = [m["user_id"] for m in get_r.json()["members"]]
    assert str(new_user.id) not in member_ids


async def test_remove_member_as_member_forbidden(
    client: AsyncClient, db_session: AsyncSession, stub_user: User
):
    project_id = await _make_project_with_member_stub(db_session, stub_user)

    r = await client.delete(f"/api/v1/projects/{project_id}/members/{stub_user.id}")
    assert r.status_code == 403
    assert r.json()["detail"]["code"] == "PERMISSION_DENIED"


async def test_create_project_auto_creates_workflow(client: AsyncClient):
    r = await client.post("/api/v1/projects", json={"name": "Workflow Test", "key": "WFAUTO"})
    assert r.status_code == 201
    project_id = r.json()["id"]

    wf_r = await client.get(f"/api/v1/projects/{project_id}/workflows")
    assert wf_r.status_code == 200
    workflows = wf_r.json()
    assert len(workflows) == 1
    wf = workflows[0]
    assert wf["is_default"] is True
    assert wf["name"] == "Basic"

    status_names = [s["name"] for s in wf["statuses"]]
    assert "To Do" in status_names
    assert "In Progress" in status_names
    assert "Done" in status_names



async def test_get_project_task_types(client: AsyncClient):
    r = await client.post("/api/v1/projects", json={"name": "TT Test", "key": "TTTEST"})
    assert r.status_code == 201
    project_id = r.json()["id"]

    resp = await client.get(f"/api/v1/projects/{project_id}/task-types")
    assert resp.status_code == 200
    items = resp.json()["items"]
    # 5 system types always present
    assert len(items) >= 5
    keys = {t["key"] for t in items}
    assert keys >= {"task", "bug", "story", "epic", "decision"}
    for t in items:
        assert "id" in t
        assert "name" in t
        assert "is_system" in t


async def test_add_member_with_viewer_role(client: AsyncClient, db_session: AsyncSession):
    viewer = User(
        id=uuid.uuid4(), email="viewer@test.com", display_name="Viewer",
        keycloak_id=f"kc-{uuid.uuid4().hex[:8]}", is_active=True,
    )
    db_session.add(viewer)
    await db_session.flush()

    r = await client.post("/api/v1/projects", json={"name": "Viewer Test", "key": "VWTEST"})
    assert r.status_code == 201
    project_id = r.json()["id"]

    add_r = await client.post(f"/api/v1/projects/{project_id}/members", json={
        "user_id": str(viewer.id),
        "role": "viewer",
    })
    assert add_r.status_code == 201
    assert add_r.json()["role"] == "viewer"
