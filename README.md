# SupplySync
### Supplier Collaboration & Supply Chain Control Tower

SupplySync is a supply-chain collaboration and visibility platform designed to help procurement and planning teams manage supplier acknowledgements, delivery commitments, purchase-order changes, approvals, inventory planning, and downstream production risks.

The platform brings important supplier and purchase-order workflows into one place, helping planners identify exceptions, make informed decisions, and maintain an auditable record of operational changes.

## 🚀 Run SupplySync Locally

**Frontend:** http://localhost:5173

**Backend API:** http://127.0.0.1:8000

**API Documentation:** http://127.0.0.1:8000/docs

> Note: These links work when SupplySync is running locally on your computer.

---

## 1. Business Problem

Supply-chain teams often coordinate purchase orders, supplier confirmations, delivery commitments, quantity changes, and production requirements across disconnected processes.

This can result in:

- Delayed visibility into supplier commitments.
- Quantity mismatches between purchase orders and acknowledgements.
- Unapproved changes to quantities, prices, and delivery dates.
- Inventory shortages and production schedule risks.
- Limited traceability of approval decisions.
- Difficulty identifying operational exceptions.

**SupplySync addresses these challenges** through a centralized supplier collaboration and supply-chain control tower.

## 2. Key Features

### Purchase Order & Supplier Management
- View and manage purchase orders and line items.
- Maintain supplier records and information.
- Monitor purchase-order status and quantities.

### Supplier Collaboration
- Record supplier acknowledgements.
- Track accepted and rejected quantities.
- Maintain promised delivery dates and revisions.
- Identify partial acknowledgements and delivery commitment differences.

### Change Request Management
- Submit purchase-order quantity, price, and delivery-date changes.
- Compare original and proposed values.
- Classify requests using configurable business rules.
- Route significant changes for manual approval.

### Approval Management
- Review pending change requests.
- Approve or reject requests with comments.
- Maintain approval decisions and timestamps.
- Preserve workflow traceability.

### Inventory & Production Planning
- Reflect approved purchase-order changes in inventory plans.
- Monitor projected quantities and delivery dates.
- Evaluate production schedule risks.
- Identify potential shortages and delays.

### Exception & Anomaly Detection
- Identify inconsistent supplier and purchase-order records.
- Detect suspicious workflow conditions.
- Classify anomalies by severity.
- Review exceptions through the application.

### Audit & Operational Visibility
- Maintain an audit trail of important business events.
- View notifications and workflow activity.
- Monitor operational metrics through a centralized dashboard.

### Logistics Database Foundation
The database migration also introduces four additional entities:

- Shipments
- Shipment lines
- Warehouse receipts
- Warehouse receipt lines

These provide the initial relational database foundation for future carrier tracking and warehouse receiving workflows. Dedicated shipment and warehouse API/UI workflows are not yet implemented.

---

## 3. Technology Stack

| Layer | Technology |
|---|---|
| Frontend | React 19, JavaScript |
| Build Tool | Vite |
| Styling | CSS |
| UI Icons | Lucide React |
| Charts | Recharts |
| API Client | Axios |
| Backend | Python, FastAPI |
| Data Validation | Pydantic |
| Database | SQLite |
| API Server | Uvicorn |
| Testing | Pytest, HTTPX |

---

## 4. System Architecture


             SUPPLIER / PLANNER
                     |
                     v
              REACT FRONTEND
                     |
                     v
               AXIOS CLIENT
                     |
                     v
               FASTAPI BACKEND
                     |
          +----------+-----------+
          |          |           |
          v          v           v
      BUSINESS    WORKFLOW     ANOMALY
       RULES      PROCESSING   DETECTION
          |          |           |
          +----------+-----------+
                     |
                     v
               SQLITE DATABASE
                     |
       +-------------+-------------+
       |             |             |
       v             v             v
   PURCHASE       INVENTORY     PRODUCTION
    ORDERS          PLANS       SCHEDULES
       |
       v
  ACKNOWLEDGEMENTS
       |
       v
  CHANGE REQUESTS
       |
       v
    APPROVALS
       |
       v
   AUDIT EVENTS


