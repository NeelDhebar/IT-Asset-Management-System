================================================================================
SMART IT ASSET & SUPPORT TICKET MANAGEMENT SYSTEM
================================================================================
Version: 1.0.0
Author: Python Capstone Project
License: MIT License
Technology Stack: Python 3.12+ / 3.14 | FastAPI | SQLAlchemy | PostgreSQL / SQLite
                  Vanilla HTML5 / CSS3 / JavaScript Single-Page Application (SPA)
================================================================================


1. PROJECT OVERVIEW
--------------------------------------------------------------------------------
The Smart IT Asset & Support Ticket Management System is an enterprise-grade,
full-stack platform designed to automate the complete lifecycle of corporate IT
hardware assets and internal support incident tickets.

The platform provides role-governed workflows for three organizational tiers:
  1. Employees (Self-Service Portal):
     - View hardware equipment currently assigned to their profile.
     - Select a specific assigned asset when raising a support ticket.
     - Submit equipment requisitions to request new or replacement hardware.
     - Strict Privacy: Cannot view other employees or assets assigned to others.
     - Track ticket SLA countdowns and close resolved issues.

  2. IT Support Engineers:
     - Monitor global ticket queues with live SLA countdowns and breach alerts.
     - Claim, progress, and provide structured resolutions for incident tickets.
     - Inspect polymorphic hardware specifications and asset histories.

  3. System Administrators:
     - Register and manage hardware assets across their entire lifecycle (Available,
       Assigned, Maintenance, Retired).
     - Assign assets to employees, execute single or batch asset returns.
     - Provision and manage users with Role-Based Access Control (RBAC).
     - Stream memory-efficient analytical CSV reports using Python generators.
     - Audit system activity logs and process batch flat files with OS archiving.


2. KEY TECHNICAL HIGHLIGHTS & ARCHITECTURE
--------------------------------------------------------------------------------
- Layered / MVC Architecture: Strict separation between API routers, business
  service logic, data repositories (ACID compliance), and domain models.
- Object-Oriented Programming (OOP) Domain Hierarchy:
  * Abstract base class: Asset
  * Concrete polymorphic classes: Laptop, Monitor, Keyboard, Mouse, Printer
  * Demonstrates Inheritance, Encapsulation, Polymorphism, and Composition
    (Warranty components).
- Rule-Based Ticket Classification:
  * Automatically categorizes tickets (Hardware, Network, Software, Access)
    and predicts SLA deadlines using regex and pattern matching.
- Real-Time SLA Management Engine:
  * Computes precise deadlines and remaining response minutes using datetime
    and timedelta, with visual breach warnings.
- Memory-Efficient Streaming Generators:
  * Streams large analytical datasets and CSV exports chunk-by-chunk using
    Python generators (yield) with O(1) memory consumption.
- Cross-Cutting Custom Decorators:
  * Performance profiling (@measure_execution_time).
  * Activity audit logging (@log_activity).
  * Role authorization guards (@login_required, @admin_required).
- Robust Database Support:
  * Production: Neon Cloud Serverless PostgreSQL with connection pooling.
  * Development / Offline: Local SQLite fallback with automatic schema creation.


