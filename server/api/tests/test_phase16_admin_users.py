import pytest
from app.models import User, UserRole
from app.auth.password import hash_password


@pytest.mark.asyncio
async def test_get_my_profile(client, session):
    user = User(email="profile_user@jurisai.law", password_hash=hash_password("password123"), role=UserRole.USER)
    session.add(user)
    await session.commit()

    # Authenticated session
    with client:
        # Simulate session login
        client.post("/auth/login", json={"email": "profile_user@jurisai.law", "password": "password123"})
        res = client.get("/users/me")
        assert res.status_code == 200
        data = res.json()
        assert data["email"] == "profile_user@jurisai.law"
        assert data["role"] == "user"


@pytest.mark.asyncio
async def test_admin_list_users_rbac(client, session):
    normal_user = User(email="user1@jurisai.law", password_hash=hash_password("password123"), role=UserRole.USER)
    admin_user = User(email="admin1@jurisai.law", password_hash=hash_password("password123"), role=UserRole.ADMIN)
    session.add_all([normal_user, admin_user])
    await session.commit()

    # User cannot access /admin/users
    with client:
        client.post("/auth/login", json={"email": "user1@jurisai.law", "password": "password123"})
        res = client.get("/admin/users")
        assert res.status_code == 403

    # Admin can access /admin/users
    with client:
        client.post("/auth/login", json={"email": "admin1@jurisai.law", "password": "password123"})
        res = client.get("/admin/users")
        assert res.status_code == 200
        data = res.json()
        assert data["total"] >= 2


@pytest.mark.asyncio
async def test_super_admin_provision_admin(client, session):
    super_admin = User(email="superadmin@jurisai.law", password_hash=hash_password("password123"), role=UserRole.SUPER_ADMIN)
    session.add(super_admin)
    await session.commit()

    with client:
        client.post("/auth/login", json={"email": "superadmin@jurisai.law", "password": "password123"})
        res = client.post(
            "/admin/admins",
            json={
                "email": "new_admin@jurisai.law",
                "name": "New Admin",
                "password": "SecurePassword123!",
                "role": "admin",
            },
        )
        assert res.status_code == 201
        data = res.json()
        assert data["email"] == "new_admin@jurisai.law"
        assert data["role"] == "admin"
