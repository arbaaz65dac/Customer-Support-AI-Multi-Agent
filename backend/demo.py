"""Run a small authenticated API demo for the support assistant.

Set DEMO_EMAIL and DEMO_PASSWORD in the environment, start FastAPI, and run:
    python demo.py
"""

import json
import os
import sys
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


API_BASE_URL = os.getenv("API_BASE_URL", "http://127.0.0.1:8000").rstrip("/")


class DemoRequestError(RuntimeError):
    pass


def api_request(
    path: str,
    *,
    method: str = "GET",
    body: dict[str, Any] | None = None,
    token: str | None = None,
) -> Any:
    headers = {"Accept": "application/json"}
    data = None
    if body is not None:
        headers["Content-Type"] = "application/json"
        data = json.dumps(body).encode("utf-8")
    if token:
        headers["Authorization"] = f"Bearer {token}"

    request = Request(
        f"{API_BASE_URL}{path}",
        data=data,
        headers=headers,
        method=method,
    )
    try:
        with urlopen(request, timeout=60) as response:
            response_data = response.read()
    except HTTPError as exc:
        try:
            error_body = json.loads(exc.read().decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError):
            error_body = {}
        detail = error_body.get("detail", "The API request failed.")
        raise DemoRequestError(
            f"{method} {path} returned HTTP {exc.code}: {detail}"
        ) from exc
    except (TimeoutError, URLError) as exc:
        raise DemoRequestError(
            f"Could not reach {API_BASE_URL}: {exc}"
        ) from exc

    if not response_data:
        return None
    try:
        return json.loads(response_data.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise DemoRequestError(
            f"{method} {path} returned invalid JSON."
        ) from exc


def print_result(title: str, result: dict[str, Any]) -> None:
    print(f"\n--- {title} ---")
    print(f"Assistant: {result.get('answer', '(no answer)')}")
    for product in result.get("products", []):
        print(
            "Product card: "
            f"{product.get('name')} | ₹{product.get('price')} | "
            f"stock {product.get('stock')}"
        )
    for citation in result.get("citations", []):
        print(
            "Citation: "
            f"{citation.get('source')} v{citation.get('version')} "
            f"(effective {citation.get('effective_date')})"
        )


def main() -> int:
    email = os.getenv("DEMO_EMAIL")
    password = os.getenv("DEMO_PASSWORD")
    if not email or not password:
        print(
            "Set DEMO_EMAIL and DEMO_PASSWORD to a seeded customer account.",
            file=sys.stderr,
        )
        return 2

    try:
        login = api_request(
            "/api/auth/login",
            method="POST",
            body={"email": email, "password": password},
        )
        token = login.get("access_token")
        if not token:
            raise DemoRequestError("Login response did not contain a token.")

        print(f"Connected to {API_BASE_URL} as {email}")

        scenarios = [
            (
                "Product query",
                "Find wireless headphones under ₹3000",
            ),
            (
                "Policy question",
                "What is the return window?",
            ),
            (
                "Mixed policy and product query",
                "Can I return my order? Also show wireless headphones "
                "under ₹3000",
            ),
            (
                "Out-of-domain refusal",
                "Who is Rohit Sharma?",
            ),
        ]
        for title, question in scenarios:
            result = api_request(
                "/api/support/ask",
                method="POST",
                body={"question": question},
                token=token,
            )
            print_result(title, result)

        ticket = api_request(
            "/api/support-tickets",
            method="POST",
            body={
                "subject": "Demo delivery follow-up",
                "description": (
                    "Please share an update about my recent delivery."
                ),
            },
            token=token,
        )
        print(
            f"\nCreated support ticket #{ticket['id']}: "
            f"{ticket['status']}"
        )

        print("\n--- Tracked return/refund request ---")
        existing_requests = api_request(
            "/api/refund-requests",
            token=token,
        )
        pending_requests = [
            item
            for item in existing_requests
            if item.get("status") == "pending"
        ]
        requested_order_id = os.getenv("DEMO_ORDER_ID")
        if requested_order_id:
            try:
                order_id = int(requested_order_id)
            except ValueError as exc:
                raise DemoRequestError(
                    "DEMO_ORDER_ID must be a positive integer."
                ) from exc
            if order_id <= 0:
                raise DemoRequestError("DEMO_ORDER_ID must be positive.")
        else:
            orders = api_request("/api/orders", token=token)
            delivered_orders = [
                order for order in orders if order.get("status") == "delivered"
            ]
            if not delivered_orders:
                raise DemoRequestError(
                    "No delivered order is available for the refund demo. "
                    "Seed demo orders or set DEMO_ORDER_ID to an owned "
                    "eligible order."
                )
            order_id = delivered_orders[0]["id"]

        existing = next(
            (
                item for item in pending_requests
                if item.get("order_id") == order_id
            ),
            None,
        )
        if existing:
            request_result = existing
            print("A pending request already exists for the selected order.")
        else:
            request_result = api_request(
                "/api/refund-requests",
                method="POST",
                body={
                    "order_id": order_id,
                    "request_type": "return",
                    "reason": (
                        "Demo request: the item does not meet expectations; "
                        "please review eligibility."
                    ),
                },
                token=token,
            )
        print(
            f"Request #{request_result['id']} for order "
            f"#{request_result['order_id']}: "
            f"{request_result['status']} (admin review; no payment executed)"
        )
        return 0
    except DemoRequestError as exc:
        print(f"Demo stopped: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
