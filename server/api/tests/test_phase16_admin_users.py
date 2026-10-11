import uuid
import pytest
from sqlalchemy import select

from app.models import SystemEvent, User, UserRole
from app.auth.password import hash_password


@pytest.mark.asyncio
async def test_get_my_profile(client, session):
    user = User(email="profile_user@jurisai.law", password_hash=hash_password("password123"), role=UserRole.USER)
    session.add(user)
    await session.commit()

    # Authenticated session
    client.cookies.clear()
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
    client.cookies.clear()
    client.post("/auth/login", json={"email": "user1@jurisai.law", "password": "password123"})
    res = client.get("/admin/users")
    assert res.status_code == 403

    # Admin can access /admin/users
    client.cookies.clear()
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

    client.cookies.clear()
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


@pytest.mark.asyncio
async def test_admin_create_user_success_with_password(client, session):
    admin = User(email="admin_creator@jurisai.law", password_hash=hash_password("password123"), role=UserRole.ADMIN)
    session.add(admin)
    await session.commit()

    client.cookies.clear()
    client.post("/auth/login", json={"email": "admin_creator@jurisai.law", "password": "password123"})
    res = client.post(
        "/admin/users",
        json={
            "email": "researcher_alpha@jurisai.law",
            "name": "Alpha Researcher",
            "password": "ValidPassword123!",
        },
    )
    assert res.status_code == 201
    data = res.json()
    assert data["email"] == "researcher_alpha@jurisai.law"
    assert data["name"] == "Alpha Researcher"
    assert data["role"] == "user"
    assert data["is_active"] is True
    assert "id" in data

    # Verify created user can log in with password
    client.cookies.clear()
    login_res = client.post(
        "/auth/login",
        json={"email": "researcher_alpha@jurisai.law", "password": "ValidPassword123!"},
    )
    assert login_res.status_code == 200
    assert login_res.json()["email"] == "researcher_alpha@jurisai.law"


@pytest.mark.asyncio
async def test_admin_create_user_passwordless(client, session):
    admin = User(email="admin_oauth@jurisai.law", password_hash=hash_password("password123"), role=UserRole.ADMIN)
    session.add(admin)
    await session.commit()

    client.cookies.clear()
    client.post("/auth/login", json={"email": "admin_oauth@jurisai.law", "password": "password123"})
    res = client.post(
        "/admin/users",
        json={
            "email": "oauth_user@jurisai.law",
            "name": "OAuth User",
        },
    )
    assert res.status_code == 201
    data = res.json()
    assert data["email"] == "oauth_user@jurisai.law"
    assert data["role"] == "user"
    assert data["is_active"] is True

    # Direct database check: password_hash is None
    created_id = uuid.UUID(data["id"])
    created_db_user = await session.get(User, created_id)
    assert created_db_user is not None
    assert created_db_user.password_hash is None


@pytest.mark.asyncio
async def test_admin_create_user_validation_failures(client, session):
    admin = User(email="admin_val@jurisai.law", password_hash=hash_password("password123"), role=UserRole.ADMIN)
    session.add(admin)
    await session.commit()

    client.cookies.clear()
    client.post("/auth/login", json={"email": "admin_val@jurisai.law", "password": "password123"})

    # Invalid email format
    res_bad_email = client.post(
        "/admin/users",
        json={"email": "not-a-valid-email", "name": "Bad Email"},
    )
    assert res_bad_email.status_code == 422

    # Password too short (< 8 chars)
    res_short_pw = client.post(
        "/admin/users",
        json={"email": "short_pw@jurisai.law", "name": "Short Pw", "password": "short"},
    )
    assert res_short_pw.status_code == 422


@pytest.mark.asyncio
async def test_admin_create_user_duplicate_email_conflict(client, session):
    admin = User(email="admin_dup@jurisai.law", password_hash=hash_password("password123"), role=UserRole.ADMIN)
    existing_user = User(email="existing@jurisai.law", password_hash=hash_password("password123"), role=UserRole.USER)
    session.add_all([admin, existing_user])
    await session.commit()

    client.cookies.clear()
    client.post("/auth/login", json={"email": "admin_dup@jurisai.law", "password": "password123"})
    res = client.post(
        "/admin/users",
        json={"email": "existing@jurisai.law", "name": "Duplicate User", "password": "ValidPassword123!"},
    )
    assert res.status_code == 409
    assert "already registered" in res.json()["detail"].lower()


@pytest.mark.asyncio
async def test_admin_create_user_rbac_and_unauthenticated(client, session):
    user = User(email="standard_user@jurisai.law", password_hash=hash_password("password123"), role=UserRole.USER)
    session.add(user)
    await session.commit()

    # Unauthenticated -> 401
    client.cookies.clear()
    res_unauth = client.post(
        "/admin/users",
        json={"email": "new_attempt@jurisai.law", "password": "ValidPassword123!"},
    )
    assert res_unauth.status_code == 401

    # Standard user -> 403 Forbidden
    client.cookies.clear()
    client.post("/auth/login", json={"email": "standard_user@jurisai.law", "password": "password123"})
    res_forbidden = client.post(
        "/admin/users",
        json={"email": "new_attempt@jurisai.law", "password": "ValidPassword123!"},
    )
    assert res_forbidden.status_code == 403


@pytest.mark.asyncio
async def test_admin_create_user_ignores_caller_supplied_privileged_role(client, session):
    admin = User(email="admin_role_check@jurisai.law", password_hash=hash_password("password123"), role=UserRole.ADMIN)
    session.add(admin)
    await session.commit()

    client.cookies.clear()
    client.post("/auth/login", json={"email": "admin_role_check@jurisai.law", "password": "password123"})
    res = client.post(
        "/admin/users",
        json={
            "email": "sneaky_role@jurisai.law",
            "name": "Sneaky Role Attempt",
            "password": "ValidPassword123!",
            "role": "super_admin",
        },
    )
    assert res.status_code == 201
    data = res.json()
    assert data["role"] == "user"  # Strictly enforced server-side


