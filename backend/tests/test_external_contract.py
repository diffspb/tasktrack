"""Испытание поддержки контракта с офисом и системой требований v1.0 (ADR-024).

Проверяется сторона TaskTrack на тестовых поставщиках и ручном импорте — без внешних
сервисов. Разделы повторяют таблицу «Что предъявляет проект TaskTrack»:

- TT-08: проект связан с офисным строковым ID, репозиторием и редакцией регламента;
  совпадающие ID у разных поставщиков не смешиваются;
- TT-10: основания разных типов и редакций; задача из проблемы без выдуманного требования;
- TT-11: непринятый вход, невыделенный ресурс, неразрешённое изменение — видимая блокировка;
  действительное ограниченное разрешение позволяет ручное исполнение;
- TT-19: пробел становится предложением; руководитель связывает; импорт не запускает работу;
- TT-20: повтор и новая редакция не плодят задачи; две области — две работы;
- TT-21: повтор события безопасен; позднее событие не откатывает; пропуск восстанавливается
  снимком; приёмка старого результата не принимается за приёмку нового.

Плюс условия испытания: отозванное/истёкшее разрешение, недоступный поставщик, неизвестная
текущая редакция, частичная выгрузка, учебный источник — без ложной готовности.
"""
import hashlib
import json
import uuid
from datetime import UTC, datetime, timedelta

import pytest_asyncio
from httpx import AsyncClient
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.main import app
from app.models.external import ExternalEvent, ExternalRevision
from app.models.project import ProjectMember, ProjectMemberRole
from app.models.session import SessionCheckpoint
from app.models.task import Task
from app.models.user import User
from app.models.workflow import Status, StatusCategory, Transition
from app.schemas.project import ProjectCreate
from app.services import project_service

API = "/api/v1"
NOW = datetime.now(UTC)
PACKAGE = {
    "goal": "Проверить интерфейс", "expected_result": "Отчёт о проверке",
    "criteria": [{"text": "Все сценарии пройдены"}], "specialization": "qa",
}
OFFICE_TYPES = ["project", "allocation", "authorization", "input_acceptance", "recipient_acceptance",
                "regulation", "commitment", "office_process"]
REQ_TYPES = ["requirement", "verification_plan", "issue", "risk", "mitigation", "decision", "initiative",
             "migration", "evidence"]


def act_as(user: User) -> None:
    app.dependency_overrides[get_current_user] = lambda: user


async def _user(session: AsyncSession) -> User:
    u = User(id=uuid.uuid4(), email=f"u_{uuid.uuid4().hex[:8]}@t.com", display_name="U",
             keycloak_id=str(uuid.uuid4()), is_active=True)
    session.add(u)
    await session.flush()
    return u


def ref(provider: str, namespace: str, type_: str, id_: str, revision: str | None = None) -> dict:
    r = {"provider": provider, "namespace": namespace, "type": type_, "id": id_}
    return {**r, "revision": revision} if revision else r


class World:
    def __init__(self, client: AsyncClient, db: AsyncSession, owner: User):
        self.client, self.db, self.owner = client, db, owner
        self.sfx = uuid.uuid4().hex[:6]

    def key(self, name: str) -> str:
        return f"{name}-{self.sfx}"

    async def provider(self, name: str, kind: str, namespaces: list[str], fact_types: list[str],
                       training: bool = False) -> str:
        r = await self.client.post(f"{API}/external/providers", json={
            "key": self.key(name), "name": name, "kind": kind, "namespaces": namespaces,
            "fact_types": fact_types, "is_training": training,
        })
        assert r.status_code == 201, r.text
        return self.key(name)

    async def fact(self, provider: str, namespace: str, type_: str, id_: str, *, expect: int = 200,
                   observed_at: datetime | None = None, **kw) -> dict:
        body = {**ref(provider, namespace, type_, id_), "observed_at": (observed_at or NOW).isoformat(),
                "project_id": str(self.project.id), **kw}
        r = await self.client.post(f"{API}/external/facts", json=body)
        assert r.status_code == expect, r.text
        return r.json()

    async def task(self, title: str = "Работа", assignee: User | None = None, **kw) -> dict:
        r = await self.client.post(f"{API}/projects/{self.project.id}/tasks", json={
            "title": title, "assignee_id": str((assignee or self.worker).id), **kw})
        assert r.status_code == 201, r.text
        return r.json()

    async def issue(self, task_id: str, expect: int = 201) -> dict:
        await self.client.put(f"{API}/tasks/{task_id}/work-package/draft", json=PACKAGE)
        r = await self.client.post(f"{API}/tasks/{task_id}/work-package/issue")
        assert r.status_code == expect, r.text
        return r.json()

    async def basis(self, task_id: str, obj: dict, revision: str, role: str, expect: int = 201, **kw) -> dict:
        r = await self.client.post(f"{API}/tasks/{task_id}/bases",
                                   json={"object": obj, "revision": revision, "role": role, **kw})
        assert r.status_code == expect, r.text
        return r.json()

    async def readiness(self, task_id: str) -> dict:
        r = await self.client.get(f"{API}/tasks/{task_id}/readiness")
        assert r.status_code == 200, r.text
        return r.json()

    async def link(self, office_id: str = "P-PACK", **kw) -> dict:
        r = await self.client.put(f"{API}/projects/{self.project.id}/portfolio", json={
            "office_project": {"provider": self.office, "namespace": "portfolio", "id": office_id},
            "repository_url": "git@github.com:org/pack.git", "stage": "pilot", **kw,
        })
        assert r.status_code == 200, r.text
        return r.json()

    async def claim(self, task_id: str, user: User | None = None) -> tuple[int, dict]:
        act_as(user or self.worker)
        r = await self.client.post(f"{API}/tasks/{task_id}/sessions", json={"machine": "console"})
        act_as(self.owner)
        return r.status_code, r.json()

    def grant_claims(self, **kw) -> dict:
        return {
            "status": "granted", "recipient": ref(self.office, "portfolio", "project", "P-PACK"),
            "scope": "ручной пилот: одна консольная сессия", "resource": "console", "limit": "1 сессия, 8 часов",
            "valid_until": (NOW + timedelta(days=1)).isoformat(), **kw,
        }

    def acceptance_claims(self, input_ref: dict, **kw) -> dict:
        return {
            "input": input_ref, "recipient": ref(self.office, "portfolio", "project", "P-PACK"),
            "usage": "исполнение этапа pilot", "accepted_by": "owner@office", "accepted_at": NOW.isoformat(),
            "authority": "решение владельца программы OD-7", **kw,
        }