3. DIRECTORY STRUCTURE
--------------------------------------------------------------------------------
IT_Asset_Management_System/
│
├── backend/
│   ├── app/
│   │   ├── api/                    # REST routers & WebSocket managers
│   │   │   ├── auth.py             # Authentication & JWT issuance
│   │   │   ├── users.py            # User CRUD & access control
│   │   │   ├── assets.py           # Asset inventory & lifecycle transitions
│   │   │   ├── tickets.py          # Incident ticket state transitions
│   │   │   ├── reports.py          # Generator-based CSV streaming
│   │   │   ├── files.py            # Batch file processing & external API
│   │   │   └── websocket.py        # Real-time WebSocket connection manager
│   │   │
│   │   ├── database/               # Relational persistence layer
│   │   │   ├── connection.py       # Thread-safe database connection manager
│   │   │   └── repositories.py     # ACID-compliant repository implementations
│   │   │
│   │   ├── models/                 # Domain & ORM entity definitions
│   │   │   ├── domain_assets.py    # Polymorphic OOP asset hierarchy
│   │   │   ├── enums.py            # UserRole, TicketStatus, AssetStatus, etc.
│   │   │   └── orm.py              # SQLAlchemy database tables
│   │   │
│   │   ├── schemas/                # Pydantic request / response validation
│   │   │   ├── common.py           # Standard APIResponse envelopes
│   │   │   ├── user.py             # User and authentication schemas
│   │   │   ├── asset.py            # Asset registration & assignment schemas
│   │   │   └── ticket.py           # Ticket creation, update, & SLA schemas
│   │   │
│   │   ├── services/               # Core business logic services
│   │   │   ├── asset_service.py    # Asset domain logic & factory instantiation
│   │   │   ├── ticket_service.py   # State machine & lifecycle management
│   │   │   ├── classifier_service.py # Rule-based regex classification
│   │   │   ├── sla_service.py      # SLA deadline calculation & breach checks
│   │   │   ├── report_service.py   # Streaming CSV generator logic
│   │   │   ├── file_service.py     # Flat-file parsing & OS archiving
│   │   │   └── external_api.py     # Resilient external REST client (requests)
│   │   │
│   │   ├── static/                 # Embedded frontend bundle for Docker
│   │   │   ├── css/styles.css      # Dark glassmorphic stylesheet
│   │   │   ├── js/app.js           # Client controller & API consumer
│   │   │   └── index.html          # HTML5 single-page application
│   │   │
│   │   ├── utils/                  # Shared utilities & security
│   │   │   ├── decorators.py       # Execution timing & logging decorators
│   │   │   ├── exceptions.py       # Domain exception hierarchy
│   │   │   ├── generators.py       # Generator functions
│   │   │   ├── logger.py           # Centralized logging manager
│   │   │   └── security.py         # PBKDF2 password hashing & JWT tokens
│   │   │
│   │   ├── config.py               # Singleton application configuration
│   │   └── main.py                 # FastAPI app entry point & lifespan
│   │
│   ├── tests/                      # Automated Pytest suite (37 tests)
│   ├── .env.dev                    # Development environment configuration
│   ├── .env.prod                   # Production environment configuration
│   └── requirements.txt            # Python dependencies
│
├── frontend/                       # Static frontend application
│   ├── css/styles.css              # Frontend styling system
│   ├── js/app.js                   # Client frontend script
│   └── index.html                  # Single-page interface
│
├── Dockerfile                      # Production container specification
├── .dockerignore                   # Docker ignore definitions
├── render.yaml                     # Render infrastructure deployment config
├── README.md                       # Comprehensive markdown documentation
└── README.txt                      # Project plain-text manual (this file)


4. DEFAULT DEMO ACCOUNTS & ROLES
--------------------------------------------------------------------------------
The database seeds three primary demo profiles for testing:

+---------------+-----------------------+---------------+--------------------------------------+
| Role          | Email                 | Password      | Primary Capabilities                 |
+---------------+-----------------------+---------------+--------------------------------------+
| Administrator | admin@company.com     | Admin@1234    | Full system access: Assets, Users,   |
|               |                       |               | Tickets, CSV Reports, File Ops       |
+---------------+-----------------------+---------------+--------------------------------------+
| IT Support    | support@company.com   | Support@1234  | Incident queue, ticket assignment,   |
|               |                       |               | progression, resolution, SLA review  |
+---------------+-----------------------+---------------+--------------------------------------+
| Employee      | employee@company.com  | Emp@1234      | Self-service portal: Raise tickets,  |
|               |                       |               | select assigned assets, request      |
|               |                       |               | new hardware equipment               |
+---------------+-----------------------+---------------+--------------------------------------+


5. INSTALLATION & LOCAL SETUP
--------------------------------------------------------------------------------
Prerequisites:
  - Python 3.12 or 3.14 installed on your machine
  - Git version control

