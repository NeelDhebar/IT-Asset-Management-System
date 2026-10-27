"""Integration Tests for FastAPI REST Endpoints and Security."""

import pytest
from fastapi.testclient import TestClient
from app.main import app, seed_initial_demo_users
from app.database.connection import DatabaseConnectionManager

client = TestClient(app)


@pytest.fixture(scope="module", autouse=True)
def setup_database():
    """Ensure database tables and demo seed users are created before API tests run."""
    db_mgr = DatabaseConnectionManager()
    db_mgr.create_tables()
    seed_initial_demo_users()


def test_health_check_endpoint():
    """Verify /health returns 200 OK with correct schema."""
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert "app_env" in data


def test_auth_login_success():
    """Verify admin login succeeds and returns valid JWT token."""
    response = client.post(
        "/api/v1/auth/login",
        json={"email": "admin@company.com", "password": "Admin@1234"},
    )
    assert response.status_code == 200
    json_data = response.json()
    assert json_data["success"] is True
    assert "access_token" in json_data["data"]
    assert json_data["data"]["user"]["role"] == "ADMIN"


def test_auth_login_invalid_credentials():
    """Verify invalid password returns 401 Unauthorized."""
    response = client.post(
        "/api/v1/auth/login",
        json={"email": "admin@company.com", "password": "WrongPassword!"},
    )
    assert response.status_code == 401


def test_prehashed_client_login():
    """Verify login with SHA-256 client pre-hashed password payload succeeds."""
    import hashlib
    raw_pwd = "Admin@1234"
    prehashed = hashlib.sha256(raw_pwd.encode("utf-8")).hexdigest()
    res = client.post("/api/v1/auth/login", json={"email": "admin@company.com", "password": prehashed})
    assert res.status_code == 200
    assert "access_token" in res.json()["data"]


def get_auth_token(email: str = "admin@company.com", password: str = "Admin@1234") -> str:
    """Helper to retrieve JWT token for authenticated requests."""
    res = client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": password},
    )
    return res.json()["data"]["access_token"]


def test_get_current_user_profile():
    """Verify /auth/me returns the authenticated user context."""
    token = get_auth_token()
    headers = {"Authorization": f"Bearer {token}"}
    response = client.get("/api/v1/auth/me", headers=headers)
    assert response.status_code == 200
    data = response.json()["data"]
    assert data["email"] == "admin@company.com"
    assert data["role"] == "ADMIN"


def test_ticket_creation_and_auto_classification():
    """Verify ticket creation applies rule-based classification and returns 201 Created."""
    token = get_auth_token()
    headers = {"Authorization": f"Bearer {token}"}
    payload = {
        "title": "My laptop is not starting today",
        "description": "Black screen and power light flashes three times upon startup.",
    }
    response = client.post("/api/v1/tickets", json=payload, headers=headers)
    assert response.status_code == 201
    ticket = response.json()["data"]
    assert ticket["ticket_id"].startswith("INC-")
    assert ticket["category"] == "Hardware"
    assert ticket["priority"] == "HIGH"
    assert ticket["status"] == "OPEN"
    assert "sla_deadline" in ticket


def test_asset_creation_and_assignment_flow():
    """Verify asset registration, assignment to employee, and return."""
    import uuid
    uid = uuid.uuid4().hex[:6].upper()
    asset_id = f"LAP-{uid}"
    serial_no = f"SN-{uid}"

    token = get_auth_token()
    headers = {"Authorization": f"Bearer {token}"}

    # 1. Register asset
    asset_payload = {
        "asset_id": asset_id,
        "asset_type": "Laptop",
        "brand": "Lenovo",
        "model": "ThinkPad X1 Carbon",
        "serial_number": serial_no,
        "purchase_date": "2025-02-15",
        "purchase_cost": 1600.0,
        "specs": {"ram_gb": 32, "processor": "Intel Core i7"},
    }
    res_create = client.post("/api/v1/assets", json=asset_payload, headers=headers)
    assert res_create.status_code == 201

    # 2. Assign asset to employee
    res_assign = client.post(
        f"/api/v1/assets/{asset_id}/assign",
        json={"user_id": "EMP-101", "notes": "Workstation assigned"},
        headers=headers,
    )
    assert res_assign.status_code == 200
    assert res_assign.json()["data"]["status"] == "ASSIGNED"
    assert res_assign.json()["data"]["assigned_to"] == "EMP-101"

    # 3. Return asset
    res_return = client.post(f"/api/v1/assets/{asset_id}/return", headers=headers)
    assert res_return.status_code == 200
    assert res_return.json()["data"]["status"] == "AVAILABLE"
    assert res_return.json()["data"]["assigned_to"] is None


