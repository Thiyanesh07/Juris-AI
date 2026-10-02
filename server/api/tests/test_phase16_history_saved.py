import pytest
from app.models import User, UserRole, ResearchSession, ResearchQuery, ResearchAnswer, ValidationStatus
from app.auth.password import hash_password


@pytest.mark.asyncio
async def test_user_history_and_saved_research_ownership(client, session):
    user_a = User(email="hist_a@jurisai.law", password_hash=hash_password("password123"), role=UserRole.USER)
    user_b = User(email="hist_b@jurisai.law", password_hash=hash_password("password123"), role=UserRole.USER)
    session.add_all([user_a, user_b])
    await session.commit()

    # Session for user_a
    sess_a = ResearchSession(user_id=user_a.id, title="User A Research Session")
    session.add(sess_a)
    await session.commit()
    await session.refresh(sess_a)

    q = ResearchQuery(session_id=sess_a.id, question="What does Article 21 protect?")
    session.add(q)
    await session.commit()
    await session.refresh(q)

    ans = ResearchAnswer(query_id=q.id, answer="Article 21 protects life and personal liberty.", validation_status=ValidationStatus.VALIDATED)
    session.add(ans)
    await session.commit()

    # User A accesses own history
    with client:
        client.post("/auth/login", json={"email": "hist_a@jurisai.law", "password": "password123"})
        res = client.get("/research/history")
        assert res.status_code == 200
        data = res.json()
        assert data["total"] == 1
        assert data["items"][0]["title"] == "User A Research Session"

        # User A bookmarks session
        save_res = client.post("/research/saved", json={"session_id": str(sess_a.id)})
        assert save_res.status_code == 201
        saved_id = save_res.json()["id"]

        # List saved research
        list_saved = client.get("/research/saved")
        assert list_saved.status_code == 200
        assert len(list_saved.json()) == 1

    # User B tries to access User A's history or saved research
    with client:
        client.post("/auth/login", json={"email": "hist_b@jurisai.law", "password": "password123"})
        res_history = client.get(f"/research/history/{sess_a.id}")
        assert res_history.status_code == 404

        res_saved = client.get(f"/research/saved/{saved_id}")
        assert res_saved.status_code == 404
