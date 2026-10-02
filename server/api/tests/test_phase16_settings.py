import pytest
from app.models import User, UserRole
from app.auth.password import hash_password


@pytest.mark.asyncio
async def test_settings_retrieval_and_update(client, session):
    admin = User(email="settings_admin@jurisai.law", password_hash=hash_password("password123"), role=UserRole.ADMIN)
    session.add(admin)
    await session.commit()

    with client:
        client.post("/auth/login", json={"email": "settings_admin@jurisai.law", "password": "password123"})
        
        # Get all settings (secrets masked)
        res = client.get("/settings")
        assert res.status_code == 200
        sections = res.json()["sections"]
        assert "AI_LLM" in sections
        assert sections["AI_LLM"]["api_key"] == "********"

        # Update general settings
        res = client.put(
            "/settings/GENERAL",
            json={"config": {"platform_name": "Juris AI Production", "max_query_length": 2000}},
        )
        assert res.status_code == 200
        assert res.json()["config"]["platform_name"] == "Juris AI Production"
