
def create_test_customer(client):
    response = client.post(
        "/api/customers",
        json={
            "name": "Ticket Test Customer",
            "email": "ticket-test@example.com",
            "password": "DemoPassword123!",
        },
    )
    assert response.status_code == 201
    return response.json()["id"]


def test_create_and_list_support_tickets(client):
    customer_id = create_test_customer(client)

    create_response = client.post(
        "/api/support-tickets",
        json={
            "customer_id": customer_id,
            "subject": "Delivery enquiry",
            "description": "Please provide an update on my delivery.",
        },
    )

    assert create_response.status_code == 201
    ticket = create_response.json()
    assert ticket["status"] == "open"

    list_response = client.get(
        "/api/support-tickets",
        params={"customer_id": customer_id},
    )

    assert list_response.status_code == 200
    tickets = list_response.json()
    assert len(tickets) == 1
    assert tickets[0]["id"] == ticket["id"]


def test_ticket_for_missing_customer_fails(client):
    response = client.post(
        "/api/support-tickets",
        json={
            "customer_id": 99999,
            "subject": "Delivery enquiry",
            "description": "Please provide an update on my delivery.",
        },
    )

    assert response.status_code == 404
