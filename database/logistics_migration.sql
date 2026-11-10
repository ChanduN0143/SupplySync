PRAGMA foreign_keys = ON;

-- 1. Carrier shipment records
CREATE TABLE IF NOT EXISTS shipments (
    shipment_id TEXT PRIMARY KEY,
    po_id TEXT NOT NULL,
    carrier_name TEXT NOT NULL,
    tracking_number TEXT,
    dispatched_at TEXT,
    expected_arrival TEXT,
    actual_arrival TEXT,
    status TEXT NOT NULL DEFAULT 'CREATED'
        CHECK (status IN (
            'CREATED', 'DISPATCHED', 'IN_TRANSIT',
            'DELIVERED', 'CANCELLED'
        )),
    notes TEXT,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,

    UNIQUE (shipment_id, po_id),

    FOREIGN KEY (po_id)
        REFERENCES purchase_orders(po_id)
);

-- 2. Purchase order lines included in each shipment
CREATE TABLE IF NOT EXISTS shipment_lines (
    shipment_line_id TEXT PRIMARY KEY,
    shipment_id TEXT NOT NULL,
    po_id TEXT NOT NULL,
    po_line_id TEXT NOT NULL,
    shipped_qty REAL NOT NULL CHECK (shipped_qty > 0),

    UNIQUE (shipment_line_id, shipment_id),
    UNIQUE (shipment_id, po_line_id),

    FOREIGN KEY (shipment_id, po_id)
        REFERENCES shipments(shipment_id, po_id),

    FOREIGN KEY (po_line_id, po_id)
        REFERENCES po_lines(po_line_id, po_id)
);

-- 3. Warehouse receipt records
CREATE TABLE IF NOT EXISTS warehouse_receipts (
    receipt_id TEXT PRIMARY KEY,
    shipment_id TEXT NOT NULL,
    received_by TEXT NOT NULL,
    received_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    status TEXT NOT NULL DEFAULT 'RECORDED'
        CHECK (status IN (
            'RECORDED', 'PARTIAL', 'COMPLETED', 'EXCEPTION'
        )),
    notes TEXT,

    UNIQUE (receipt_id, shipment_id),

    FOREIGN KEY (shipment_id)
        REFERENCES shipments(shipment_id)
);

-- 4. Quantities recorded against received shipment lines
CREATE TABLE IF NOT EXISTS warehouse_receipt_lines (
    receipt_line_id TEXT PRIMARY KEY,
    receipt_id TEXT NOT NULL,
    shipment_id TEXT NOT NULL,
    shipment_line_id TEXT NOT NULL,
    received_qty REAL NOT NULL CHECK (received_qty >= 0),
    accepted_qty REAL NOT NULL CHECK (accepted_qty >= 0),
    rejected_qty REAL NOT NULL CHECK (rejected_qty >= 0),
    damaged_qty REAL NOT NULL CHECK (damaged_qty >= 0),

    CHECK (accepted_qty + rejected_qty <= received_qty),
    CHECK (damaged_qty <= rejected_qty),

    FOREIGN KEY (receipt_id, shipment_id)
        REFERENCES warehouse_receipts(receipt_id, shipment_id),

    FOREIGN KEY (shipment_line_id, shipment_id)
        REFERENCES shipment_lines(shipment_line_id, shipment_id)
);

CREATE INDEX IF NOT EXISTS idx_shipments_po
    ON shipments(po_id);

CREATE INDEX IF NOT EXISTS idx_shipments_status
    ON shipments(status);

CREATE INDEX IF NOT EXISTS idx_shipment_lines_po_line
    ON shipment_lines(po_line_id);

CREATE INDEX IF NOT EXISTS idx_receipts_shipment
    ON warehouse_receipts(shipment_id);

CREATE INDEX IF NOT EXISTS idx_receipt_lines_shipment_line
    ON warehouse_receipt_lines(shipment_line_id);
