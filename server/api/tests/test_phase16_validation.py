import pytest
from app.models import User, UserRole, ValidationItem
from app.auth.password import hash_password


@pytest.mark.asyncio
async def test_validation_queue_workflow(client, session):
    admin = User(email="val_admin@jurisai.law", password_hash=hash_password("password123"), role=UserRole.ADMIN)
    item = ValidationItem(
        item_type="ENTITY",
        status="PENDING",
        confidence=0.95,
        proposed_payload={"id": "art21", "name": "Article 21"},
        evidence_text="Right to life and personal liberty",
    )
    session.add_all([admin, item])
    await session.commit()
    await session.refresh(item)

    with client:
        client.post("/auth/login", json={"email": "val_admin@jurisai.law", "password": "password123"})
        
        # List validation queue
        res = client.get("/validation")
        assert res.status_code == 200
        assert res.json()["total"] >= 1

        # Approve item
        res = client.post(f"/validation/{item.id}/approve")
        assert res.status_code == 200
        assert res.json()["status"] == "APPROVED"


@pytest.mark.asyncio
async def test_validation_queue_reject(client, session):
    admin = User(email="val_admin2@jurisai.law", password_hash=hash_password("password123"), role=UserRole.ADMIN)
    item = ValidationItem(
        item_type="RELATIONSHIP",
        status="PENDING",
        confidence=0.70,
        proposed_payload={"source": "A", "target": "B"},
    )
    session.add_all([admin, item])
    await session.commit()
    await session.refresh(item)

    with client:
        client.post("/auth/login", json={"email": "val_admin2@jurisai.law", "password": "password123"})
        res = client.post(f"/validation/{item.id}/reject", json={"rejection_note": "Invalid triple relation"})
        assert res.status_code == 200
        assert res.json()["status"] == "REJECTED"
        assert res.json()["rejection_note"] == "Invalid triple relation"