The React frontend communicates with the FastAPI backend through HTTP API endpoints. The backend applies business rules, validates requests, processes workflow decisions, and persists information in SQLite.



## 5. Core Business Workflow

1. A planner creates or reviews a purchase order.
2. A supplier acknowledges the order.
3. Accepted quantities, rejected quantities, and promised delivery dates are recorded.
4. A supplier or planner submits a change request.
5. Business rules classify the change for automatic or manual approval.
6. The planner reviews and approves or rejects applicable requests.
7. Approved changes are reflected in inventory planning.
8. Production requirements are evaluated for shortages and schedule risks.
9. Anomalies are identified for investigation.
10. Important business decisions and workflow events are recorded in audit logs.



## 6. Database Design

The existing database includes the following core entities:

| Entity | Purpose |
|---|---|
| suppliers | Supplier information |
| purchase_orders | Purchase-order headers |
| po_lines | Purchase-order line items |
| acknowledgements | Supplier acknowledgement records |
| promise_dates | Supplier delivery commitments |
| change_requests | Requested purchase-order changes |
| approvals | Approval decisions |
| inventory_plans | Inventory projections |
| production_orders | Downstream production requirements |
| notifications | Workflow notifications |
| audit_events | Audit history |
| anomaly_cases | Detected exceptions |

The additive logistics migration introduces:

| Entity | Purpose |
|---|---|
| shipments | Carrier shipment records |
| shipment_lines | Items and quantities included in shipments |
| warehouse_receipts | Warehouse receiving records |
| warehouse_receipt_lines | Received, accepted, rejected, and damaged quantities |

---

## 7. Project Structure

```text
SupplySync/
│
├── backend/
│   └── app/
│       ├── __init__.py
│       ├── database.py
│       └── main.py
│
├── database/
│   ├── schema.sql
│   └── logistics_migration.sql
│
├── data/
│   └── (locally generated database and CSV data)
│
├── docs/
│
├── frontend/
│   ├── public/
│   ├── src/
│   │   ├── assets/
│   │   ├── services/
│   │   │   └── api.js
│   │   ├── App.jsx
│   │   ├── App.css
│   │   ├── index.css
│   │   └── main.jsx
│   └── package.json
│
├── generator/
│   ├── generate_data.py
│   └── extend_data.py
│
├── tests/
│   ├── test_api.py
│   └── test_business_rules.py
│
├── app.py
├── business_rules.py
├── db.py
├── requirements.txt
├── verify_schema.py
├── inspect_database.py
├── .gitignore
└── README.md
```

---

## 8. Installation & Setup

### Prerequisites

Install the following:

- Python 3.10 or later
- Node.js and npm
- Git

### Step 1: Clone the repository

```bash
git clone https://github.com/YOUR_USERNAME/SupplySync.git
cd SupplySync
```

Replace `YOUR_USERNAME` with the GitHub account that owns the repository.

### Step 2: Create a Python virtual environment

Windows PowerShell:

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
```

### Step 3: Install backend dependencies

```powershell
pip install -r requirements.txt
```

### Step 4: Generate the initial database

Warning: The initial data generator deletes an existing `data/supplysync.db` before recreating it. Run these commands only when setting up a fresh database.

```powershell
python generator/generate_data.py
python generator/extend_data.py
```

### Step 5: Apply the logistics migration

```powershell
@'
import sqlite3

connection = sqlite3.connect("data/supplysync.db")
connection.execute("PRAGMA foreign_keys = ON")

with open("database/logistics_migration.sql", encoding="utf-8-sig") as file:
    connection.executescript(file.read())

violations = connection.execute("PRAGMA foreign_key_check").fetchall()

if violations:
    raise RuntimeError(violations)

connection.close()
print("Database migration completed successfully.")
'@ | python -
```

### Step 6: Install frontend dependencies

Open a terminal in the frontend directory:

```powershell
cd frontend
npm install
```

---

## 9. Running the Application

### Start the backend

From the project root:

```powershell
python -m uvicorn backend.app.main:app --reload
```

Backend:

`http://127.0.0.1:8000`

