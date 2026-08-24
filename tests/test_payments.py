async def test_payment_valid(client, funded_sender, recipient):
    response = await client.post(
        "/transactions/payments",
        json={
            "amount": "100.00",
            "recipient_account_number": recipient["account_number"],
            "description": "test payment",
        },
        headers={**funded_sender["headers"], "Idempotency-Key": "key-valid-1"},
    )
    assert response.status_code == 201
    assert response.json()["status"] == "pending"

    balance = await client.get("/accounts/me", headers=funded_sender["headers"])
    assert balance.json()["balance"] == "400.00"


async def test_payment_recipient_not_found(client, funded_sender):
    response = await client.post(
        "/transactions/payments",
        json={
            "amount": "50.00",
            "recipient_account_number": "RO_INEXISTENT",
            "description": "test",
        },
        headers={**funded_sender["headers"], "Idempotency-Key": "key-notfound-1"},
    )
    assert response.status_code == 404


async def test_payment_to_own_account(client, funded_sender):
    response = await client.post(
        "/transactions/payments",
        json={
            "amount": "50.00",
            "recipient_account_number": funded_sender["account_number"],
            "description": "test",
        },
        headers={**funded_sender["headers"], "Idempotency-Key": "key-self-1"},
    )
    assert response.status_code == 400


async def test_payment_insufficient_balance(client, funded_sender, recipient):
    response = await client.post(
        "/transactions/payments",
        json={
            "amount": "999999.00",
            "recipient_account_number": recipient["account_number"],
            "description": "too much",
        },
        headers={**funded_sender["headers"], "Idempotency-Key": "key-insufficient-1"},
    )
    assert response.status_code == 201
    assert response.json()["status"] == "failed"

    balance = await client.get("/accounts/me", headers=funded_sender["headers"])
    assert balance.json()["balance"] == "500.00"


async def test_payment_idempotent_retry_same_payload(client, funded_sender, recipient):
    payload = {
        "amount": "100.00",
        "recipient_account_number": recipient["account_number"],
        "description": "retry test",
    }
    headers = {**funded_sender["headers"], "Idempotency-Key": "key-retry-1"}

    first = await client.post("/transactions/payments", json=payload, headers=headers)
    second = await client.post("/transactions/payments", json=payload, headers=headers)

    assert first.status_code == 201
    assert second.status_code == 201
    assert first.json()["id"] == second.json()["id"]

    balance = await client.get("/accounts/me", headers=funded_sender["headers"])
    assert balance.json()["balance"] == "400.00" 


async def test_payment_idempotency_conflict_different_payload(client, funded_sender, recipient):
    headers = {**funded_sender["headers"], "Idempotency-Key": "key-conflict-1"}

    await client.post(
        "/transactions/payments",
        json={"amount": "50.00", "recipient_account_number": recipient["account_number"], "description": "a"},
        headers=headers,
    )
    response = await client.post(
        "/transactions/payments",
        json={"amount": "51.00", "recipient_account_number": recipient["account_number"], "description": "a"},
        headers=headers,
    )
    assert response.status_code == 409


async def test_payment_missing_idempotency_key(client, funded_sender, recipient):
    response = await client.post(
        "/transactions/payments",
        json={"amount": "50.00", "recipient_account_number": recipient["account_number"], "description": "x"},
        headers=funded_sender["headers"],
    )
    assert response.status_code == 422