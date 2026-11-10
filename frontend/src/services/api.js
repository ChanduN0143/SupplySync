
import axios from "axios";

const api = axios.create({
  baseURL: "http://127.0.0.1:8000",
  timeout: 15000,
  headers: {
    "Content-Type": "application/json",
  },
});

export const getDashboardData = async () => {
  const endpoints = [
    { name: "Summary", url: "/api/summary", fallback: {} },
    { name: "Orders", url: "/api/orders?limit=100", fallback: [] },
    { name: "Change requests", url: "/api/change-requests?limit=100", fallback: [] },
    { name: "Anomalies", url: "/api/anomalies?limit=100", fallback: [] },
    { name: "Audit events", url: "/api/audit-events?limit=100", fallback: [] },
    { name: "Suppliers", url: "/api/suppliers?limit=100", fallback: [] },
    { name: "Acknowledgements", url: "/api/acknowledgements?limit=100", fallback: [] },
    { name: "Promise dates", url: "/api/promise-dates?limit=100", fallback: [] },
    { name: "Approvals", url: "/api/approvals?limit=100", fallback: [] },
    { name: "Inventory plans", url: "/api/inventory-plans?limit=100", fallback: [] },
    { name: "Production orders", url: "/api/production-orders?limit=100", fallback: [] },
  ];

  const results = await Promise.allSettled(
    endpoints.map((endpoint) => api.get(endpoint.url))
  );

  const read = (index) =>
    results[index].status === "fulfilled"
      ? results[index].value.data
      : endpoints[index].fallback;

  return {
    summary: read(0),
    orders: read(1),
    changes: read(2),
    anomalies: read(3),
    audit: read(4),
    suppliers: read(5),
    acknowledgements: read(6),
    promises: read(7),
    approvals: read(8),
    inventoryPlans: read(9),
    productionOrders: read(10),
    errors: results
      .map((result, index) =>
        result.status === "rejected"
          ? `${endpoints[index].name}: ${result.reason?.message || "Failed"}`
          : null
      )
      .filter(Boolean),
  };
};

export default api;