def test_asset_batch_return_flow():
    """Verify batch return of multiple assigned assets."""
    import uuid
    token = get_auth_token()
    headers = {"Authorization": f"Bearer {token}"}

    ids = []
    for _ in range(2):
        uid = uuid.uuid4().hex[:6].upper()
        asset_id = f"AST-B-{uid}"
        client.post(
            "/api/v1/assets",
            json={
                "asset_id": asset_id,
                "asset_type": "Keyboard",
                "brand": "Dell",
                "model": "KB216",
                "serial_number": f"SN-KB-{uid}",
                "purchase_date": "2025-01-01",
                "purchase_cost": 25.0,
            },
            headers=headers,
        )
        client.post(
            f"/api/v1/assets/{asset_id}/assign",
            json={"user_id": "EMP-101", "notes": "Batch test assign"},
            headers=headers,
        )
        ids.append(asset_id)

    res_batch = client.post(
        "/api/v1/assets/return-batch",
        json={"asset_ids": ids},
        headers=headers,
    )
    assert res_batch.status_code == 200
    assert len(res_batch.json()["data"]["returned_ids"]) == 2


def test_ticket_lifecycle_state_machine():
    """Verify ticket progression through OPEN -> ASSIGNED -> IN_PROGRESS -> RESOLVED -> CLOSED."""
    token = get_auth_token()
    headers = {"Authorization": f"Bearer {token}"}

    # Create ticket
    res_create = client.post(
        "/api/v1/tickets",
        json={"title": "Printer paper jam in 3rd floor", "description": "Need assistance clearing paper jam."},
        headers=headers,
    )
    ticket_id = res_create.json()["data"]["ticket_id"]

    # Assign ticket
    res_assign = client.post(
        f"/api/v1/tickets/{ticket_id}/assign",
        json={"assigned_to": "SUP-201", "comments": "Assigned to helpdesk"},
        headers=headers,
    )
    assert res_assign.status_code == 200
    assert res_assign.json()["data"]["status"] == "ASSIGNED"

    # Start progress
    res_prog = client.post(f"/api/v1/tickets/{ticket_id}/progress", headers=headers)
    assert res_prog.status_code == 200
    assert res_prog.json()["data"]["status"] == "IN_PROGRESS"

    # Resolve ticket
    res_res = client.post(
        f"/api/v1/tickets/{ticket_id}/resolve",
        json={"resolution": "Cleared rollers and ran test page successfully."},
        headers=headers,
    )
    assert res_res.status_code == 200
    assert res_res.json()["data"]["status"] == "RESOLVED"

    # Close ticket
    res_close = client.post(f"/api/v1/tickets/{ticket_id}/close", headers=headers)
    assert res_close.status_code == 200
    assert res_close.json()["data"]["status"] == "CLOSED"


def test_invalid_status_transition_error_mapping():
    """Verify invalid transition (e.g., closing open ticket directly) is intercepted and returns 422."""
    token = get_auth_token()
    headers = {"Authorization": f"Bearer {token}"}

    # Create open ticket
    res_create = client.post(
        "/api/v1/tickets",
        json={"title": "Test invalid transition", "description": "Attempting invalid status transition directly to closed."},
        headers=headers,
    )
    ticket_id = res_create.json()["data"]["ticket_id"]

    # Attempt illegal transition: resolving directly from OPEN without IN_PROGRESS
    res_illegal = client.post(
        f"/api/v1/tickets/{ticket_id}/resolve",
        json={"resolution": "Illegal jump straight to resolved"},
        headers=headers,
    )
    # Custom exception InvalidStatusTransitionError mapped to HTTP 422 Unprocessable Entity
    assert res_illegal.status_code == 422
    assert "Invalid Ticket status transition" in res_illegal.json()["message"]


def test_reports_generator_csv_stream():
    """Verify GET /reports/tickets?format=csv returns streaming text/csv."""
    token = get_auth_token()
    headers = {"Authorization": f"Bearer {token}"}
    response = client.get("/api/v1/reports/tickets?format=csv", headers=headers)
    assert response.status_code == 200
    assert "text/csv" in response.headers["content-type"]
    assert "ticket_id,title,category" in response.text


def test_support_only_sees_assigned_tickets():
    """Verify SUPPORT role only retrieves and accesses tickets assigned to their user_id."""
    support_token = get_auth_token(email="support@company.com", password="Support@1234")
    support_headers = {"Authorization": f"Bearer {support_token}"}

    # 1. Admin creates an unassigned ticket
    admin_token = get_auth_token(email="admin@company.com", password="Admin@1234")
    admin_headers = {"Authorization": f"Bearer {admin_token}"}
    res_create = client.post(
        "/api/v1/tickets",
        json={"title": "Unassigned incident for test", "description": "Needs triage"},
        headers=admin_headers,
    )
    unassigned_ticket_id = res_create.json()["data"]["ticket_id"]

    # 2. Support lists tickets: all tickets returned must be assigned to SUP-201
    res_list = client.get("/api/v1/tickets", headers=support_headers)
    assert res_list.status_code == 200
    tickets = res_list.json()["data"]
    for t in tickets:
        assert t["assigned_to"] == "SUP-201"
    assert not any(t["ticket_id"] == unassigned_ticket_id for t in tickets)

    # 3. Support cannot view details of unassigned ticket
    res_detail = client.get(f"/api/v1/tickets/{unassigned_ticket_id}", headers=support_headers)
    assert res_detail.status_code == 403

    # 4. Support cannot progress unassigned ticket
    res_prog = client.post(f"/api/v1/tickets/{unassigned_ticket_id}/progress", headers=support_headers)
    assert res_prog.status_code == 403

