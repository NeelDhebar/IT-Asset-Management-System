"""Main Application Entrypoint for Smart IT Ops Lifecycle Management.

Configures FastAPI, lifespan hooks, CORS middleware, global exception handlers,
API routing, static dashboard serving, and real-time WebSocket channels.
"""

# pylint: disable=wrong-import-position

import os
import sys
from pathlib import Path
from contextlib import asynccontextmanager

# Ensure project root is in sys.path when executed directly as a script
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from fastapi import FastAPI, Request, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, FileResponse
from fastapi.staticfiles import StaticFiles

from app.config import get_settings
from app.utils.logger import get_logger
from app.utils.exceptions import AppException

from app.database.connection import DatabaseConnectionManager
from app.api.auth import router as auth_router
from app.api.users import router as users_router
from app.api.assets import router as assets_router
from app.api.tickets import router as tickets_router
from app.api.reports import router as reports_router
from app.api.files import router as files_router
from app.api.websocket import ws_manager
import json
from app.utils.security import hash_password
from app.models.orm import UserModel, AssetModel, TicketModel

logger = get_logger()
settings = get_settings()


def seed_initial_demo_users() -> None:
    """Seeds users, assets, and support tickets with unique, realistic demo data."""
    from datetime import datetime, timezone, timedelta
    db_mgr = DatabaseConnectionManager()
    session = db_mgr.get_session()
    try:
        # ── Users ────────────────────────────────────────────────────────────
        if session.query(UserModel).count() == 0:
            logger.info("Seeding demo users...")
            session.add_all([
                UserModel(user_id="ADM-001", email="admin@company.com",
                          hashed_password=hash_password("Admin@1234"),
                          full_name="System Administrator", role="ADMIN",
                          department="IT Infrastructure", is_active=True),
                UserModel(user_id="SUP-201", email="support@company.com",
                          hashed_password=hash_password("Support@1234"),
                          full_name="Sarah Support", role="SUPPORT",
                          department="IT Helpdesk", is_active=True),
                UserModel(user_id="EMP-101", email="employee@company.com",
                          hashed_password=hash_password("Emp@1234"),
                          full_name="John Employee", role="EMPLOYEE",
                          department="Product Design", is_active=True),
            ])
            session.commit()
            logger.info("Demo users seeded.")

        # ── Assets ───────────────────────────────────────────────────────────
        if session.query(AssetModel).count() == 0:
            logger.info("Seeding demo assets...")
            session.add_all([
                # Laptops
                AssetModel(asset_id="LAP-101", asset_type="Laptop",
                           brand="Dell", model="XPS 15 9530",
                           serial_number="SN-DELL-XPS-1001",
                           purchase_date="2024-01-15", purchase_cost=1850.00,
                           status="ASSIGNED", assigned_to="EMP-101",
                           specs_json=json.dumps({"processor": "Intel Core i7-13700H",
                                                  "ram_gb": 32, "storage_gb": 1000,
                                                  "battery_health_percent": 94})),
                AssetModel(asset_id="LAP-102", asset_type="Laptop",
                           brand="Lenovo", model="ThinkPad X1 Carbon Gen 11",
                           serial_number="SN-LNV-X1C-2002",
                           purchase_date="2024-03-10", purchase_cost=1620.00,
                           status="AVAILABLE", assigned_to=None,
                           specs_json=json.dumps({"processor": "Intel Core i5-1345U",
                                                  "ram_gb": 16, "storage_gb": 512,
                                                  "battery_health_percent": 100})),
                AssetModel(asset_id="LAP-103", asset_type="Laptop",
                           brand="Apple", model="MacBook Pro 14 (M3)",
                           serial_number="SN-APL-MBP-3003",
                           purchase_date="2024-06-01", purchase_cost=2399.00,
                           status="AVAILABLE", assigned_to=None,
                           specs_json=json.dumps({"processor": "Apple M3 Pro",
                                                  "ram_gb": 18, "storage_gb": 512,
                                                  "battery_health_percent": 100})),
                AssetModel(asset_id="LAP-104", asset_type="Laptop",
                           brand="HP", model="EliteBook 840 G10",
                           serial_number="SN-HP-EB840-4004",
                           purchase_date="2023-09-20", purchase_cost=1350.00,
                           status="UNDER_REPAIR", assigned_to=None,
                           specs_json=json.dumps({"processor": "Intel Core i7-1355U",
                                                  "ram_gb": 16, "storage_gb": 512,
                                                  "battery_health_percent": 71})),
                AssetModel(asset_id="LAP-001", asset_type="Laptop",
                           brand="Lenovo", model="ThinkPad T14s Gen 2",
                           serial_number="SN-LNV-T14S-0001",
                           purchase_date="2021-05-12", purchase_cost=1150.00,
                           status="RETIRED", assigned_to=None,
                           specs_json=json.dumps({"processor": "AMD Ryzen 5 PRO 5650U",
                                                  "ram_gb": 8, "storage_gb": 256,
                                                  "battery_health_percent": 38})),
                # Monitors
                AssetModel(asset_id="MON-201", asset_type="Monitor",
                           brand="Dell", model="UltraSharp U2723QE 27\"",
                           serial_number="SN-DELL-U27-5005",
                           purchase_date="2023-11-05", purchase_cost=550.00,
                           status="AVAILABLE", assigned_to=None,
                           specs_json=json.dumps({"resolution": "3840x2160",
                                                  "panel": "IPS", "refresh_hz": 60})),
                AssetModel(asset_id="MON-202", asset_type="Monitor",
                           brand="LG", model="27UK850-W 27\" 4K",
                           serial_number="SN-LG-27UK-6006",
                           purchase_date="2023-08-17", purchase_cost=420.00,
                           status="AVAILABLE", assigned_to=None,
                           specs_json=json.dumps({"resolution": "3840x2160",
                                                  "panel": "IPS", "refresh_hz": 60})),
                # Keyboard
                AssetModel(asset_id="KEY-301", asset_type="Keyboard",
                           brand="Logitech", model="MX Keys Advanced",
                           serial_number="SN-LGT-MXKEYS-7007",
                           purchase_date="2024-02-01", purchase_cost=119.00,
                           status="AVAILABLE", assigned_to=None,
                           specs_json=json.dumps({"layout": "US Full-Size",
                                                  "backlit": True, "wireless": True})),
                # Mouse
                AssetModel(asset_id="MOU-401", asset_type="Mouse",
                           brand="Logitech", model="MX Master 3S",
                           serial_number="SN-LGT-MXMS-8008",
                           purchase_date="2024-02-01", purchase_cost=99.00,
                           status="AVAILABLE", assigned_to=None,
                           specs_json=json.dumps({"dpi": 8000, "wireless": True,
                                                  "silent_clicks": True})),
                # Printer
                AssetModel(asset_id="PRN-501", asset_type="Printer",
                           brand="HP", model="LaserJet Pro M404dn",
                           serial_number="SN-HP-LJM404-9009",
                           purchase_date="2022-12-15", purchase_cost=380.00,
                           status="AVAILABLE", assigned_to=None,
                           specs_json=json.dumps({"ppm": 38, "duplex": True,
                                                  "network": True})),
            ])
            session.commit()
            logger.info("Demo assets seeded: 5 laptops, 2 monitors, keyboard, mouse, printer.")

        # ── Tickets ──────────────────────────────────────────────────────────
        if session.query(TicketModel).count() == 0:
            logger.info("Seeding demo tickets...")
            now = datetime.now(timezone.utc)
            session.add_all([
                # Assigned to SUP-201
                TicketModel(ticket_id="INC-1001",
                            title="VPN gateway timeout when connecting from home",
                            description="Multiple engineers unable to connect via OpenVPN since 09:00. Gateway shows authentication timeouts. Affects entire remote team.",
                            category="Network", priority="HIGH", status="ASSIGNED",
                            created_by="EMP-101", assigned_to="SUP-201",
                            sla_deadline=now + timedelta(hours=4)),
                TicketModel(ticket_id="INC-1002",
                            title="Microsoft Teams desktop app crashes on startup",
                            description="Teams crashes immediately after login on Windows 11. Reinstall attempted — issue persists. Meeting in 2 hours.",
                            category="Software", priority="HIGH", status="IN_PROGRESS",
                            created_by="EMP-101", assigned_to="SUP-201",
                            sla_deadline=now + timedelta(hours=3)),
                TicketModel(ticket_id="INC-1003",
                            title="Office printer on 3rd floor not printing",
                            description="PRN-501 shows paper jam error but tray is clear. All jobs stuck in queue. Affects entire floor.",
                            category="Hardware", priority="MEDIUM", status="ASSIGNED",
                            created_by="ADM-001", assigned_to="SUP-201",
                            sla_deadline=now + timedelta(hours=8)),
                # Open / Unassigned — visible to Admin
                TicketModel(ticket_id="INC-2001",
                            title="Monitor MON-202 showing intermittent flickering",
                            description="Display flickers every few minutes, especially during video playback. Tested with two different DisplayPort cables.",
                            category="Hardware", priority="MEDIUM", status="OPEN",
                            created_by="ADM-001", assigned_to=None,
                            sla_deadline=now + timedelta(hours=8)),
                TicketModel(ticket_id="INC-2002",
                            title="Active Directory account locked out",
                            description="User locked out after 5 failed password attempts. Requires admin reset and MFA re-enrolment.",
                            category="Access", priority="HIGH", status="OPEN",
                            created_by="ADM-001", assigned_to=None,
                            sla_deadline=now + timedelta(hours=4)),
                TicketModel(ticket_id="INC-2003",
                            title="Adobe Creative Cloud license activation needed",
                            description="Product Design team requires Adobe CC on LAP-103. Department head approval received.",
                            category="Software", priority="LOW", status="OPEN",
                            created_by="ADM-001", assigned_to=None,
                            sla_deadline=now + timedelta(hours=24)),
                TicketModel(ticket_id="INC-2004",
                            title="Production server disk usage at 91%",
                            description="prod-server-01 disk at 91% capacity. Risk of service disruption. Requires cleanup or volume expansion.",
                            category="Hardware", priority="CRITICAL", status="OPEN",
                            created_by="ADM-001", assigned_to=None,
                            sla_deadline=now + timedelta(hours=2)),
                TicketModel(ticket_id="INC-2005",
                            title="Ethernet switch port failure in meeting room A",
                            description="Port 12 on meeting room A switch is dead. Wired conference setup non-functional. Wireless available as fallback.",
                            category="Network", priority="MEDIUM", status="OPEN",
                            created_by="ADM-001", assigned_to=None,
                            sla_deadline=now + timedelta(hours=8)),
                # Resolved / Closed — historical SLA data
                TicketModel(ticket_id="INC-3001",
                            title="Laptop LAP-104 battery draining in under 2 hours",
                            description="Battery health at 71%. Replacement requested. Temporary workaround: always plugged in.",
                            category="Hardware", priority="MEDIUM", status="RESOLVED",
                            created_by="ADM-001", assigned_to="SUP-201",
                            resolution="Battery replacement ordered. Scheduled for next maintenance window.",
                            sla_deadline=now - timedelta(hours=2)),
                TicketModel(ticket_id="INC-3002",
                            title="Wi-Fi dropping in open-plan office every morning",
                            description="AP-07 loses connectivity between 09:00–09:30 daily. Channel congestion suspected during peak logins.",
                            category="Network", priority="HIGH", status="CLOSED",
                            created_by="ADM-001", assigned_to="SUP-201",
                            resolution="AP-07 firmware updated and channel set to auto-select. No recurrence in 5 days.",
                            sla_deadline=now - timedelta(hours=6)),
                # Employee's own ticket
                TicketModel(ticket_id="INC-4001",
                            title="Laptop screen cracked at corner",
                            description="Bottom-left corner of LAP-101 display cracked after accidental impact. No dead pixels but crack is growing. Request screen replacement.",
                            category="Hardware", priority="MEDIUM", status="OPEN",
                            created_by="EMP-101", assigned_to=None,
                            sla_deadline=now + timedelta(hours=8)),
            ])
            session.commit()
            logger.info("Demo tickets seeded: 3 assigned to support, 5 open, 2 historical, 1 employee.")

    except Exception as exc:
        session.rollback()
        logger.warning("Could not seed demo data: %s", exc)
    finally:
        session.close()


