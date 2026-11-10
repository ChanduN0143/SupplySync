async function api(path, options = {}) {
    const response = await fetch(path, {
        headers: { "Content-Type": "application/json" },
        ...options
    });

    const data = await response.json();

    if (!response.ok) {
        throw new Error(data.error || "Request failed");
    }

    return data;
}

function formatNumber(value) {
    return Number(value || 0).toLocaleString("en-IN");
}

function escapeHTML(value) {
    return String(value ?? "").replace(/[&<>"']/g, char => ({
        "&": "&amp;",
        "<": "&lt;",
        ">": "&gt;",
        '"': "&quot;",
        "'": "&#39;"
    })[char]);
}

async function loadSummary() {
    const data = await api("/api/summary");
    const counts = data.counts;

    document.getElementById("purchase-orders").textContent =
        formatNumber(counts.purchase_orders);

    document.getElementById("suppliers").textContent =
        formatNumber(counts.suppliers);

    document.getElementById("pending").textContent =
        formatNumber(data.pending_changes);

    document.getElementById("approved").textContent =
        formatNumber(data.approved_changes);

    document.getElementById("rejected").textContent =
        formatNumber(data.rejected_changes);

    document.getElementById("audit-count").textContent =
        formatNumber(counts.audit_events);
}

async function loadChanges() {
    const rows = await api("/api/changes");
    const body = document.getElementById("changes-body");

    if (!rows.length) {
        body.innerHTML = `<tr><td colspan="7">No change requests found.</td></tr>`;
        return;
    }

    body.innerHTML = rows.map(row => {
        const status = escapeHTML(row.status);
        const actions = row.status === "PENDING"
            ? `<button class="approve" onclick="decide('${escapeHTML(row.change_id)}','APPROVED')">Approve</button>
               <button class="reject" onclick="decide('${escapeHTML(row.change_id)}','REJECTED')">Reject</button>`
            : `<span class="muted">Processed</span>`;

        return `
            <tr>
                <td>${escapeHTML(row.change_id)}</td>
                <td>${escapeHTML(row.supplier_name)}</td>
                <td>${escapeHTML(row.po_id)}<br>${escapeHTML(row.po_line_id)}</td>
                <td>${escapeHTML(row.old_qty)} → ${escapeHTML(row.new_qty)}</td>
                <td>${escapeHTML(row.old_price)} → ${escapeHTML(row.new_price)}</td>
                <td><span class="status ${status}">${status}</span></td>
                <td>${actions}</td>
            </tr>
        `;
    }).join("");
}

async function decide(changeId, decision) {
    const message = decision === "APPROVED"
        ? "Approve this change? The inventory plan will be updated."
        : "Reject this change? The inventory plan will remain unchanged.";

    if (!confirm(message)) return;

    try {
        await api(`/api/changes/${encodeURIComponent(changeId)}/decision`, {
            method: "POST",
            body: JSON.stringify({ decision })
        });

        alert(`Change ${decision.toLowerCase()} successfully.`);
        await loadDashboard();
    } catch (error) {
        alert(error.message);
    }
}

async function loadAnomalies() {
    const rows = await api("/api/anomalies");

    document.getElementById("anomaly-count").textContent =
        `${rows.length} detected`;

    const container = document.getElementById("anomaly-list");

    if (!rows.length) {
        container.innerHTML = `<div class="anomaly">No anomalies detected.</div>`;
        return;
    }

    container.innerHTML = rows.map(row => `
        <article class="anomaly">
            <strong>${escapeHTML(row.type)}</strong>
            <p>${escapeHTML(row.description)}</p>
            <p>Entity: ${escapeHTML(row.entity_id)} · Severity: ${escapeHTML(row.severity)}</p>
        </article>
    `).join("");
}

async function loadOrders() {
    const rows = await api("/api/orders");
    const body = document.getElementById("orders-body");

    body.innerHTML = rows.map(row => `
        <tr>
            <td>${escapeHTML(row.po_id)}</td>
            <td>${escapeHTML(row.supplier_name)}</td>
            <td>${escapeHTML(row.order_date)}</td>
            <td>${formatNumber(row.line_count)}</td>
            <td>${formatNumber(row.requested_quantity)}</td>
            <td>${escapeHTML(row.status)}</td>
        </tr>
    `).join("");
}

async function loadAudit() {
    const rows = await api("/api/audit");
    const container = document.getElementById("audit-list");

    container.innerHTML = rows.map(row => `
        <article class="audit-item">
            <strong>${escapeHTML(row.event_type)} · ${escapeHTML(row.entity_type)}</strong>
            <p>Entity: ${escapeHTML(row.entity_id)} · Actor: ${escapeHTML(row.actor)}</p>
            <p>${escapeHTML(row.created_at)}</p>
        </article>
    `).join("");
}

async function loadDashboard() {
    try {
        await Promise.all([
            loadSummary(),
            loadChanges(),
            loadAnomalies(),
            loadOrders(),
            loadAudit()
        ]);
    } catch (error) {
        console.error(error);
        alert("Could not load the dashboard: " + error.message);
    }
}

loadDashboard();