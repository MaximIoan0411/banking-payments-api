async def test_deposit_valid(client, auth_headers):
    response = await client.post(
        "/transactions/deposits",
        json={"amount": "100.00", "description": "test deposit"},
        headers=auth_headers,
    )
    assert response.status_code == 201
    data = response.json()
    assert data["status"] == "completed"
    assert data["type"] == "deposit"

    balance = await client.get("/accounts/me", headers=auth_headers)
    assert balance.json()["balance"] == "100.00"


async def test_deposit_negative_amount(client, auth_headers):
    response = await client.post(
        "/transactions/deposits",
        json={"amount": "-10.00", "description": "invalid"},
        headers=auth_headers,
    )
    assert response.status_code == 422