@asynccontextmanager
async def lifespan(_app: FastAPI):
    """Application lifespan event handler for startup and shutdown hooks."""
    logger.info("=== Starting %s (%s profile) ===", settings.APP_NAME, settings.APP_ENV.upper())
    # 1. Initialize DB tables
    db_manager = DatabaseConnectionManager()
    db_manager.create_tables()

    # 2. Seed default users
    seed_initial_demo_users()
    yield
    logger.info("=== Shutting down %s ===", settings.APP_NAME)


app = FastAPI(
    title=settings.APP_NAME,
    description=(
        "Production-style Smart IT Asset Management & Support Ticket Management System. "
        "Demonstrating OOP, SOLID principles, Layered Architecture, ACID transactions, "
        "SLA Tracking, Rule-based Classification, Generators, Decorators, and WebSockets."
    ),
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)

# CORS Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_origin_regex=r"^https?://(localhost|127\.0\.0\.1)(:\d+)?$",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Global Exception Handler for domain AppException hierarchy
@app.exception_handler(AppException)
async def app_exception_handler(_request: Request, exc: AppException):
    """Catches all domain AppException subclasses and transforms them into clean HTTP JSON responses."""
    logger.warning(
        "Domain exception intercepted: %s - %s [Status %d]",
        exc.__class__.__name__,
        exc.message,
        exc.status_code,
    )
    return JSONResponse(
        status_code=exc.status_code,
        content=exc.to_dict(),
    )


