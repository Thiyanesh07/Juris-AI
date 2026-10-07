"""Integration tests for the /evaluation API (Phase 7C.1)."""

from __future__ import annotations

from uuid import uuid4

from fastapi.testclient import TestClient
from sqlalchemy import delete
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import get_current_user, require_admin
from app.main import app
from app.models import EvaluationRun, User
from app.models.enums import UserRole


def _make_user(email: str = "user@test.com", role: UserRole = UserRole.USER) -> User:
    return User(id=uuid4(), email=email, name="Test", role=role)


def _override_user(user: User) -> None:
    app.dependency_overrides[get_current_user] = lambda: user


def _override_admin(user: User) -> None:
    app.dependency_overrides[get_current_user] = lambda: user
    app.dependency_overrides[require_admin] = lambda: user


def _clear_overrides() -> None:
    app.dependency_overrides.pop(get_current_user, None)
    app.dependency_overrides.pop(require_admin, None)


async def test_admin_list_empty(client: TestClient, session: AsyncSession) -> None:
    await session.execute(delete(EvaluationRun))
    await session.commit()

    admin = _make_user(role=UserRole.ADMIN)
    _override_admin(admin)
    try:
        resp = client.get("/evaluation")
        assert resp.status_code == 200
        data = resp.json()
        assert data["items"] == []
        assert data["total"] == 0
        assert data["page"] == 1
        assert data["page_size"] == 20
    finally:
        _clear_overrides()


async def test_admin_can_list_evaluation_runs(client: TestClient, session: AsyncSession) -> None:
    session.add_all(
        [
            EvaluationRun(name="run-a", configuration={"k": 5}, results={"score": 0.1}),
            EvaluationRun(name="run-b", configuration={"k": 10}, results={"score": 0.2}),
        ]
    )
    await session.commit()

    admin = _make_user(role=UserRole.ADMIN)
    _override_admin(admin)
    try:
        resp = client.get("/evaluation")
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] >= 2
        names = {item["name"] for item in data["items"]}
        assert {"run-a", "run-b"}.issubset(names)
    finally:
        _clear_overrides()


async def test_admin_can_get_evaluation_run(client: TestClient, session: AsyncSession) -> None:
    configuration = {"retriever": "hybrid", "k": 10, "hops": 2}
    results = {"recall_at_5": 0.42}
    run = EvaluationRun(name="baseline", configuration=configuration, results=results)
    session.add(run)
    await session.commit()
    await session.refresh(run)

    admin = _make_user(role=UserRole.ADMIN)
    _override_admin(admin)
    try:
        resp = client.get(f"/evaluation/{run.id}")
        assert resp.status_code == 200
        body = resp.json()
        assert body["id"] == str(run.id)
        assert body["name"] == "baseline"
        assert body["configuration"] == configuration
        assert body["results"] == results
        assert "created_at" in body
    finally:
        _clear_overrides()


def test_get_evaluation_run_not_found(client: TestClient) -> None:
    admin = _make_user(role=UserRole.ADMIN)
    _override_admin(admin)
    try:
        resp = client.get(f"/evaluation/{uuid4()}")
        assert resp.status_code == 404
        assert resp.json()["detail"] == "Evaluation run not found"
    finally:
        _clear_overrides()


def test_evaluation_requires_auth(client: TestClient) -> None:
    _clear_overrides()
    resp = client.get("/evaluation")
    assert resp.status_code == 401


def test_evaluation_requires_admin(client: TestClient) -> None:
    user = _make_user(role=UserRole.USER)
    _override_user(user)
    try:
        resp = client.get("/evaluation")
        assert resp.status_code == 403
        resp_detail = client.get(f"/evaluation/{uuid4()}")
        assert resp_detail.status_code == 403
    finally:
        _clear_overrides()


async def test_evaluation_jsonb_roundtrip_via_api(
    client: TestClient, session: AsyncSession
) -> None:
    configuration = {"retriever": "dense", "nested": {"alpha": 0.5}, "tags": ["a", "b"]}
    results = {"metrics": {"mrr": 0.33}, "ok": True}
    run = EvaluationRun(name="jsonb-api", configuration=configuration, results=results)
    session.add(run)
    await session.commit()
    await session.refresh(run)

    admin = _make_user(role=UserRole.ADMIN)
    _override_admin(admin)
    try:
        list_resp = client.get("/evaluation")
        assert list_resp.status_code == 200
        listed = next(i for i in list_resp.json()["items"] if i["id"] == str(run.id))
        assert listed["configuration"] == configuration
        assert listed["results"] == results

        detail_resp = client.get(f"/evaluation/{run.id}")
        assert detail_resp.status_code == 200
        detail = detail_resp.json()
        assert detail["configuration"] == configuration
        assert detail["results"] == results
    finally:
        _clear_overrides()


async def test_evaluation_list_pagination(client: TestClient, session: AsyncSession) -> None:
    await session.execute(delete(EvaluationRun))
    for index in range(7):
        session.add(EvaluationRun(name=f"run-{index}"))
    await session.commit()

    admin = _make_user(role=UserRole.ADMIN)
    _override_admin(admin)
    try:
        page1 = client.get("/evaluation?page=1&page_size=3")
        assert page1.status_code == 200
        data1 = page1.json()
        assert data1["total"] == 7
        assert data1["page"] == 1
        assert data1["page_size"] == 3
        assert len(data1["items"]) == 3

        page3 = client.get("/evaluation?page=3&page_size=3")
        assert page3.status_code == 200
        data3 = page3.json()
        assert len(data3["items"]) == 1
    finally:
        _clear_overrides()