@pytest_asyncio.fixture
async def w(client: AsyncClient, db_session: AsyncSession, stub_user: User) -> World:
    stub_user.is_superuser = True   # registers providers; imports as instance admin
    world = World(client, db_session, stub_user)
    world.project = await project_service.create_project(
        db_session, ProjectCreate(name="Pack", key=uuid.uuid4().hex[:8].upper()), stub_user)
    world.worker = await _user(db_session)
    world.member = await _user(db_session)
    db_session.add_all([
        ProjectMember(project_id=world.project.id, user_id=world.worker.id, role=ProjectMemberRole.member),
        ProjectMember(project_id=world.project.id, user_id=world.member.id, role=ProjectMemberRole.member),
    ])
    await db_session.flush()
    world.office = await world.provider("office", "office", ["portfolio"], OFFICE_TYPES)
    world.req = await world.provider("req", "requirements", ["proj-pack", "proj-other"], REQ_TYPES)
    world.training = await world.provider("sandbox", "other", ["portfolio", "proj-pack"],
                                           OFFICE_TYPES + REQ_TYPES, training=True)
    await world.fact(world.office, "portfolio", "regulation", "REG-1", revision="r3",
                     content={"title": "Регламент портфеля", "status": "accepted"})
    return world


async def _ready_task(w: World) -> dict:
    """A portfolio task with an issued package, an accepted input and an owner's authorization."""
    await w.fact(w.req, "proj-pack", "requirement", "REQ-12", revision="v1",
                 content={"text": "Интерфейс отдаёт статус", "status": "accepted", "stages": ["pilot"]})
    await w.fact(w.req, "proj-pack", "verification_plan", "VP-3", revision="1",
                 content={"steps": ["вызвать /status"]})
    inp = ref(w.req, "proj-pack", "verification_plan", "VP-3")
    await w.fact(w.office, "portfolio", "input_acceptance", "IA-1", revision="1",
                 content=w.acceptance_claims({**inp, "revision": "1"}))
    await w.fact(w.office, "portfolio", "authorization", "AUTH-1", revision="1", content=w.grant_claims())
    t = await w.task()
    await w.basis(t["id"], ref(w.req, "proj-pack", "requirement", "REQ-12"), "v1", "normative")
    await w.basis(t["id"], inp, "1", "input")
    await w.basis(t["id"], ref(w.office, "portfolio", "authorization", "AUTH-1"), "1", "grant")
    await w.issue(t["id"])
    return t


def _codes(readiness: dict, key: str | None = None) -> set[str]:
    return {r["code"] for c in readiness["conditions"] if key in (None, c["key"]) for r in c["reasons"]}


async def _leave_initial(w: World, task_id: str) -> int:
    task = await w.db.get(Task, uuid.UUID(task_id))
    target = await w.db.scalar(
        select(Transition.to_status_id).join(Status, Status.id == Transition.to_status_id)
        .where(Transition.from_status_id == task.current_status_id, Status.category != StatusCategory.initial)
    )
    act_as(w.worker)
    r = await w.client.post(f"{API}/tasks/{task_id}/transition", json={"status_id": str(target)})
    act_as(w.owner)
    return r.status_code


# ── Реестр и закреплённые редакции ───────────────────────────────────────────

async def test_same_revision_other_bytes_is_integrity_conflict(w: World):
    first = await w.fact(w.req, "proj-pack", "requirement", "REQ-1", revision="v1", content={"text": "A"})
    again = await w.fact(w.req, "proj-pack", "requirement", "REQ-1", revision="v1", content={"text": "A"})
    assert again["outcome"]["created"] is False and again["revision"]["id"] == first["revision"]["id"]
    r = await w.fact(w.req, "proj-pack", "requirement", "REQ-1", revision="v1", content={"text": "B"}, expect=409)
    assert r["detail"]["code"] == "INTEGRITY_CONFLICT"


async def test_exact_bytes_are_pinned_and_hash_serves_as_revision(w: World):
    raw = "Требование в свободной форме\r\n".encode()
    import base64
    r = await w.fact(w.req, "proj-pack", "requirement", "REQ-RAW",
                     content_base64=base64.b64encode(raw).decode(), media_type="text/plain")
    digest = hashlib.sha256(raw).hexdigest()
    assert r["revision"]["revision"] == f"sha256:{digest}" and r["revision"]["sha256"] == digest
    row = await w.db.get(ExternalRevision, uuid.UUID(r["revision"]["id"]))
    assert row.content == raw


async def test_mutable_pointers_are_not_pinned(w: World):
    for rev in ("latest", "HEAD", "main", "refs/heads/feature", "current"):
        r = await w.fact(w.req, "proj-pack", "requirement", "REQ-2", revision=rev, content={"x": 1}, expect=422)
        assert r["detail"]["code"] == "REVISION_NOT_PINNED"


async def test_provider_speaks_only_for_its_namespaces_and_types(w: World):
    r = await w.fact(w.req, "portfolio", "requirement", "REQ-3", revision="1", content={}, expect=403)
    assert r["detail"]["code"] == "NAMESPACE_NOT_ALLOWED"
    # The requirements system is not authoritative for allocations: kept as an unverified message.
    msg = await w.fact(w.req, "proj-pack", "allocation", "AL-1", revision="1", content={"status": "granted"})
    assert msg["revision"]["verified"] is False and msg["outcome"]["effect"] == "unverified_message"
    assert msg["object"]["current_revision"] is None


async def test_import_rights(w: World):
    act_as(w.member)   # a plain member may not register facts
    r = await w.client.post(f"{API}/external/facts", json={
        **ref(w.req, "proj-pack", "requirement", "REQ-4"), "revision": "1", "content": {},
        "observed_at": NOW.isoformat(), "project_id": str(w.project.id)})
    assert r.status_code == 403
    r = await w.client.post(f"{API}/external/providers", json={
        "key": "rogue", "name": "R", "kind": "other"})
    assert r.status_code == 403
    act_as(w.owner)


