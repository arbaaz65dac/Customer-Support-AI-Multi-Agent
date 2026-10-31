from demo import main


def test_demo_runs_all_support_scenarios_and_tracks_refund(
    monkeypatch,
    capsys,
):
    monkeypatch.setenv("DEMO_EMAIL", "customer@example.in")
    monkeypatch.setenv("DEMO_PASSWORD", "test-password")
    calls = []

    def fake_api_request(path, *, method="GET", body=None, token=None):
        calls.append((path, method, body, token))
        if path == "/api/auth/login":
            return {"access_token": "demo-token"}
        if path == "/api/support/ask":
            return {
                "answer": "Demo response.",
                "citations": [],
                "products": [],
            }
        if path == "/api/support-tickets":
            return {"id": 18, "status": "open"}
        if path == "/api/refund-requests":
            if method == "GET":
                return []
            return {
                "id": 61,
                "order_id": 25,
                "status": "pending",
            }
        if path == "/api/orders":
            return [{"id": 25, "status": "delivered"}]
        raise AssertionError(f"Unexpected API path: {path}")

    monkeypatch.setattr("demo.api_request", fake_api_request)

    assert main() == 0

    output = capsys.readouterr().out
    assert "--- Product query ---" in output
    assert "--- Policy question ---" in output
    assert "--- Mixed policy and product query ---" in output
    assert "--- Out-of-domain refusal ---" in output
    assert "Created support ticket #18: open" in output
    assert "Request #61 for order #25: pending" in output
    assistant_calls = [
        call for call in calls if call[0] == "/api/support/ask"
    ]
    assert len(assistant_calls) == 4
    assert any(call[0] == "/api/support-tickets" for call in calls)
    assert all(call[3] == "demo-token" for call in assistant_calls)


def test_demo_does_not_duplicate_existing_pending_request(
    monkeypatch,
    capsys,
):
    monkeypatch.setenv("DEMO_EMAIL", "customer@example.in")
    monkeypatch.setenv("DEMO_PASSWORD", "test-password")

    def fake_api_request(path, *, method="GET", body=None, token=None):
        if path == "/api/auth/login":
            return {"access_token": "demo-token"}
        if path == "/api/support/ask":
            return {"answer": "Demo response.", "citations": [], "products": []}
        if path == "/api/support-tickets":
            return {"id": 19, "status": "open"}
        if path == "/api/refund-requests":
            assert method == "GET"
            return [
                {
                    "id": 61,
                    "order_id": 25,
                    "status": "pending",
                }
            ]
        if path == "/api/orders":
            return [{"id": 25, "status": "delivered"}]
        raise AssertionError(f"Unexpected API path: {path}")

    monkeypatch.setattr("demo.api_request", fake_api_request)

    assert main() == 0
    assert "A pending request already exists" in capsys.readouterr().out