Interactive API documentation:

`http://127.0.0.1:8000/docs`

### Start the frontend

Open a second terminal:

```powershell
cd frontend
npm run dev
```

Frontend:

`http://localhost:5173`

Keep both development servers running while using the application.

---

## 10. API Overview

The FastAPI backend exposes endpoints for the core business workflows.

| Endpoint | Purpose |
|---|---|
| GET `/` | API root |
| GET `/api/health` | Backend and database health |
| GET `/api/summary` | Dashboard summary |
| GET `/api/orders` | Purchase orders |
| GET `/api/orders/{po_id}` | Purchase-order details |
| GET `/api/suppliers` | Supplier records |
| GET `/api/acknowledgements` | Supplier acknowledgements |
| GET `/api/promise-dates` | Delivery commitments |
| GET `/api/change-requests` | Change requests |
| POST `/api/change-requests` | Create change request |
| POST `/api/change-requests/{change_id}/decision` | Record approval decision |
| GET `/api/approvals` | Approval history |
| GET `/api/inventory-plans` | Inventory projections |
| GET `/api/production-orders` | Production schedule records |
| GET `/api/anomalies` | Anomaly records |
| GET `/api/audit-events` | Audit history |

For request schemas, parameters, and interactive testing, visit `/docs` after starting the backend.

---

## 11. Testing

Run backend tests from the project root:

```powershell
python -m pytest tests -q
```

Check Python syntax:

```powershell
python -m compileall backend
```

Build the frontend:

```powershell
cd frontend
npm run build
```

The project has previously passed its backend test suite (10 tests) and frontend production build. Re-run these commands against the latest submitted version to verify it.

---

## 12. Business Rules & Decision Logic

SupplySync uses configurable thresholds to classify purchase-order changes.

Examples include:

- Quantity changes greater than 10% require manual approval.
- Price changes greater than 5% require manual approval.
- Delivery-date changes greater than 7 days require manual approval.
- Smaller changes can qualify for automatic approval.

The schedule-impact logic evaluates delivery delays and quantity shortages to classify production risk.

These thresholds are configurable business rules and can be adapted to an organization's procurement policies.

---

## 13. Demo Scenarios

For a hackathon demonstration, showcase these workflows:

1. Open the dashboard and explain the operational metrics.
2. Select a purchase order and inspect its supplier and line-item information.
3. Review supplier acknowledgement quantities and promised dates.
4. Submit a quantity or delivery-date change request.
5. Demonstrate automatic versus manual approval classification.
6. Approve or reject a pending request.
7. Show the resulting inventory and production schedule impact.
8. Open the anomaly detection page and explain an exception.
9. Show the audit log to demonstrate traceability.

---

## 14. Current Scope & Future Enhancements

The current implementation focuses on supplier collaboration, purchase-order changes, approval workflows, inventory planning, production impact, anomaly visibility, and auditability.

Planned enhancements include:

- Carrier shipment creation and tracking APIs.
- Shipment status updates and delivery-event history.
- Warehouse goods-receipt workflows.
- Partial delivery and damaged-goods reconciliation.
- Automated notifications for shipment delays.
- Role-based authentication and authorization.
- Advanced operational analytics and reporting.
- Automated integration with external ERP and supplier systems.

The logistics database schema is an initial foundation; the corresponding application workflows remain future implementation work.

---

## 15. Hackathon Project Summary

Project: SupplySync
Category: Supply Chain Management / Supplier Collaboration
Primary Users: Suppliers, Planners, and Supply Chain Operations Teams

Objective: Improve supply-chain visibility and decision-making by connecting supplier acknowledgements, delivery commitments, purchase-order changes, approval decisions, inventory planning, and production schedule impacts in one centralized platform.

Core Value: Better visibility, faster exception handling, controlled approvals, downstream risk awareness, and traceable operational decisions.

---

## License

This project was developed as a hackathon submission. Add a license file if you intend to distribute it under a specific open-source license.

---

Built with React, FastAPI, Python, and SQLite.