async def test_identity_change_keeps_history(w: World):
    await w.fact(w.req, "proj-pack", "requirement", "REQ-NEW", revision="1", content={"text": "A"})
    r = await w.client.post(f"{API}/external/aliases", json={
        "old": ref(w.req, "proj-pack", "requirement", "REQ-OLD"),
        "current": ref(w.req, "proj-pack", "requirement", "REQ-NEW"), "reason": "перенумерация каталога"})
    assert r.status_code == 201, r.text
    r = await w.client.get(f"{API}/external/objects", params=ref(w.req, "proj-pack", "requirement", "REQ-OLD"))
    assert r.json()["object"]["ext_id"] == "REQ-NEW"


# ── TT-08 ────────────────────────────────────────────────────────────────────

async def test_tt08_project_linked_to_office_string_id(w: World):
    link = await w.link(regulation=ref(w.office, "portfolio", "regulation", "REG-1", "r3"))
    assert link["office_project"]["ext_id"] == "P-PACK"
    assert link["office_project"]["provider"] == w.office
    assert link["repository_url"] == "git@github.com:org/pack.git"
    assert link["regulation_revision"] == "r3" and link["stage"] == "pilot"
    assert link["recipient"] == f"{w.office}/portfolio/project/P-PACK"
    # The local project UUID is unchanged and no UUID was invented for the office project.
    assert link["project_id"] == str(w.project.id)

    # Same ID at another provider is a different object; one office project ↔ one local project.
    office2 = await w.provider("office2", "office", ["portfolio"], OFFICE_TYPES)
    other = await project_service.create_project(
        w.db, ProjectCreate(name="Other", key=uuid.uuid4().hex[:8].upper()), w.owner)
    body = {"repository_url": "git@github.com:org/other.git"}
    r = await w.client.put(f"{API}/projects/{other.id}/portfolio", json={
        **body, "office_project": {"provider": w.office, "namespace": "portfolio", "id": "P-PACK"}})
    assert r.status_code == 409 and r.json()["detail"]["code"] == "OFFICE_PROJECT_ALREADY_LINKED"
    r = await w.client.put(f"{API}/projects/{other.id}/portfolio", json={
        **body, "office_project": {"provider": office2, "namespace": "portfolio", "id": "P-PACK"}})
    assert r.status_code == 200
    assert r.json()["office_project"]["id"] != link["office_project"]["id"]


async def test_tt08_regulation_must_be_pinned_and_real(w: World):
    r = await w.client.put(f"{API}/projects/{w.project.id}/portfolio", json={
        "office_project": {"provider": w.office, "namespace": "portfolio", "id": "P-PACK"},
        "repository_url": "x", "regulation": ref(w.office, "portfolio", "regulation", "REG-1", "r9")})
    assert r.json()["detail"]["code"] == "REVISION_UNKNOWN"
    r = await w.client.put(f"{API}/projects/{w.project.id}/portfolio", json={
        "office_project": {"provider": w.training, "namespace": "portfolio", "id": "P-PACK"}, "repository_url": "x"})
    assert r.json()["detail"]["code"] == "TRAINING_PROVIDER_FOR_REAL_PROJECT"


async def test_tt08_only_project_admin_links(w: World):
    act_as(w.worker)
    r = await w.client.put(f"{API}/projects/{w.project.id}/portfolio", json={
        "office_project": {"provider": w.office, "namespace": "portfolio", "id": "P-PACK"}, "repository_url": "x"})
    assert r.status_code == 403
    act_as(w.owner)


async def test_standalone_project_keeps_local_process(w: World):
    t = await w.task()
    ready = await w.readiness(t["id"])
    assert ready == {**ready, "mode": "standalone", "ready": True, "conditions": []}
    code, _ = await w.claim(t["id"])
    assert code == 201


# ── TT-10 ────────────────────────────────────────────────────────────────────

async def test_tt10_bases_have_types_roles_and_revisions(w: World):
    await w.link()
    await w.fact(w.req, "proj-pack", "issue", "ISS-7", revision="2", content={"text": "Падает статус"})
    await w.fact(w.req, "proj-pack", "decision", "DEC-1", revision="a", content={"text": "Чинить в pilot"})
    t = await w.task()
    await w.basis(t["id"], ref(w.req, "proj-pack", "issue", "ISS-7"), "2", "cause", meaning="причина работы")
    await w.basis(t["id"], ref(w.req, "proj-pack", "decision", "DEC-1"), "a", "reference")
    bases = (await w.client.get(f"{API}/tasks/{t['id']}/bases")).json()
    assert {(b["object"]["type"], b["revision"], b["role"]) for b in bases} == {
        ("issue", "2", "cause"), ("decision", "a", "reference")}
    # A task born from an issue needs no invented requirement: the normative condition holds.
    ready = await w.readiness(t["id"])
    assert next(c for c in ready["conditions"] if c["key"] == "normative")["ok"]

    r = await w.basis(t["id"], ref(w.req, "proj-pack", "issue", "ISS-7"), "2", "grant", expect=422)
    assert r["detail"]["code"] == "BASIS_ROLE_TYPE_MISMATCH"
    r = await w.basis(t["id"], ref(w.req, "proj-pack", "issue", "ISS-7"), "3", "input", expect=422)
    assert r["detail"]["code"] == "REVISION_UNKNOWN"


async def test_tt10_issued_package_pins_bases_and_old_versions_stay(w: World):
    await w.fact(w.req, "proj-pack", "issue", "ISS-8", revision="1", content={"text": "A"})
    t = await w.task()
    v1 = await w.issue(t["id"])
    assert "bases" not in v1["content"]     # a task without bases keeps the previous shape
    await w.basis(t["id"], ref(w.req, "proj-pack", "issue", "ISS-8"), "1", "cause")
    state = (await w.client.get(f"{API}/tasks/{t['id']}/work-package")).json()
    assert state["state"] == "draft_changed"
    v2 = (await w.client.post(f"{API}/tasks/{t['id']}/work-package/issue")).json()
    assert v2["version"] == 2 and v2["content"]["bases"][0]["id"] == "ISS-8"
    old = (await w.client.get(f"{API}/work-packages/{v1['id']}")).json()
    assert old["content"] == v1["content"] and old["digest"] == v1["digest"]


