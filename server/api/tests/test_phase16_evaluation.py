import pytest
from app.models import User, UserRole
from app.auth.password import hash_password
from app.services.evaluation_runner import _load_dataset, run_evaluation_benchmark


def test_load_evaluation_dataset():
    questions, citations, entities, temporal = _load_dataset()
    assert len(questions) >= 9
    assert "eval_q01" in citations
    assert "eval_q01" in entities


@pytest.mark.asyncio
async def test_run_evaluation_benchmark(client, session):
    admin = User(email="eval_admin@jurisai.law", password_hash=hash_password("password123"), role=UserRole.ADMIN)
    session.add(admin)
    await session.commit()

    run_obj = await run_evaluation_benchmark(session, name="Test Benchmark Run", top_k=2, strategies=["vector_only"])
    assert run_obj.id is not None
    assert run_obj.name == "Test Benchmark Run"
    assert "vector_only" in run_obj.results

    with client:
        client.post("/auth/login", json={"email": "eval_admin@jurisai.law", "password": "password123"})
        res = client.get("/evaluation")
        assert res.status_code == 200
        data = res.json()
        assert data["total"] >= 1