Step 1: Clone the repository
  git clone https://github.com/NeelDhebar/IT-Asset-Management-System.git
  cd IT-Asset-Management-System

Step 2: Create and activate a Python virtual environment
  Windows (PowerShell):
    python -m venv .venv
    .\.venv\Scripts\Activate.ps1

  Linux / macOS:
    python3 -m venv .venv
    source .venv/bin/activate

Step 3: Install required dependencies
  pip install -r backend/requirements.txt

Step 4: Launch the backend server
  Windows / Linux:
    cd backend
    uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload

Step 5: Access the application
  - Web Application:       http://localhost:8000/
  - Interactive API Docs:  http://localhost:8000/docs
  - Alternative ReDoc:     http://localhost:8000/redoc


6. DOCKER & CLOUD DEPLOYMENT
--------------------------------------------------------------------------------
The project contains a production-ready root Dockerfile configured for Render
and containerized cloud environments.

Build and run with Docker locally:
  docker build -t it-asset-management-system .
  docker run -p 8000:8000 it-asset-management-system

Cloud Deployment (Render):
  - Repository: https://github.com/NeelDhebar/IT-Asset-Management-System
  - Build Runtime: Docker
  - Database: Neon Cloud Serverless PostgreSQL
  - Environment Variables configured in Render dashboard:
      APP_ENV=prod
      DATABASE_URL=postgresql://<user>:<password>@<neon-host>/neondb?sslmode=require


7. RUNNING AUTOMATED TESTS
--------------------------------------------------------------------------------
The project features an automated Pytest test suite covering all architectural
layers (OOP inheritance, polymorphism, SLA logic, classification, generators,
decorators, file processing, and API integration).

To execute the test suite:
  cd backend
  pytest -v

All 37 test cases must pass with 100% green status.


8. API ENDPOINT SUMMARY
--------------------------------------------------------------------------------
Authentication:
  POST  /api/v1/auth/login             Authenticate user and receive JWT token
  GET   /api/v1/auth/me                Retrieve current user profile
  POST  /api/v1/auth/logout            Terminate session

Users (Admin / Support):
  GET   /api/v1/users                  List all users (Admin/Support only)
  POST  /api/v1/users                  Create new user account (Admin only)
  GET   /api/v1/users/{user_id}        Retrieve user details

Assets:
  GET   /api/v1/assets                 List assets (Employees scoped to own)
  POST  /api/v1/assets                 Register new hardware asset (Admin)
  GET   /api/v1/assets/{asset_id}      Get asset polymorphic details
  POST  /api/v1/assets/{id}/assign     Assign asset to an employee (Admin/Support)
  POST  /api/v1/assets/{id}/return     Return asset to inventory (Admin/Support)
  POST  /api/v1/assets/batch-return    Return multiple assets in one transaction
  POST  /api/v1/assets/{id}/retire     Retire hardware asset (Admin only)

Tickets:
  GET   /api/v1/tickets                List tickets (Role-scoped visibility)
  POST  /api/v1/tickets                Create ticket (with auto-classification)
  GET   /api/v1/tickets/{id}           Get ticket details
  GET   /api/v1/tickets/{id}/sla       Retrieve live SLA metrics & remaining time
  POST  /api/v1/tickets/{id}/assign    Assign ticket to support engineer
  POST  /api/v1/tickets/{id}/progress  Commence work on ticket (IN_PROGRESS)
  POST  /api/v1/tickets/{id}/resolve   Provide resolution details (RESOLVED)
  POST  /api/v1/tickets/{id}/close     Final closure of ticket (CLOSED)

Reports & Analytics:
  GET   /api/v1/reports/summary        High-level KPI counts & SLA metrics
  GET   /api/v1/reports/tickets        Stream ticket records (JSON or CSV export)
  GET   /api/v1/reports/assets         Stream asset inventory (JSON or CSV export)


================================================================================
END OF README.txt
================================================================================