# ── TT-11 ────────────────────────────────────────────────────────────────────

async def test_tt11_missing_input_acceptance_and_grant_block_visibly(w: World):
    await w.link()
    await w.fact(w.req, "proj-pack", "verification_plan", "VP-9", revision="1", content={"steps": []})
    t = await w.task()
    await w.basis(t["id"], ref(w.req, "proj-pack", "verification_plan", "VP-9"), "1", "input")
    ready = await w.readiness(t["id"])
    assert ready["mode"] == "portfolio" and not ready["ready"]
    assert {"NO_WORK_PACKAGE"} <= _codes(ready, "package")
    assert _codes(ready, "inputs") == {"INPUT_NOT_ACCEPTED"}
    assert _codes(ready, "grant") == {"NO_GRANT"}

    await w.issue(t["id"])      # a full package can be issued with inputs still expected
    code, body = await w.claim(t["id"])
    assert code == 409 and body["detail"]["code"] == "TASK_NOT_READY"
    assert {r["code"] for r in body["detail"]["reasons"]} == {"INPUT_NOT_ACCEPTED", "NO_GRANT"}
    assert await _leave_initial(w, t["id"]) == 409


async def test_tt11_valid_bounded_authorization_allows_manual_execution(w: World):
    await w.link(regulation=ref(w.office, "portfolio", "regulation", "REG-1", "r3"))
    t = await _ready_task(w)
    ready = await w.readiness(t["id"])
    assert ready["ready"], ready
    grant = next(c for c in ready["conditions"] if c["key"] == "grant")
    assert grant["facts"][0]["claims"]["limit"] == "1 сессия, 8 часов" and grant["facts"][0]["as_of"]
    assert await _leave_initial(w, t["id"]) == 200
    code, _ = await w.claim(t["id"])
    assert code == 201


async def test_tt11_acceptance_must_match_exact_input_and_be_complete(w: World):
    await w.link()
    t = await _ready_task(w)
    inp = ref(w.req, "proj-pack", "verification_plan", "VP-3")
    # A new acceptance revision for another input revision / without authority replaces the valid one.
    await w.fact(w.office, "portfolio", "input_acceptance", "IA-1", revision="2", supersedes="1",
                 content=w.acceptance_claims({**inp, "revision": "0"}))
    ready = await w.readiness(t["id"])
    assert _codes(ready, "inputs") == {"INPUT_NOT_ACCEPTED"}
    assert "другая редакция" in ready["conditions"][1]["reasons"][0]["message"]
    await w.fact(w.office, "portfolio", "input_acceptance", "IA-1", revision="3", supersedes="2",
                 content=w.acceptance_claims({**inp, "revision": "1"}, authority=None))
    assert "authority" in (await w.readiness(t["id"]))["conditions"][1]["reasons"][0]["message"]


async def test_tt11_need_without_allocation_expired_and_revoked_grants(w: World):
    await w.link()
    t = await _ready_task(w)
    auth = ref(w.office, "portfolio", "authorization", "AUTH-1")

    await w.fact(w.office, "portfolio", "authorization", "AUTH-1", revision="2", supersedes="1",
                 content=w.grant_claims(status="requested"))
    assert _codes(await w.readiness(t["id"]), "grant") == {"GRANT_NOT_GRANTED"}

    await w.fact(w.office, "portfolio", "authorization", "AUTH-1", revision="3", supersedes="2",
                 content=w.grant_claims(valid_until=(NOW - timedelta(hours=1)).isoformat()))
    assert _codes(await w.readiness(t["id"]), "grant") == {"GRANT_EXPIRED"}

    await w.fact(w.office, "portfolio", "authorization", "AUTH-1", revision="4", supersedes="3",
                 content=w.grant_claims())
    assert (await w.readiness(t["id"]))["ready"]
    revoked = await w.fact(w.office, "portfolio", "authorization", "AUTH-1", revision="5", supersedes="4",
                           revoked=True, content={"status": "revoked", "reason": "перераспределение GPU"})
    assert revoked["object"]["status"] == "revoked"
    ready = await w.readiness(t["id"])
    assert _codes(ready, "grant") == {"GRANT_REVOKED"}
    code, _ = await w.claim(t["id"])
    assert code == 409
    # The revocation is history, not deletion.
    detail = (await w.client.get(f"{API}/external/objects", params=auth)).json()
    assert [r["revision"] for r in detail["revisions"]] == ["1", "2", "3", "4", "5"]


async def test_tt11_training_source_never_confirms_real_work(w: World):
    await w.link()
    t = await _ready_task(w)
    await w.fact(w.training, "portfolio", "authorization", "SANDBOX-AUTH", revision="1", content=w.grant_claims())
    await w.client.delete(f"{API}/bases/{(await _basis_id(w, t['id'], 'grant'))}")
    await w.basis(t["id"], ref(w.training, "portfolio", "authorization", "SANDBOX-AUTH"), "1", "grant")
    await w.client.post(f"{API}/tasks/{t['id']}/work-package/issue")
    assert _codes(await w.readiness(t["id"]), "grant") == {"GRANT_TRAINING"}


async def test_training_project_accepts_training_facts(w: World):
    r = await w.client.put(f"{API}/projects/{w.project.id}/portfolio", json={
        "office_project": {"provider": w.training, "namespace": "portfolio", "id": "P-SANDBOX"},
        "repository_url": "git@github.com:org/sandbox.git", "is_training": True})
    assert r.status_code == 200, r.text
    await w.fact(w.training, "portfolio", "authorization", "SB-AUTH", revision="1",
                 content=w.grant_claims(recipient=ref(w.training, "portfolio", "project", "P-SANDBOX")))
    t = await w.task()
    await w.basis(t["id"], ref(w.training, "portfolio", "authorization", "SB-AUTH"), "1", "grant")
    await w.issue(t["id"])
    assert (await w.readiness(t["id"]))["ready"]


