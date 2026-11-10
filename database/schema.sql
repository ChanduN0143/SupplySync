PRAGMA foreign_keys = ON;

-- =========================================
-- 1. SUPPLIERS
-- =========================================

CREATE TABLE IF NOT EXISTS suppliers (
    supplier_id TEXT PRIMARY KEY,
    supplier_name TEXT NOT NULL,
    email TEXT UNIQUE NOT NULL,
    contact_number TEXT,
    status TEXT NOT NULL DEFAULT 'ACTIVE'
        CHECK (status IN ('ACTIVE', 'INACTIVE'))
);

-- =========================================
-- 2. PURCHASE ORDERS
-- =========================================

CREATE TABLE IF NOT EXISTS purchase_orders (
    po_id TEXT PRIMARY KEY,
    supplier_id TEXT NOT NULL,
    order_date TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'OPEN'
        CHECK (status IN ('OPEN', 'PARTIAL', 'COMPLETED', 'CANCELLED')),

    FOREIGN KEY (supplier_id)
        REFERENCES suppliers(supplier_id)
);

-- =========================================
-- 3. PURCHASE ORDER LINES
-- =========================================

CREATE TABLE IF NOT EXISTS po_lines (
    po_line_id TEXT PRIMARY KEY,
    po_id TEXT NOT NULL,
    item_code TEXT NOT NULL,
    description TEXT,
    requested_qty REAL NOT NULL CHECK (requested_qty > 0),
    unit_price REAL NOT NULL CHECK (unit_price >= 0),
    required_date TEXT NOT NULL,

    UNIQUE (po_line_id, po_id),

    FOREIGN KEY (po_id)
        REFERENCES purchase_orders(po_id)
);

-- =========================================
-- 4. SUPPLIER ACKNOWLEDGEMENTS
-- =========================================

CREATE TABLE IF NOT EXISTS acknowledgements (
    ack_id TEXT PRIMARY KEY,
    po_id TEXT NOT NULL,
    po_line_id TEXT NOT NULL,
    revision INTEGER NOT NULL CHECK (revision > 0),
    accepted_qty REAL NOT NULL CHECK (accepted_qty >= 0),
    rejected_qty REAL NOT NULL CHECK (rejected_qty >= 0),
    submitted_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    status TEXT NOT NULL DEFAULT 'SUBMITTED'
        CHECK (status IN ('SUBMITTED', 'ACCEPTED', 'PARTIAL', 'REJECTED')),

    UNIQUE (po_line_id, revision),

    FOREIGN KEY (po_line_id, po_id)
        REFERENCES po_lines(po_line_id, po_id)
);

-- =========================================
-- 5. PROMISE DATE HISTORY
-- =========================================

CREATE TABLE IF NOT EXISTS promise_dates (
    promise_id TEXT PRIMARY KEY,
    ack_id TEXT NOT NULL,
    promised_date TEXT NOT NULL,
    revision INTEGER NOT NULL CHECK (revision > 0),
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,

    UNIQUE (ack_id, revision),

    FOREIGN KEY (ack_id)
        REFERENCES acknowledgements(ack_id)
);

-- =========================================
-- 6. CHANGE REQUESTS
-- =========================================

CREATE TABLE IF NOT EXISTS change_requests (
    change_id TEXT PRIMARY KEY,
    po_id TEXT NOT NULL,
    po_line_id TEXT NOT NULL,
    change_type TEXT NOT NULL
        CHECK (change_type IN ('QUANTITY', 'PRICE', 'DATE', 'MULTIPLE')),

    old_qty REAL NOT NULL,
    new_qty REAL NOT NULL,
    old_price REAL NOT NULL,
    new_price REAL NOT NULL,
    old_date TEXT NOT NULL,
    new_date TEXT NOT NULL,

    reason TEXT,
    status TEXT NOT NULL DEFAULT 'PENDING'
        CHECK (status IN ('PENDING', 'APPROVED', 'REJECTED', 'AUTO_APPROVED')),

    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (po_line_id, po_id)
        REFERENCES po_lines(po_line_id, po_id)
);

-- =========================================
-- 7. APPROVALS
-- =========================================

CREATE TABLE IF NOT EXISTS approvals (
    approval_id TEXT PRIMARY KEY,
    change_id TEXT NOT NULL,
    approver_role TEXT NOT NULL,
    decision TEXT NOT NULL DEFAULT 'PENDING'
        CHECK (decision IN ('PENDING', 'APPROVED', 'REJECTED')),

    comments TEXT,
    decided_at TEXT,

    FOREIGN KEY (change_id)
        REFERENCES change_requests(change_id)
);

-- =========================================
-- 8. INVENTORY PLANS
-- =========================================

CREATE TABLE IF NOT EXISTS inventory_plans (
    plan_id TEXT PRIMARY KEY,
    po_line_id TEXT NOT NULL UNIQUE,
    projected_qty REAL NOT NULL,
    projected_date TEXT NOT NULL,
    last_change_id TEXT,
    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (po_line_id)
        REFERENCES po_lines(po_line_id),

    FOREIGN KEY (last_change_id)
        REFERENCES change_requests(change_id)
);

-- =========================================
-- 9. PRODUCTION ORDERS
-- =========================================

CREATE TABLE IF NOT EXISTS production_orders (
    production_id TEXT PRIMARY KEY,
    plan_id TEXT NOT NULL,
    required_qty REAL NOT NULL,
    required_date TEXT NOT NULL,

    status TEXT NOT NULL DEFAULT 'ON_TRACK'
        CHECK (status IN ('ON_TRACK', 'SHORTAGE', 'AT_RISK', 'DELAYED')),

    FOREIGN KEY (plan_id)
        REFERENCES inventory_plans(plan_id)
);

-- =========================================
-- 10. NOTIFICATIONS
-- =========================================

CREATE TABLE IF NOT EXISTS notifications (
    notification_id TEXT PRIMARY KEY,
    po_id TEXT NOT NULL,
    recipient_role TEXT NOT NULL,
    message TEXT NOT NULL,

    status TEXT NOT NULL DEFAULT 'UNREAD'
        CHECK (status IN ('UNREAD', 'READ')),

    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (po_id)
        REFERENCES purchase_orders(po_id)
);

-- =========================================
-- 11. AUDIT EVENTS
-- =========================================

CREATE TABLE IF NOT EXISTS audit_events (
    event_id INTEGER PRIMARY KEY AUTOINCREMENT,
    entity_type TEXT NOT NULL,
    entity_id TEXT NOT NULL,
    event_type TEXT NOT NULL,
    actor TEXT NOT NULL,
    details TEXT,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- =========================================
-- INDEXES FOR FASTER QUERIES
-- =========================================

CREATE INDEX IF NOT EXISTS idx_po_supplier
ON purchase_orders(supplier_id);

CREATE INDEX IF NOT EXISTS idx_po_line
ON po_lines(po_id);

CREATE INDEX IF NOT EXISTS idx_ack_line
ON acknowledgements(po_line_id);

CREATE INDEX IF NOT EXISTS idx_change_status
ON change_requests(status);

CREATE INDEX IF NOT EXISTS idx_approval_decision
ON approvals(decision);

CREATE INDEX IF NOT EXISTS idx_audit_entity
ON audit_events(entity_type, entity_id);

CREATE INDEX IF NOT EXISTS idx_notification_status
ON notifications(status);
