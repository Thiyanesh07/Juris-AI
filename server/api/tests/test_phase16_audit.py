import pytest
from app.models import User, UserRole
from app.auth.password import hash_password
from app.services.audit import log_audit_event


@pytest.mark.asyncio
async def test_audit_event_logging_and_retrieval(client, session):
    admin = User(email="audit_admin@jurisai.law", password_hash=hash_password("password123"), role=UserRole.ADMIN)
    session.add(admin)
    await session.commit()

    # Log audit event
    evt = await log_audit_event(
        session,
        category="SECURITY",
        action="LOGIN",
        result="SUCCESS",
        actor_id=admin.id,
        description="Admin login successful",
    )

    with client:
        client.post("/auth/login", json={"email": "audit_admin@jurisai.law", "password": "password123"})
        
        # Query audit log
        res = client.get("/audit?category=SECURITY")
        assert res.status_code == 200
        data = res.json()
        assert data["total"] >= 1
        assert any(item["id"] == str(evt.id) for item in data["items"])