async def test_tt11_unverified_message_does_not_satisfy(w: World):
    await w.link()
    await w.fact(w.req, "proj-pack", "authorization", "RUMOUR", revision="1", content=w.grant_claims())
    t = await w.task()
    await w.basis(t["id"], ref(w.req, "proj-pack", "authorization", "RUMOUR"), "1", "grant")
    await w.issue(t["id"])
    assert _codes(await w.readiness(t["id"]), "grant") == {"GRANT_UNVERIFIED"}


async def test_tt11_unavailable_provider_and_unknown_current_state(w: World):
    """Pinned policy may use an accepted pinned snapshot (with its date); confirm_current with
    an unknown state blocks; a disabled provider's grant never counts."""
    await w.link()
    t = await _ready_task(w)
    ready = await w.readiness(t["id"])
    normative = next(c for c in ready["conditions"] if c["key"] == "normative")
    assert ready["ready"] and normative["facts"][0]["as_of"]

    await w.fact(w.req, "proj-pack", "requirement", "REQ-CUR", revision="1",
                 content={"status": "accepted"})     # first revision: known, not confirmed current
    await w.basis(t["id"], ref(w.req, "proj-pack", "requirement", "REQ-CUR"), "1", "normative",
                  freshness="confirm_current")
    await w.client.post(f"{API}/tasks/{t['id']}/work-package/issue")
    assert _codes(await w.readiness(t["id"]), "blockers") == {"BASIS_STATE_UNKNOWN"}
    await w.fact(w.req, "proj-pack", "requirement", "REQ-CUR", revision="1", content={"status": "accepted"},
                 confirmed_current=True)
    assert (await w.readiness(t["id"]))["ready"]

    provider = next(p for p in (await w.client.get(f"{API}/external/providers")).json() if p["key"] == w.office)
    await w.client.patch(f"{API}/external/providers/{provider['id']}", json={"active": False})
    assert "PROVIDER_INACTIVE" in _codes(await w.readiness(t["id"]), "grant")


async def test_tt11_new_revision_of_mandatory_basis_waits_for_impact_decision(w: World):
    await w.link()
    t = await _ready_task(w)
    package_before = (await w.client.get(f"{API}/tasks/{t['id']}/work-package")).json()["current"]
    code, session = await w.claim(t["id"])
    assert code == 201

    new = await w.fact(w.req, "proj-pack", "requirement", "REQ-12", revision="v2", supersedes="v1",
                       content={"text": "Статус и версия", "status": "accepted", "stages": ["pilot"]})
    assert new["outcome"]["effect"] == "current_changed"
    ready = await w.readiness(t["id"])
    assert _codes(ready, "blockers") == {"IMPACT_PENDING"}
    # The running session gets a visible problem and a checkpoint; nothing is killed.
    notes = (await w.db.scalars(select(SessionCheckpoint.note).where(
        SessionCheckpoint.session_id == uuid.UUID(session["id"])))).all()
    assert any("оценка влияния" in n for n in notes)
    assert (await w.client.get(f"{API}/sessions/{session['id']}")).json()["state"] == "active"
    # The issued package is not rewritten by the new fact.
    assert (await w.client.get(f"{API}/work-packages/{package_before['id']}")).json() == package_before

    [assessment] = (await w.client.get(f"{API}/tasks/{t['id']}/impact-assessments")).json()
    assert (assessment["old_revision"], assessment["new_revision"]) == ("v1", "v2")
    url = f"{API}/impact-assessments/{assessment['id']}/decide"
    act_as(w.worker)
    assert (await w.client.post(url, json={"decision": "continue", "rationale": "x", "authority": "y"})).status_code == 403
    act_as(w.owner)
    r = await w.client.post(url, json={"decision": "continue", "rationale": "изменение не касается пилота"})
    assert r.json()["detail"]["code"] == "AUTHORITY_REQUIRED"
    r = await w.client.post(url, json={"decision": "continue", "rationale": "изменение не касается пилота",
                                       "authority": "владелец программы, OD-9"})
    assert r.status_code == 200 and r.json()["decision"] == "continue"
    assert (await w.readiness(t["id"]))["ready"]


async def test_tt11_reissue_and_stop_decisions(w: World):
    await w.link()
    t = await _ready_task(w)
    await w.fact(w.req, "proj-pack", "requirement", "REQ-12", revision="v2", supersedes="v1",
                 content={"status": "accepted", "stages": ["pilot"]})
    [a] = (await w.client.get(f"{API}/tasks/{t['id']}/impact-assessments")).json()
    await w.client.post(f"{API}/impact-assessments/{a['id']}/decide",
                        json={"decision": "reissue", "rationale": "новая редакция обязательна"})
    assert _codes(await w.readiness(t["id"])) == {"WORK_PACKAGE_OUTDATED"}
    v2 = (await w.client.post(f"{API}/tasks/{t['id']}/work-package/issue")).json()
    assert {b["revision"] for b in v2["content"]["bases"] if b["role"] == "normative"} == {"v2"}
    assert (await w.readiness(t["id"]))["ready"]

    await w.fact(w.req, "proj-pack", "requirement", "REQ-12", revision="v3", supersedes="v2",
                 content={"status": "accepted", "stages": ["pilot"]})
    pending = [x for x in (await w.client.get(f"{API}/tasks/{t['id']}/impact-assessments")).json()
               if x["status"] == "pending"]
    await w.client.post(f"{API}/impact-assessments/{pending[0]['id']}/decide",
                        json={"decision": "stop", "rationale": "требование пересматривается"})
    assert _codes(await w.readiness(t["id"])) == {"BLOCKER"}


async def test_tt11_unknown_order_keeps_current_and_waits_for_reconciliation(w: World):
    await w.link()
    t = await _ready_task(w)
    r = await w.fact(w.req, "proj-pack", "requirement", "REQ-12", revision="x9",
                     content={"status": "accepted"})     # no supersession, no confirmation
    assert r["outcome"]["effect"] == "pending_reconciliation"
    assert r["object"]["current_revision"] == "v1" and r["object"]["revision_state"] == "pending_reconciliation"
    assert (await w.client.get(f"{API}/tasks/{t['id']}/impact-assessments")).json() == []


