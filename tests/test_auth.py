from sqlalchemy import select

from app.models.user import User


async def test_register_success(client):
    response = await client.post("/auth/register", json={
        "email": "newuser@test.com",
        "password": "parola123",
        "full_name": "New User",
    })
    assert response.status_code == 201
    data = response.json()
    assert data["email"] == "newuser@test.com"
    assert data["is_admin"] is False


async def test_register_cannot_self_promote_to_admin(client, db_session):
    response = await client.post("/auth/register", json={
        "email": "sneaky@test.com",
        "password": "parola123",
        "full_name": "Sneaky User",
        "is_admin": True, 
    })
    assert response.status_code == 201
    assert response.json()["is_admin"] is False

    result = await db_session.execute(select(User).where(User.email == "sneaky@test.com"))
    user = result.scalar_one()
    assert user.is_admin is False


async def test_login_success(client):
    await client.post("/auth/register", json={
        "email": "loginuser@test.com",
        "password": "parola123",
        "full_name": "Login User",
    })
    response = await client.post("/auth/login", data={
        "username": "loginuser@test.com",
        "password": "parola123",
    })
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert "refresh_token" in data


async def test_login_wrong_password(client):
    await client.post("/auth/register", json={
        "email": "wrongpass@test.com",
        "password": "parola123",
        "full_name": "Wrong Pass",
    })
    response = await client.post("/auth/login", data={
        "username": "wrongpass@test.com",
        "password": "gresita",
    })
    assert response.status_code == 401