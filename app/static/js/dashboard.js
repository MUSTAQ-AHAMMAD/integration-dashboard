/* ── Dashboard real-time logic ────────────────────────────────────── */
"use strict";

const REFRESH_MS = (window.REFRESH_INTERVAL || 30) * 1000;

// Chart instances (created once, updated on each refresh)
let pieChart = null;
let barChart = null;

// ── Helpers ─────────────────────────────────────────────────────────
function statusBadge(status) {
  const s = (status || "unknown").toLowerCase();
  const cls = "badge badge-" + s;
  return '<span class="badge ' + cls + '">' + escapeHtml(status) + "</span>";
}

function escapeHtml(text) {
  if (text === null || text === undefined) return "";
  const d = document.createElement("div");
  d.appendChild(document.createTextNode(String(text)));
  return d.innerHTML;
}

function formatDate(val) {
  if (!val) return "–";
  const d = new Date(val);
  if (isNaN(d.getTime())) return escapeHtml(String(val));
  return d.toLocaleString();
}

// ── KPI Cards ───────────────────────────────────────────────────────
async function refreshKPIs() {
  try {
    const res = await fetch("/api/kpis");
    const data = await res.json();
    document.getElementById("kpi-total").textContent = data.total ?? "–";
    document.getElementById("kpi-running").textContent = data.running ?? "–";
    document.getElementById("kpi-stopped").textContent = data.stopped ?? "–";
    document.getElementById("kpi-error").textContent = data.error ?? "–";
  } catch {
    /* network error – keep previous values */
  }
}

// ── Pie Chart (Overall Status) ──────────────────────────────────────
async function refreshPieChart() {
  try {
    const res = await fetch("/api/kpis");
    const data = await res.json();

    const labels = ["Running", "Stopped", "Error"];
    const values = [data.running || 0, data.stopped || 0, data.error || 0];
    const colors = ["#198754", "#ffc107", "#dc3545"];

    if (!pieChart) {
      const ctx = document.getElementById("statusPieChart").getContext("2d");
      pieChart = new Chart(ctx, {
        type: "doughnut",
        data: {
          labels: labels,
          datasets: [{ data: values, backgroundColor: colors }],
        },
        options: {
          responsive: true,
          maintainAspectRatio: false,
          plugins: { legend: { position: "bottom" } },
        },
      });
    } else {
      pieChart.data.datasets[0].data = values;
      pieChart.update();
    }
  } catch {
    /* keep chart as-is */
  }
}

// ── Bar Chart (Region-wise) ─────────────────────────────────────────
async function refreshBarChart() {
  try {
    const res = await fetch("/api/region-summary");
    const rows = await res.json();

    const labels = rows.map((r) => r.region || "Unknown");
    const running = rows.map((r) => r.running || 0);
    const stopped = rows.map((r) => r.stopped || 0);
    const errors = rows.map((r) => r.error || 0);

    if (!barChart) {
      const ctx = document.getElementById("regionBarChart").getContext("2d");
      barChart = new Chart(ctx, {
        type: "bar",
        data: {
          labels: labels,
          datasets: [
            { label: "Running", data: running, backgroundColor: "#198754" },
            { label: "Stopped", data: stopped, backgroundColor: "#ffc107" },
            { label: "Error", data: errors, backgroundColor: "#dc3545" },
          ],
        },
        options: {
          responsive: true,
          maintainAspectRatio: false,
          scales: {
            x: { stacked: true },
            y: { stacked: true, beginAtZero: true, ticks: { stepSize: 1 } },
          },
          plugins: { legend: { position: "bottom" } },
        },
      });
    } else {
      barChart.data.labels = labels;
      barChart.data.datasets[0].data = running;
      barChart.data.datasets[1].data = stopped;
      barChart.data.datasets[2].data = errors;
      barChart.update();
    }
  } catch {
    /* keep chart as-is */
  }
}

// ── Table Error Summary ─────────────────────────────────────────────
async function refreshTableErrors() {
  try {
    const res = await fetch("/api/table-errors");
    const tables = await res.json();
    const tbody = document.querySelector("#table-error-summary tbody");
    tbody.innerHTML = "";

    tables.forEach((t) => {
      const tr = document.createElement("tr");
      const badges = t.status_counts
        .map(
          (sc) =>
            '<span class="badge badge-' +
            escapeHtml((sc.status || "unknown").toLowerCase()) +
            ' me-1">' +
            escapeHtml(sc.status) +
            ": " +
            sc.count +
            "</span>"
        )
        .join("");
      tr.innerHTML =
        "<td><strong>" +
        escapeHtml(t.table) +
        "</strong></td><td>" +
        (badges || '<span class="text-muted">No data</span>') +
        "</td>";
      tbody.appendChild(tr);
    });
  } catch {
    /* retain previous data */
  }
}

// ── Integration Status Detail ───────────────────────────────────────
async function refreshIntegrationStatus() {
  try {
    const res = await fetch("/api/integration-status");
    const rows = await res.json();

    document.getElementById("status-count").textContent = rows.length + " integrations";

    const tbody = document.querySelector("#integration-status-table tbody");
    tbody.innerHTML = "";

    rows.forEach((r) => {
      const tr = document.createElement("tr");
      tr.innerHTML =
        "<td>" +
        escapeHtml(r.region) +
        "</td>" +
        "<td>" +
        escapeHtml(r.integration_name) +
        "</td>" +
        "<td>" +
        statusBadge(r.status) +
        "</td>" +
        "<td>" +
        formatDate(r.last_run_time) +
        "</td>" +
        '<td class="error-message-cell" title="' +
        escapeHtml(r.error_message) +
        '">' +
        escapeHtml(r.error_message || "–") +
        "</td>" +
        "<td>" +
        formatDate(r.updated_at) +
        "</td>";
      tbody.appendChild(tr);
    });
  } catch {
    /* retain previous data */
  }
}

// ── Orchestrator ────────────────────────────────────────────────────
async function refreshAll() {
  document.getElementById("last-updated").textContent = "Refreshing…";
  document.getElementById("last-updated").classList.add("refreshing");

  await Promise.all([
    refreshKPIs(),
    refreshPieChart(),
    refreshBarChart(),
    refreshTableErrors(),
    refreshIntegrationStatus(),
  ]);

  document.getElementById("last-updated").textContent =
    "Last updated: " + new Date().toLocaleTimeString();
  document.getElementById("last-updated").classList.remove("refreshing");
}

// Run on load, then auto-refresh
document.addEventListener("DOMContentLoaded", () => {
  refreshAll();
  setInterval(refreshAll, REFRESH_MS);
});