async def test_tt11_registered_blocker(w: World):
    await w.link()
    t = await _ready_task(w)
    b = (await w.client.post(f"{API}/tasks/{t['id']}/blockers", json={"reason": "стенд занят"})).json()
    assert _codes(await w.readiness(t["id"])) == {"BLOCKER"}
    await w.client.post(f"{API}/blockers/{b['id']}/resolve", json={"resolution": "стенд свободен"})
    assert (await w.readiness(t["id"]))["ready"]


async def _basis_id(w: World, task_id: str, role: str) -> str:
    return next(b["id"] for b in (await w.client.get(f"{API}/tasks/{task_id}/bases")).json() if b["role"] == role)


# ── TT-19 / TT-20 ────────────────────────────────────────────────────────────

def _proposal(w: World, revision: str = "v1", scope: str = "status-endpoint", **kw) -> dict:
    return {
        "provider": w.req, "stage": "pilot", "work_kind": "verification",
        "basis": ref(w.req, "proj-pack", "requirement", "REQ-12", revision),
        "verification_plan": ref(w.req, "proj-pack", "verification_plan", "VP-3", "1"),
        "work_scope_key": scope, "result_scope": "эндпоинт /status",
        "expected_output": "Отчёт о проверке", "reason": "нет подтверждения соблюдения", **kw,
    }


async def _tasks_count(w: World) -> int:
    return await w.db.scalar(select(func.count()).select_from(Task).where(Task.project_id == w.project.id))


async def test_tt19_gap_becomes_proposal_and_manager_links_it(w: World):
    await w.link()
    await w.fact(w.req, "proj-pack", "requirement", "REQ-12", revision="v1", content={"status": "accepted"})
    await w.fact(w.req, "proj-pack", "verification_plan", "VP-3", revision="1", content={})
    before = await _tasks_count(w)
    r = await w.client.post(f"{API}/projects/{w.project.id}/work-proposals", json=_proposal(w))
    assert r.status_code == 200, r.text
    proposal = r.json()["proposal"]
    assert r.json()["created"] and proposal["status"] == "open" and proposal["task_id"] is None
    assert proposal["versions"][0]["verification_plan_revision"] == "1"
    assert await _tasks_count(w) == before     # import never creates or starts work

    existing = await w.task("Проверка статуса")
    act_as(w.member)
    r = await w.client.post(f"{API}/work-proposals/{proposal['id']}/decide",
                            json={"action": "link", "task_id": existing["id"]})
    assert r.status_code == 403
    act_as(w.owner)
    r = await w.client.post(f"{API}/work-proposals/{proposal['id']}/decide",
                            json={"action": "link", "task_id": existing["id"], "reason": "уже в работе"})
    assert r.json()["status"] == "linked" and r.json()["task_id"] == existing["id"]
    bases = (await w.client.get(f"{API}/tasks/{existing['id']}/bases")).json()
    assert [(b["role"], b["revision"]) for b in bases] == [("cause", "v1")]
    assert not (await w.readiness(existing["id"]))["ready"]   # a proposal allocates nothing


async def test_tt19_reject_and_defer_need_reason_and_keep_history(w: World):
    await w.fact(w.req, "proj-pack", "requirement", "REQ-12", revision="v1", content={})
    await w.fact(w.req, "proj-pack", "verification_plan", "VP-3", revision="1", content={})
    p = (await w.client.post(f"{API}/projects/{w.project.id}/work-proposals", json=_proposal(w))).json()["proposal"]
    url = f"{API}/work-proposals/{p['id']}/decide"
    assert (await w.client.post(url, json={"action": "reject"})).json()["detail"]["code"] == "REASON_REQUIRED"
    assert (await w.client.post(url, json={"action": "defer", "reason": "после релиза"})).json()["status"] == "deferred"
    r = (await w.client.post(url, json={"action": "reject", "reason": "дублирует REQ-10"})).json()
    assert r["status"] == "rejected" and r["decision_reason"] == "дублирует REQ-10"
    assert (await w.client.post(url, json={"action": "defer", "reason": "x"})).status_code == 409
    # A repeat of the rejected proposal changes nothing and opens nothing.
    again = (await w.client.post(f"{API}/projects/{w.project.id}/work-proposals", json=_proposal(w))).json()
    assert not again["created"] and not again["new_version"] and again["proposal"]["status"] == "rejected"


async def test_tt20_repeat_and_new_revision_do_not_multiply_tasks(w: World):
    await w.fact(w.req, "proj-pack", "requirement", "REQ-12", revision="v1", content={})
    await w.fact(w.req, "proj-pack", "verification_plan", "VP-3", revision="1", content={})
    url = f"{API}/projects/{w.project.id}/work-proposals"
    first = (await w.client.post(url, json=_proposal(w, event_id="gap-1"))).json()
    replay = (await w.client.post(url, json=_proposal(w, event_id="gap-1"))).json()
    assert replay["replayed"] and replay["proposal"]["id"] == first["proposal"]["id"]
    repeat = (await w.client.post(url, json=_proposal(w, event_id="gap-2"))).json()   # new command id, same key
    assert not repeat["created"] and not repeat["new_version"]
    assert repeat["proposal"]["id"] == first["proposal"]["id"]

    decided = (await w.client.post(f"{API}/work-proposals/{first['proposal']['id']}/decide",
                                   json={"action": "create_task", "title": "Проверить REQ-12"})).json()
    assert decided["status"] == "converted"
    tasks_after_convert = await _tasks_count(w)

    await w.fact(w.req, "proj-pack", "requirement", "REQ-12", revision="v2", supersedes="v1", content={"n": 2})
    newer = (await w.client.post(url, json=_proposal(w, revision="v2"))).json()
    assert newer["new_version"] and not newer["created"]
    assert newer["proposal"]["id"] == first["proposal"]["id"] and newer["proposal"]["current_version"] == 2
    assert newer["proposal"]["updated_since_decision"] and newer["proposal"]["status"] == "converted"
    assert await _tasks_count(w) == tasks_after_convert
    # The new revision is a reason for impact assessment on the converted task.
    [a] = (await w.client.get(f"{API}/tasks/{decided['task_id']}/impact-assessments")).json()
    assert (a["old_revision"], a["new_revision"]) == ("v1", "v2")

    # Another meaningful scope of the same requirement is another work with its own key.
    other = (await w.client.post(url, json=_proposal(w, revision="v2", scope="version-field"))).json()
    assert other["created"] and other["proposal"]["id"] != first["proposal"]["id"]
    task2 = (await w.client.post(f"{API}/work-proposals/{other['proposal']['id']}/decide",
                                 json={"action": "create_task"})).json()
    assert task2["task_id"] != decided["task_id"]