# Register API Routers under configured prefix
API_PREFIX = settings.API_V1_PREFIX
app.include_router(auth_router, prefix=API_PREFIX)
app.include_router(users_router, prefix=API_PREFIX)
app.include_router(assets_router, prefix=API_PREFIX)
app.include_router(tickets_router, prefix=API_PREFIX)
app.include_router(reports_router, prefix=API_PREFIX)
app.include_router(files_router, prefix=API_PREFIX)


# Real-time WebSocket Endpoint
@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """Persistent WebSocket channel for real-time ticket and asset updates."""
    await ws_manager.connect(websocket)
    try:
        while True:
            # Keep socket alive and accept ping/pong or client messages
            data = await websocket.receive_text()
            logger.debug("Received client WebSocket message: %s", data)
    except WebSocketDisconnect:
        ws_manager.disconnect(websocket)
    except Exception as exc:
        logger.warning("WebSocket connection encountered error: %s", exc)
        ws_manager.disconnect(websocket)


# Mount static directory for Frontend Web UI
static_dir = os.path.join(os.path.dirname(__file__), "static")
if not os.path.exists(static_dir):
    os.makedirs(static_dir, exist_ok=True)

app.mount("/static", StaticFiles(directory=static_dir), name="static")


@app.get("/", include_in_schema=False)
async def serve_index():
    """Serves the interactive frontend web dashboard."""
    index_file = os.path.join(static_dir, "index.html")
    if os.path.exists(index_file):
        return FileResponse(
            index_file,
            headers={
                "Cache-Control": "no-cache, no-store, must-revalidate",
                "Pragma": "no-cache",
                "Expires": "0",
            },
        )
    return {"message": f"Welcome to {settings.APP_NAME}. Visit /docs for Swagger API documentation."}


@app.get("/health", tags=["Health"])
async def health_check():
    """Basic health check and profile verification endpoint."""
    return {
        "status": "healthy",
        "app_env": settings.APP_ENV,
        "app_name": settings.APP_NAME,
        "version": "1.0.0",
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)
