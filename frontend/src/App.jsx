
import { useEffect, useMemo, useState } from "react";
import {
  Activity,
  AlertTriangle,
  ArrowDownRight,
  ArrowUpRight,
  Bell,
  Boxes,
  CalendarDays,
  CheckCircle2,
  ChevronDown,
  ClipboardList,
  Clock3,
  FileText,
  LayoutDashboard,
  Menu,
  Package,
  RefreshCw,
  Search,
  Settings,
  ShieldAlert,
  Truck,
  Users,
  X,
} from "lucide-react";
import {
  Area,
  AreaChart,
  CartesianGrid,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { getDashboardData } from "./services/api";
import "./App.css";

const navigation = [
  { name: "Dashboard", icon: LayoutDashboard },
  { name: "Purchase Orders", icon: Package },
  { name: "Suppliers", icon: Users },
  { name: "Acknowledgements", icon: ClipboardList },
  { name: "Promise Dates", icon: CalendarDays },
  { name: "Change Requests", icon: RefreshCw },
  { name: "Approval Center", icon: CheckCircle2 },
  { name: "Inventory Planning", icon: Boxes },
  { name: "Production Schedule", icon: Truck },
  { name: "Anomaly Detection", icon: ShieldAlert },
  { name: "Audit Logs", icon: FileText },
];

function getArray(data, possibleKeys = []) {
  if (Array.isArray(data)) return data;
  if (!data || typeof data !== "object") return [];

  for (const key of possibleKeys) {
    if (Array.isArray(data[key])) return data[key];
  }

  const firstArray = Object.values(data).find(Array.isArray);
  return firstArray || [];
}

function getCount(summary, key) {
  const value = summary?.[key];

  if (typeof value === "number") return value;
  if (typeof value === "string" && value.trim() !== "") {
    const number = Number(value);
    return Number.isFinite(number) ? number : 0;
  }
  if (value && typeof value === "object") {
    return Number(value.total ?? value.count ?? 0);
  }

  return 0;
}

function formatNumber(value) {
  return Number(value || 0).toLocaleString("en-IN");
}

function getValue(item, keys, fallback = "—") {
  for (const key of keys) {
    const value = item?.[key];
    if (value !== undefined && value !== null && value !== "") {
      return value;
    }
  }
  return fallback;
}

function StatusBadge({ status }) {
  const value = String(status || "UNKNOWN").toUpperCase();
  let className = "status-neutral";

  if (["APPROVED", "COMPLETED", "ACTIVE", "ACKNOWLEDGED"].includes(value)) {
    className = "status-success";
  } else if (["PENDING", "OPEN", "PARTIAL", "IN_PROGRESS"].includes(value)) {
    className = "status-warning";
  } else if (["REJECTED", "CANCELLED", "CRITICAL", "FAILED"].includes(value)) {
    className = "status-danger";
  }

  return <span className={`status-badge ${className}`}>{value.replaceAll("_", " ")}</span>;
}

function MetricCard({ title, value, subtitle, icon: Icon, color, trend }) {
  return (
    <div className="metric-card">
      <div className="metric-top">
        <span className="metric-title">{title}</span>
        <span className={`metric-icon ${color}`}><Icon size={19} /></span>
      </div>
      <div className="metric-value">{formatNumber(value)}</div>
      <div className="metric-bottom">
        <span className="metric-subtitle">{subtitle}</span>
        {trend && <span className="metric-trend"><ArrowUpRight size={14} /> Live</span>}
      </div>
    </div>
  );
}

function EmptyState({ message }) {
  return <div className="empty-state">{message}</div>;
}

function Dashboard({ data, loading, onRefresh }) {
  const summary = data.summary || {};
const counts = summary.counts || {};
const changeStatus = summary.change_status || {};

  const metrics = [
  {
    title: "Total Suppliers",
    value: getCount(counts, "suppliers"),
    subtitle: "Registered suppliers",
    icon: Users,
    color: "purple",
  },
  {
    title: "Purchase Orders",
    value: getCount(counts, "purchase_orders"),
    subtitle: "Total purchase orders",
    icon: Package,
    color: "blue",
    trend: true,
  },
  {
    title: "Pending Changes",
    value: getCount(changeStatus, "pending"),
    subtitle: "Awaiting decisions",
    icon: Clock3,
    color: "orange",
  },
  {
    title: "Anomaly Cases",
    value: getCount(counts, "anomaly_cases"),
    subtitle: "Detected exceptions",
    icon: AlertTriangle,
    color: "red",
  },
];

  const orders = getArray(data.orders, ["orders", "items", "results", "data"]);
  const changes = getArray(data.changes, ["changes", "items", "results", "data"]);
  const anomalies = getArray(data.anomalies, ["anomalies", "items", "results", "data"]);
  const audit = getArray(data.audit, ["audit", "events", "items", "results", "data"]);

  const statusData = [
  { name: "Pending", value: getCount(changeStatus, "pending") },
  { name: "Approved", value: getCount(changeStatus, "approved") },
  { name: "Rejected", value: getCount(changeStatus, "rejected") },
];

  const chartData = [
    { day: "Mon", orders: 0 },
    { day: "Tue", orders: 0 },
    { day: "Wed", orders: 0 },
    { day: "Thu", orders: 0 },
    { day: "Fri", orders: 0 },
    { day: "Sat", orders: 0 },
    { day: "Sun", orders: 0 },
  ];

  return (
    <>
      <div className="page-heading">
        <div>
          <p className="eyebrow">OVERVIEW</p>
          <h1>Supply Chain Dashboard</h1>
          <p className="page-description">
            Monitor supplier performance, purchase orders and operational exceptions.
          </p>
        </div>
        <button className="refresh-button" onClick={onRefresh} disabled={loading}>
          <RefreshCw size={16} className={loading ? "spin" : ""} />
          Refresh
        </button>
      </div>

      {data.errors?.length > 0 && (
        <div className="warning-banner">
          <AlertTriangle size={18} />
          Some API requests failed. Check that your backend is running and review the browser console.
        </div>
      )}

      <div className="metrics-grid">
        {metrics.map((metric) => <MetricCard key={metric.title} {...metric} />)}
      </div>

      <div className="section-grid">
        <section className="panel chart-panel">
          <div className="panel-heading">
            <div>
              <h2>Change Request Overview</h2>
              <p>Current request status distribution</p>
            </div>
            <span className="panel-icon"><Activity size={18} /></span>
          </div>

          <div className="status-overview">
            {statusData.map((item, index) => (
              <div className="status-stat" key={item.name}>
                <span className={`status-dot dot-${index}`} />
                <div>
                  <span className="status-stat-label">{item.name}</span>
                  <strong>{formatNumber(item.value)}</strong>
                </div>
              </div>
            ))}
          </div>

          <div className="chart-container">
            <ResponsiveContainer width="100%" height="100%">
              <AreaChart data={chartData}>
                <defs>
                  <linearGradient id="orderGradient" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%" stopColor="#6487f5" stopOpacity={0.25} />
                    <stop offset="95%" stopColor="#6487f5" stopOpacity={0} />
                  </linearGradient>
                </defs>
                <CartesianGrid stroke="#263247" strokeDasharray="4 4" vertical={false} />
                <XAxis dataKey="day" stroke="#8490a5" tickLine={false} axisLine={false} />
                <YAxis stroke="#8490a5" tickLine={false} axisLine={false} />
                <Tooltip contentStyle={{ background: "#151f30", border: "1px solid #344158", borderRadius: 8 }} />
                <Area type="monotone" dataKey="orders" stroke="#6487f5" fill="url(#orderGradient)" strokeWidth={2} />
              </AreaChart>
            </ResponsiveContainer>
          </div>
          <p className="chart-note">Daily order history will appear when historical reporting data is available.</p>
        </section>

        <section className="panel">
          <div className="panel-heading">
            <div>
              <h2>Operational Summary</h2>
              <p>Database record counts</p>
            </div>
            <span className="panel-icon"><Boxes size={18} /></span>
          </div>
          <div className="summary-list">
            {[
              ["PO Lines", "po_lines"],
              ["Acknowledgements", "acknowledgements"],
              ["Promise Dates", "promise_dates"],
              ["Inventory Plans", "inventory_plans"],
              ["Production Orders", "production_orders"],
              ["Notifications", "notifications"],
              ["Audit Events", "audit_events"],
            ].map(([label, key]) => (
              <div className="summary-row" key={key}>
                <span>{label}</span>
                <strong>{formatNumber(getCount(counts, key))}</strong>
              </div>
            ))}
          </div>
        </section>
      </div>

      <section className="panel table-panel">
        <div className="panel-heading">
          <div>
            <h2>Recent Purchase Orders</h2>
            <p>Latest purchase order records from your database</p>
          </div>
          <span className="view-label">{orders.length} records loaded</span>
        </div>

        {orders.length === 0 ? (
          <EmptyState message="No purchase order records returned by the API." />
        ) : (
          <div className="table-scroll">
            <table>
              <thead>
                <tr>
                  <th>PO NUMBER</th>
                  <th>SUPPLIER</th>
                  <th>ORDER DATE</th>
                  <th>QUANTITY</th>
                  <th>STATUS</th>
                </tr>
              </thead>
              <tbody>
                {orders.slice(0, 8).map((order, index) => (
                  <tr key={order.id || order.po_number || index}>
                    <td className="primary-cell">{getValue(order, ["po_number", "po_id", "order_number", "id"])}</td>
                    <td>{getValue(order, ["supplier_name", "supplier", "vendor_name"])}</td>
                    <td>{getValue(order, ["order_date", "created_at", "date"])}</td>
                    <td>{formatNumber(getValue(order, ["requested_quantity", "quantity", "total_quantity"], 0))}</td>
                    <td><StatusBadge status={getValue(order, ["status", "po_status"])} /></td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </section>

      <div className="section-grid lower-grid">
        <section className="panel">
          <div className="panel-heading">
            <div>
              <h2>Recent Change Requests</h2>
              <p>Supplier updates requiring attention</p>
            </div>
            <RefreshCw size={18} className="muted-icon" />
          </div>
          {changes.length === 0 ? <EmptyState message="No change requests returned." /> : (
            <div className="activity-list">
              {changes.slice(0, 6).map((item, index) => (
                <div className="activity-item" key={item.id || item.change_id || index}>
                  <span className="activity-symbol orange-symbol"><RefreshCw size={15} /></span>
                  <div className="activity-content">
                    <strong>{getValue(item, ["change_id", "request_id", "id"], "Change request")}</strong>
                    <span>{getValue(item, ["change_type", "description", "reason"], "Supplier change submitted")}</span>
                  </div>
                  <StatusBadge status={getValue(item, ["status"])} />
                </div>
              ))}
            </div>
          )}
        </section>

        <section className="panel">
          <div className="panel-heading">
            <div>
              <h2>Anomaly Detection</h2>
              <p>Potential data and process exceptions</p>
            </div>
            <ShieldAlert size={18} className="muted-icon" />
          </div>
          {anomalies.length === 0 ? <EmptyState message="No anomaly records returned." /> : (
            <div className="activity-list">
              {anomalies.slice(0, 6).map((item, index) => (
                <div className="activity-item" key={item.id || item.entity_id || index}>
                  <span className="activity-symbol red-symbol"><AlertTriangle size={15} /></span>
                  <div className="activity-content">
                    <strong>{getValue(item, ["anomaly_type", "type", "rule_name"], "Anomaly")}</strong>
                    <span>{getValue(item, ["entity_id", "description", "message"], "Exception detected")}</span>
                  </div>
                  <StatusBadge status={getValue(item, ["severity", "priority"], "HIGH")} />
                </div>
              ))}
            </div>
          )}
        </section>
      </div>

      <section className="panel audit-panel">
        <div className="panel-heading">
          <div>
            <h2>Recent Audit Activity</h2>
            <p>Traceability of system operations</p>
          </div>
          <FileText size={18} className="muted-icon" />
        </div>
        {audit.length === 0 ? <EmptyState message="No audit events returned." /> : (
          <div className="activity-list">
            {audit.slice(0, 5).map((item, index) => (
              <div className="activity-item" key={item.id || item.event_id || index}>
                <span className="activity-symbol blue-symbol"><FileText size={15} /></span>
                <div className="activity-content">
                  <strong>{getValue(item, ["action", "event_type", "event"], "System event")}</strong>
                  <span>{getValue(item, ["entity_id", "description", "entity_type"], "Audit record")}</span>
                </div>
                <span className="audit-time">{getValue(item, ["created_at", "timestamp", "event_time"])}</span>
              </div>
            ))}
          </div>
        )}
      </section>
    </>
  );
}

function App() {
  const [activePage, setActivePage] = useState("Dashboard");
const [data, setData] = useState({
    summary: {},
    orders: [],
    changes: [],
    anomalies: [],
    audit: [],
    suppliers: [],
    acknowledgements: [],
    promises: [],
    approvals: [],
    inventoryPlans: [],
    productionOrders: [],
    errors: [],
  });

  const [loading, setLoading] = useState(true);
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const [search, setSearch] = useState("");

  const loadData = async () => {
    setLoading(true);
    try {
      const result = await getDashboardData();
      setData(result);
    } catch (error) {
      console.error("SupplySync API error:", error);
      setData((previous) => ({
        ...previous,
        errors: [error.message || "Unable to connect to backend"],
      }));
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadData();
  }, []);

  const pageDescriptions = useMemo(() => ({
    "Purchase Orders": "Monitor purchase orders and their fulfilment status.",
    Suppliers: "View supplier records and supplier-related operations.",
    Acknowledgements: "Review supplier acknowledgement information.",
    "Promise Dates": "Monitor committed delivery dates and changes.",
    "Change Requests": "Review supplier quantity and date change requests.",
    "Approval Center": "Track pending, approved and rejected decisions.",
    "Inventory Planning": "Review inventory plans and material availability.",
    "Production Schedule": "Monitor production orders and schedule impacts.",
    "Anomaly Detection": "Investigate unusual records and process exceptions.",
    "Audit Logs": "Review historical system activity and traceability.",
  }), []);

  const pageRows = useMemo(() => {
    const mapping = {
      "Purchase Orders": getArray(data.orders, ["orders", "items", "results", "data"]),
      "Suppliers": getArray(data.suppliers, ["suppliers", "items", "results", "data"]),
      "Acknowledgements": getArray(data.acknowledgements, ["acknowledgements", "items", "results", "data"]),
      "Promise Dates": getArray(data.promises, ["promises", "items", "results", "data"]),
      "Change Requests": getArray(data.changes, ["changes", "items", "results", "data"]),
      "Approval Center": getArray(data.approvals, ["approvals", "items", "results", "data"]),
      "Inventory Planning": getArray(data.inventoryPlans, ["plans", "items", "results", "data"]),
      "Production Schedule": getArray(data.productionOrders, ["production_orders", "items", "results", "data"]),
      "Anomaly Detection": getArray(data.anomalies, ["anomalies", "items", "results", "data"]),
      "Audit Logs": getArray(data.audit, ["audit", "events", "items", "results", "data"]),
    };

    return mapping[activePage] || [];
  }, [data, activePage]);
  const filteredRows = pageRows.filter((row) =>
    JSON.stringify(row).toLowerCase().includes(search.toLowerCase())
  );

  return (
    <div className="app-shell">
      {sidebarOpen && <button className="mobile-overlay" onClick={() => setSidebarOpen(false)} aria-label="Close menu" />}
      <aside className={`sidebar ${sidebarOpen ? "sidebar-open" : ""}`}>
        <div className="brand">
          <div className="brand-logo"><Boxes size={23} /></div>
          <div>
            <strong>SupplySync</strong>
            <span>SUPPLY CHAIN PLATFORM</span>
          </div>
          <button className="close-sidebar" onClick={() => setSidebarOpen(false)}><X size={19} /></button>
        </div>

        <div className="workspace-label">WORKSPACE</div>
        <nav className="navigation">
          {navigation.map(({ name, icon: Icon }) => (
            <button
              key={name}
              className={`nav-item ${activePage === name ? "nav-active" : ""}`}
              onClick={() => {
                setActivePage(name);
                setSearch("");
                setSidebarOpen(false);
              }}
            >
              <Icon size={18} />
              <span>{name}</span>
              {name === "Anomaly Detection" && data.anomalies?.length > 0 && (
                <span className="nav-count">{getArray(data.anomalies, ["anomalies", "items", "results", "data"]).length}</span>
              )}
            </button>
          ))}
        </nav>

        <div className="sidebar-bottom">
          <button className="nav-item"><Settings size={18} /><span>Settings</span></button>
          <div className="user-profile">
            <div className="avatar">S</div>
            <div className="user-info"><strong>SupplySync Admin</strong><span>Administrator</span></div>
            <ChevronDown size={16} />
          </div>
        </div>
      </aside>

      <main className="main-area">
        <header className="topbar">
          <div className="topbar-left">
            <button className="mobile-menu" onClick={() => setSidebarOpen(true)}><Menu size={21} /></button>
            <div className="breadcrumb">Workspace <span>/</span> <strong>{activePage}</strong></div>
          </div>
          <div className="topbar-right">
            <div className="system-status"><span /> System operational</div>
            <button className="icon-button" aria-label="Notifications"><Bell size={19} /></button>
            <div className="top-avatar">S</div>
          </div>
        </header>

        <div className="content-area">
          {activePage === "Dashboard" ? (
            <Dashboard data={data} loading={loading} onRefresh={loadData} />
          ) : (
            <>
              <div className="page-heading">
                <div>
                  <p className="eyebrow">SUPPLYSYNC MODULE</p>
                  <h1>{activePage}</h1>
                  <p className="page-description">{pageDescriptions[activePage]}</p>
                </div>
                <button className="refresh-button" onClick={loadData} disabled={loading}>
                  <RefreshCw size={16} className={loading ? "spin" : ""} /> Refresh
                </button>
              </div>


                <section className="panel table-panel">
  <div className="panel-heading">
    <div>
      <h2>{activePage} Records</h2>
      <p>Data loaded from your SupplySync backend</p>
    </div>
    <span className="view-label">{filteredRows.length} records</span>
  </div>

  <div className="search-box">
    <Search size={17} />
    <input
      value={search}
      onChange={(event) => setSearch(event.target.value)}
      placeholder={`Search ${activePage.toLowerCase()}...`}
    />
  </div>

  {filteredRows.length === 0 ? (
    <EmptyState message="No matching records found." />
  ) : (
    <div className="table-scroll">
      <table>
        <thead>
          <tr>
            <th>RECORD</th>
            <th>DETAILS</th>
            <th>STATUS / SEVERITY</th>
          </tr>
        </thead>
        <tbody>
          {filteredRows.map((row, index) => (
            <tr
              key={getValue(
                row,
                [
                  "id",
                  "po_id",
                  "supplier_id",
                  "ack_id",
                  "promise_id",
                  "change_id",
                  "approval_id",
                  "plan_id",
                  "production_id",
                  "event_id",
                  "entity_id",
                ],
                index
              )}
            >
              <td className="primary-cell">
                {getValue(
  row,
activePage === "Acknowledgements"
  ? ["ack_id", "po_id"]
  : activePage === "Promise Dates"
  ? ["promise_id"]
: activePage === "Change Requests"
? ["change_id"]
: activePage === "Approval Center"
? ["approval_id"]
: activePage === "Inventory Planning"
? ["plan_id"]
: activePage === "Production Schedule"
? ["production_id"]
: [
        "event_id",
        "po_id",
        "supplier_id",
        "ack_id",
        "promise_id",
        "change_id",
        "approval_id",
        "plan_id",
        "production_id",
        "entity_id",
        "event_id",
        "po_number",
        "id",
      ]
)}
              </td>

              <td>
  {activePage === "Acknowledgements" ? (
  <div>
    <div>{getValue(row, ["description"])}</div>
    <small>
      PO: {getValue(row, ["po_id"])} ·
      Accepted: {getValue(row, ["accepted_qty"])} ·
      Rejected: {getValue(row, ["rejected_qty"])}
    </small>
    <small>
      Promised: {getValue(row, ["promised_date"])}
    </small>
  </div>
) : activePage === "Promise Dates" ? (
  <div>
    <strong>PO: {getValue(row, ["po_id"])}</strong>
    <small>PO Line: {getValue(row, ["po_line_id"])}</small>
    <small>Acknowledgement: {getValue(row, ["ack_id"])}</small>
    <small>Promised Date: {getValue(row, ["promised_date"])}</small>
    <small>
      Accepted: {getValue(row, ["accepted_qty"])} ·
      Rejected: {getValue(row, ["rejected_qty"])}
    </small>
  </div>
) : activePage === "Audit Logs" ? (
  <div>
    <strong>{getValue(row, ["event_type"])}</strong>
    <div>
      {getValue(row, ["entity_type"])} · {getValue(row, ["actor"])}
    </div>
    <small>{getValue(row, ["created_at"])}</small>
  </div>
) : activePage === "Change Requests" ? (

  <div>
    <strong>PO: {getValue(row, ["po_id"])}</strong>
    <small>PO Line: {getValue(row, ["po_line_id"])}</small>
    <small>Change Type: {getValue(row, ["change_type"])}</small>
    <small>
      Quantity: {getValue(row, ["old_qty"])} → {getValue(row, ["new_qty"])}
    </small>
    <small>
      Price: {getValue(row, ["old_price"])} → {getValue(row, ["new_price"])}
    </small>
    <small>
      Date: {getValue(row, ["old_date"])} → {getValue(row, ["new_date"])}
    </small>
    <small>Reason: {getValue(row, ["reason"])}</small>
  </div>
) : activePage === "Approval Center" ? (
  <div>
    <strong>PO: {getValue(row, ["po_id"])}</strong>
    <small>Change ID: {getValue(row, ["change_id"])}</small>
    <small>PO Line: {getValue(row, ["po_line_id"])}</small>
    <small>Change Type: {getValue(row, ["change_type"])}</small>
    <small>
      Quantity: {getValue(row, ["old_qty"])} → {getValue(row, ["new_qty"])}
    </small>
    <small>
      Date: {getValue(row, ["old_date"])} → {getValue(row, ["new_date"])}
    </small>
    <small>Approver: {getValue(row, ["approver_role"])}</small>
    <small>Comments: {getValue(row, ["comments"])}</small>
    <small>Decided At: {getValue(row, ["decided_at"])}</small>
  </div>
) : activePage === "Inventory Planning" ? (
  <div>
    <strong>PO: {getValue(row, ["po_id"])}</strong>
    <small>PO Line: {getValue(row, ["po_line_id"])}</small>
    <small>Supplier: {getValue(row, ["supplier_name"])}</small>
    <small>Supplier ID: {getValue(row, ["supplier_id"])}</small>
    <small>Item: {getValue(row, ["item_code"])}</small>
    <small>Description: {getValue(row, ["description"])}</small>
    <small>Projected Quantity: {getValue(row, ["projected_qty"])}</small>
    <small>Projected Date: {getValue(row, ["projected_date"])}</small>
    <small>Last Change: {getValue(row, ["last_change_id"], "—")}</small>
    <small>Updated At: {getValue(row, ["updated_at"])}</small>
  </div>
) : activePage === "Production Schedule" ? (
  <div>
    <strong>PO: {getValue(row, ["po_id"])}</strong>
    <small>PO Line: {getValue(row, ["po_line_id"])}</small>
    <small>Inventory Plan: {getValue(row, ["plan_id"])}</small>
    <small>Supplier: {getValue(row, ["supplier_name"])}</small>
    <small>Required Quantity: {getValue(row, ["required_qty"])}</small>
    <small>Required Date: {getValue(row, ["required_date"])}</small>
    <small>Projected Quantity: {getValue(row, ["projected_qty"])}</small>
    <small>Projected Date: {getValue(row, ["projected_date"])}</small>
  </div>
) : (
  getValue(
    row,
    [
      "supplier_name",
      "description",
      "item_code",
      "change_type",
      "approver_role",
      "comments",
      "reason",
      "action",
      "event_type",
      "type",
      "email",
    ]
  )
)}
</td>
              <td>
                <StatusBadge
  status={
    activePage === "Audit Logs"
      ? getValue(row, ["event_type"], "RECORDED")
 : activePage === "Promise Dates"
  ? getValue(row, ["acknowledgement_status"], "UNKNOWN")
  : getValue(
      row,
      [
        "status",
        "decision",
        "change_status",
        "acknowledgement_status",
        "severity",
        "priority",
      ],
      "RECORDED"
    )
  }
/>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )}
</section>
 </>
          )}




          <footer className="footer">
            <span>© 2026 SupplySync. Supply chain visibility platform.</span>
            <span>Connected to SupplySync API <span className="footer-dot" /></span>
          </footer>
        </div>
      </main>
    </div>
  );
}

export default App;