async def test_tt20_merge_into_another_proposal(w: World):
    await w.fact(w.req, "proj-pack", "requirement", "REQ-12", revision="v1", content={})
    await w.fact(w.req, "proj-pack", "verification_plan", "VP-3", revision="1", content={})
    url = f"{API}/projects/{w.project.id}/work-proposals"
    a = (await w.client.post(url, json=_proposal(w, scope="a"))).json()["proposal"]
    b = (await w.client.post(url, json=_proposal(w, scope="b"))).json()["proposal"]
    r = (await w.client.post(f"{API}/work-proposals/{b['id']}/decide",
                             json={"action": "merge", "merge_into_id": a["id"], "reason": "одна проверка"})).json()
    assert r["status"] == "merged" and r["merged_into_id"] == a["id"]


# ── TT-21 ────────────────────────────────────────────────────────────────────

async def test_tt21_event_repeat_is_safe_and_conflict_rejected(w: World):
    body = dict(revision="1", content={"status": "granted"}, event_id="evt-100")
    first = await w.fact(w.office, "portfolio", "allocation", "AL-7", **body)
    again = await w.fact(w.office, "portfolio", "allocation", "AL-7", **body)
    assert not first["replayed"] and again["replayed"] and again["revision"]["id"] == first["revision"]["id"]
    events = (await w.db.scalars(select(ExternalEvent).where(ExternalEvent.event_id == "evt-100"))).all()
    assert len(events) == 1 and events[0].contract_version == "tasktrack-external-v1"
    r = await w.fact(w.office, "portfolio", "allocation", "AL-7", expect=409,
                     revision="1", content={"status": "revoked"}, event_id="evt-100")
    assert r["detail"]["code"] == "EVENT_CONFLICT"
    # Rights are checked on a repeat too.
    act_as(w.member)
    r = await w.client.post(f"{API}/external/facts", json={
        **ref(w.office, "portfolio", "allocation", "AL-7"), **body, "observed_at": NOW.isoformat(),
        "project_id": str(w.project.id)})
    assert r.status_code == 403
    act_as(w.owner)
    r = await w.fact(w.office, "portfolio", "allocation", "AL-8", expect=422, revision="1", content={},
                     contract_version="tasktrack-external-v2")
    assert r["detail"]["code"] == "CONTRACT_VERSION_UNSUPPORTED"


async def test_tt21_late_event_does_not_roll_back(w: World):
    await w.fact(w.req, "proj-pack", "requirement", "REQ-20", revision="a", content={"n": 1})
    await w.fact(w.req, "proj-pack", "requirement", "REQ-20", revision="b", supersedes="a", content={"n": 2},
                 confirmed_current=True, observed_at=NOW)
    late = await w.fact(w.req, "proj-pack", "requirement", "REQ-20", revision="a", content={"n": 1},
                        confirmed_current=True, observed_at=NOW - timedelta(days=1))
    assert late["outcome"]["effect"] == "stale" and late["object"]["current_revision"] == "b"
    older_confirm = await w.fact(w.req, "proj-pack", "requirement", "REQ-20", revision="c", content={"n": 3},
                                 confirmed_current=True, observed_at=NOW - timedelta(hours=1))
    assert older_confirm["outcome"]["effect"] == "stale" and older_confirm["object"]["current_revision"] == "b"


async def test_tt21_gap_restored_by_snapshot_partial_never_deletes(w: World):
    await w.fact(w.req, "proj-pack", "requirement", "REQ-30", revision="1", content={"n": 1})
    await w.fact(w.req, "proj-pack", "requirement", "REQ-31", revision="1", content={"n": 1})
    # Events for REQ-30 revisions 2 and 3 were missed; the authoritative export restores the state.
    snap = {"provider": w.req, "namespace": "proj-pack", "types": ["requirement"], "completeness": "partial",
            "as_of": NOW.isoformat(), "cursor": "opaque:7f3a", "project_id": str(w.project.id),
            "items": [{"type": "requirement", "id": "REQ-30", "revision": "3", "content": {"n": 3}}]}
    r = await w.client.post(f"{API}/external/snapshots", json=snap)
    assert r.status_code == 200, r.text
    assert r.json()["cursor"] == "opaque:7f3a" and r.json()["result"]["absent_not_deleted"] == []
    obj = (await w.client.get(f"{API}/external/objects",
                              params=ref(w.req, "proj-pack", "requirement", "REQ-30"))).json()["object"]
    assert (obj["current_revision"], obj["revision_state"]) == ("3", "current")
    untouched = (await w.client.get(f"{API}/external/objects",
                                    params=ref(w.req, "proj-pack", "requirement", "REQ-31"))).json()["object"]
    assert untouched["current_revision"] == "1" and untouched["status"] == "active"

    # A full export lists what is absent, but absence is not deletion.
    full = {**snap, "completeness": "full", "as_of": (NOW + timedelta(minutes=1)).isoformat()}
    r = (await w.client.post(f"{API}/external/snapshots", json=full)).json()
    assert "requirement/REQ-31" in r["result"]["absent_not_deleted"]
    assert (await w.client.get(f"{API}/external/objects", params=ref(
        w.req, "proj-pack", "requirement", "REQ-31"))).json()["object"]["status"] == "active"

    # An older export does not roll the current revision back.
    stale = {**snap, "as_of": (NOW - timedelta(days=2)).isoformat(),
             "items": [{"type": "requirement", "id": "REQ-30", "revision": "1", "content": {"n": 1}}]}
    r = (await w.client.post(f"{API}/external/snapshots", json=stale)).json()
    assert r["result"]["items"][0]["effect"] == "stale"
    assert r["result"]["items"][0]["current_revision"] == "3"