@pytest.mark.asyncio
async def test_admin_deactivate_user_success(client, session):
    admin = User(email="admin_deactivator@jurisai.law", password_hash=hash_password("password123"), role=UserRole.ADMIN)
    target = User(email="target_deactivate@jurisai.law", password_hash=hash_password("password123"), role=UserRole.USER, is_active=True)
    session.add_all([admin, target])
    await session.commit()

    client.cookies.clear()
    client.post("/auth/login", json={"email": "admin_deactivator@jurisai.law", "password": "password123"})
    res = client.delete(f"/admin/users/{target.id}")
    assert res.status_code == 200
    data = res.json()
    assert data["id"] == str(target.id)
    assert data["is_active"] is False

    # Verify soft deactivation: record is NOT deleted from DB
    await session.refresh(target)
    assert target is not None
    assert target.is_active is False

    # Deactivated user cannot log in
    client.cookies.clear()
    login_res = client.post(
        "/auth/login",
        json={"email": "target_deactivate@jurisai.law", "password": "password123"},
    )
    assert login_res.status_code == 403
    assert "disabled" in login_res.json()["detail"].lower()


@pytest.mark.asyncio
async def test_admin_deactivate_user_nonexistent_id(client, session):
    admin = User(email="admin_nonexistent@jurisai.law", password_hash=hash_password("password123"), role=UserRole.ADMIN)
    session.add(admin)
    await session.commit()

    fake_id = uuid.uuid4()
    client.cookies.clear()
    client.post("/auth/login", json={"email": "admin_nonexistent@jurisai.law", "password": "password123"})
    res = client.delete(f"/admin/users/{fake_id}")
    assert res.status_code == 404
    assert "not found" in res.json()["detail"].lower()


@pytest.mark.asyncio
async def test_admin_deactivate_super_admin_protection(client, session):
    admin = User(email="ordinary_admin@jurisai.law", password_hash=hash_password("password123"), role=UserRole.ADMIN)
    super_admin = User(email="root_super_admin@jurisai.law", password_hash=hash_password("password123"), role=UserRole.SUPER_ADMIN)
    session.add_all([admin, super_admin])
    await session.commit()

    # Ordinary admin attempting to deactivate super-admin -> 403 Forbidden
    client.cookies.clear()
    client.post("/auth/login", json={"email": "ordinary_admin@jurisai.law", "password": "password123"})
    res_admin_attack = client.delete(f"/admin/users/{super_admin.id}")
    assert res_admin_attack.status_code == 403

    # Super-admin attempting to deactivate super-admin -> 400 Bad Request
    client.cookies.clear()
    client.post("/auth/login", json={"email": "root_super_admin@jurisai.law", "password": "password123"})
    res_super_attack = client.delete(f"/admin/users/{super_admin.id}")
    assert res_super_attack.status_code == 400
    assert "cannot be deactivated" in res_super_attack.json()["detail"].lower()

    # Super-admin remains active
    refreshed_super = await session.get(User, super_admin.id)
    assert refreshed_super.is_active is True


@pytest.mark.asyncio
async def test_admin_audit_logs_recorded(client, session):
    admin = User(email="audited_admin@jurisai.law", password_hash=hash_password("password123"), role=UserRole.ADMIN)
    session.add(admin)
    await session.commit()

    client.cookies.clear()
    client.post("/auth/login", json={"email": "audited_admin@jurisai.law", "password": "password123"})

    # Provision user
    create_res = client.post(
        "/admin/users",
        json={"email": "audited_user@jurisai.law", "name": "Audited User", "password": "ValidPassword123!"},
    )
    assert create_res.status_code == 201
    created_id = create_res.json()["id"]

    # Deactivate user
    delete_res = client.delete(f"/admin/users/{created_id}")
    assert delete_res.status_code == 200

    # Verify audit logs in database
    events = (
        await session.scalars(
            select(SystemEvent).where(SystemEvent.actor_id == admin.id).order_by(SystemEvent.created_at.asc())
        )
    ).all()

    event_types = [e.event_type for e in events]
    assert "USER_MANAGEMENT_CREATE" in event_types
    assert "USER_MANAGEMENT_DEACTIVATE" in event_types

    deactivate_event = next(e for e in events if e.event_type == "USER_MANAGEMENT_DEACTIVATE")
    assert deactivate_event.event_metadata["before_state"]["is_active"] is True
    assert deactivate_event.event_metadata["after_state"]["is_active"] is False


@pytest.mark.asyncio
async def test_admin_self_deactivation_rejected(client, session):
    admin = User(email="self_deactivate_admin@jurisai.law", password_hash=hash_password("password123"), role=UserRole.ADMIN)
    session.add(admin)
    await session.commit()

    client.cookies.clear()
    client.post("/auth/login", json={"email": "self_deactivate_admin@jurisai.law", "password": "password123"})
    # 1. DELETE /admin/users/{own_id}
    res_del = client.delete(f"/admin/users/{admin.id}")
    assert res_del.status_code == 400
    assert "cannot deactivate their own account" in res_del.json()["detail"].lower()

    # 2. PUT /admin/users/{own_id} with is_active=False
    res_put = client.put(f"/admin/users/{admin.id}", json={"is_active": False})
    assert res_put.status_code == 400
    assert "cannot deactivate their own account" in res_put.json()["detail"].lower()

    # Admin remains active in database
    await session.refresh(admin)
    assert admin.is_active is True
