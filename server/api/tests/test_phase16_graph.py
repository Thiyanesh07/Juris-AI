import pytest
from app.models import User, UserRole
from app.auth.password import hash_password


@pytest.mark.asyncio
async def test_admin_graph_api_depth_bounding(client, session):
    admin = User(email="graph_admin@jurisai.law", password_hash=hash_password("password123"), role=UserRole.ADMIN)
    session.add(admin)
    await session.commit()

    with client:
        client.post("/auth/login", json={"email": "graph_admin@jurisai.law", "password": "password123"})
        
        # Test graph search
        res = client.get("/graph/search?query=Article")
        assert res.status_code == 200
        assert "nodes" in res.json()

        # Test neighbor depth limit bounding (max 5)
        res_valid = client.get("/graph/neighbors/article:constitution_of_india:21?depth=5")
        assert res_valid.status_code == 200
        assert res_valid.json()["depth"] == 5

        # Test depth exceeding max 5 is rejected by request validation
        res_invalid = client.get("/graph/neighbors/article:constitution_of_india:21?depth=10")
        assert res_invalid.status_code == 422