async def test_tt21_acceptance_of_old_result_is_not_acceptance_of_new(w: World):
    reviewer = await _user(w.db)
    w.db.add(ProjectMember(project_id=w.project.id, user_id=reviewer.id, role=ProjectMemberRole.member,
                           is_reviewer=True))
    await w.db.flush()
    t = await w.task()
    package = await w.issue(t["id"])

    async def accepted_result(summary: str) -> dict:
        act_as(w.worker)
        p = (await w.client.post(f"{API}/tasks/{t['id']}/proposals", json={
            "summary": summary, "criteria": [{"key": "c1", "status": "met"}],
            "links": [{"kind": "pr", "url": "https://github.com/org/pack/pull/1"}]})).json()
        act_as(reviewer)
        r = await w.client.post(f"{API}/proposals/{p['id']}/reviews", json={
            "verdict": "accepted", "rationale": "ok", "criteria": [{"key": "c1", "verdict": "met"}]})
        assert r.status_code == 201, r.text
        act_as(w.owner)
        return p

    p1 = await accepted_result("v1")
    task = (await w.client.post(f"{API}/tasks/{t['id']}/delivery", json={"target": "office:P-PACK"})).json()
    d1 = task["delivery"]["delivery_id"]
    assert task["delivery"]["proposal_id"] == p1["id"] and task["delivery"]["work_package_id"] == package["id"]
    acc = {"accepted_by": "owner@office", "accepted_at": NOW.isoformat(), "source": "office-journal",
           "usage_scope": "пилот", "authority": "OD-7"}
    task = (await w.client.post(f"{API}/tasks/{t['id']}/recipient-acceptance", json=acc)).json()
    assert task["recipient_acceptance"]["delivery_id"] == d1

    p2 = await accepted_result("v2")
    task = (await w.client.post(f"{API}/tasks/{t['id']}/delivery", json={"target": "office:P-PACK"})).json()
    d2 = task["delivery"]["delivery_id"]
    assert d2 != d1 and task["delivery"]["proposal_id"] == p2["id"] and task["recipient_acceptance"] is None
    # A late record for the old delivery stays bound to it and does not accept the new one.
    task = (await w.client.post(f"{API}/tasks/{t['id']}/recipient-acceptance",
                                json={**acc, "delivery_id": d1, "ref": "late"})).json()
    assert task["recipient_acceptance"] is None

    view = (await w.client.get(f"{API}/tasks/{t['id']}/deliveries")).json()
    by_id = {d["id"]: d for d in view["deliveries"]}
    assert by_id[d2]["is_current"] and by_id[d2]["acceptances"] == []
    assert {a["proposal_id"] for a in by_id[d1]["acceptances"]} == {p1["id"]}
    assert all(a["work_package_id"] == package["id"] for a in by_id[d1]["acceptances"])

    task = (await w.client.post(f"{API}/tasks/{t['id']}/recipient-acceptance", json=acc)).json()
    current = task["recipient_acceptance"]["acceptance_id"]
    r = await w.client.post(f"{API}/recipient-acceptances/{current}/withdraw", json={"reason": "ошибка записи"})
    assert r.json()["status"] == "withdrawn"
    assert (await w.client.get(f"{API}/tasks/{t['id']}")).json()["recipient_acceptance"] is None
    kept = (await w.client.get(f"{API}/tasks/{t['id']}/deliveries")).json()
    assert any(a["status"] == "withdrawn" for d in kept["deliveries"] for a in d["acceptances"])


async def test_evidence_is_shown_never_derived_from_done(w: World):
    await w.fact(w.req, "proj-pack", "requirement", "REQ-12", revision="v1", content={"status": "accepted"})
    t = await w.task()
    await w.basis(t["id"], ref(w.req, "proj-pack", "requirement", "REQ-12"), "v1", "normative")
    [basis] = (await w.client.get(f"{API}/tasks/{t['id']}/bases")).json()
    assert basis["evidence"] == []      # TaskTrack does not conclude compliance by itself
    await w.fact(w.req, "proj-pack", "evidence", "EV-1", revision="1", content={
        "kind": "compliance_conclusion", "outcome": "complies", "concluded_by": "req-owner",
        "subject": ref(w.req, "proj-pack", "requirement", "REQ-12", "v1"),
        "verification_plan": ref(w.req, "proj-pack", "verification_plan", "VP-3", "1"),
        "proof": {"commit": "a1b2c3d", "report": "https://ci/run/42"},
    })
    [basis] = (await w.client.get(f"{API}/tasks/{t['id']}/bases")).json()
    assert basis["evidence"][0]["claims"]["kind"] == "compliance_conclusion"
    assert json.dumps(basis["evidence"][0]["claims"]["subject"]["revision"]) == '"v1"'


async def test_mcp_claim_obeys_the_same_readiness(w: World, db_session: AsyncSession):
    from unittest.mock import MagicMock, patch

    import pytest
    from mcp.shared.exceptions import McpError

    from app.mcp.tools import work

    class _SessionFactory:   # the test's session, as in test_mcp_agent
        def __call__(self):
            return self

        async def __aenter__(self):
            return db_session

        async def __aexit__(self, *args):
            pass

    await w.link()
    await w.fact(w.req, "proj-pack", "verification_plan", "VP-9", revision="1", content={})
    t = await w.task()
    await w.basis(t["id"], ref(w.req, "proj-pack", "verification_plan", "VP-9"), "1", "input")
    await w.issue(t["id"])
    ctx = MagicMock()
    ctx.request_context.request.headers = {}
    with patch("app.mcp.utils.SessionLocal", _SessionFactory()), \
         patch("app.mcp.utils.get_user_for_key", lambda key: w.worker):
        ready = json.loads(await work.get_readiness(ctx, t["id"]))
        assert ready["mode"] == "portfolio" and not ready["ready"]
        with pytest.raises(McpError, match="TASK_NOT_READY"):
            await work.claim_task(ctx, t["id"], machine="console")
