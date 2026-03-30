/* ══════════════════════════════════════════════════════════════════════
   Integration Command Center – Modern Dashboard Logic
   ══════════════════════════════════════════════════════════════════════ */
"use strict";

/* Chart instances (created once, updated on each refresh) */
let pieChart = null;
let barChart = null;

/* Track whether this is the first data load */
let isFirstLoad = true;

/* Store all integration rows for client-side filtering */
let integrationRows = [];

/* ── Dark-theme Chart.js defaults ─────────────────────────────────── */
Chart.defaults.color = "#475569";
Chart.defaults.borderColor = "rgba(0,0,0,0.06)";
Chart.defaults.font.family = "'Inter', system-ui, sans-serif";

/* Respect prefers-reduced-motion for chart animations */
var prefersReducedMotion = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
var chartAnimationDuration = prefersReducedMotion ? 0 : 800;

/* ── Helpers ──────────────────────────────────────────────────────── */
function statusBadge(status) {
  var s = (status || "unknown").toLowerCase();
  return '<span class="status-badge status-badge-' + s + '">' + escapeHtml(status) + "</span>";
}

function tablePill(status, count) {
  var s = (status || "unknown").toLowerCase();
  return '<span class="table-pill table-pill-' + s + '">' +
    escapeHtml(status) + ": " + count + "</span>";
}

function escapeHtml(text) {
  if (text === null || text === undefined) return "";
  var d = document.createElement("div");
  d.appendChild(document.createTextNode(String(text)));
  return d.innerHTML;
}

function formatDate(val) {
  if (!val) return '<span style="color:#94a3b8">&ndash;</span>';
  var d = new Date(val);
  if (isNaN(d.getTime())) return escapeHtml(String(val));
  return d.toLocaleString();
}

/* Animate a number counting up */
function animateValue(el, target) {
  var current = parseInt(el.textContent, 10);
  if (isNaN(current)) current = 0;
  if (current === target) return;
  var diff = target - current;
  var steps = Math.min(Math.abs(diff), 20);
  var stepMs = 300 / steps;
  var i = 0;
  function tick() {
    i++;
    el.textContent = Math.round(current + (diff * i) / steps);
    if (i < steps) setTimeout(tick, stepMs);
  }
  tick();
}

/* Remove skeleton placeholders from a container */
function removeSkeletons(containerId) {
  var container = document.getElementById(containerId);
  if (!container) return;
  var skeletons = container.querySelectorAll(".skeleton-placeholder, [id$='-skeleton']");
  skeletons.forEach(function(el) { el.remove(); });
}

/* Show hidden canvas elements */
function showCanvas(canvasId) {
  var canvas = document.getElementById(canvasId);
  if (canvas) canvas.style.display = "";
}

/* ── Toast Notifications ─────────────────────────────────────────── */
function showToast(message, type) {
  type = type || "info";
  var container = document.getElementById("toast-container");
  if (!container) return;

  var icons = {
    success: "bi-check-circle-fill",
    error: "bi-exclamation-circle-fill",
    info: "bi-info-circle-fill",
  };

  var toast = document.createElement("div");
  toast.className = "toast-item toast-" + type;
  toast.innerHTML = '<i class="bi ' + (icons[type] || icons.info) + '"></i>' + escapeHtml(message);
  container.appendChild(toast);

  setTimeout(function() {
    toast.classList.add("toast-out");
    setTimeout(function() { toast.remove(); }, 300);
  }, 3000);
}

/* ── KPI Cards ───────────────────────────────────────────────────── */
async function refreshKPIs() {
  try {
    var res = await fetch("/api/kpis");
    if (!res.ok) {
      var err = await res.json();
      showToast(err.error || "Failed to load KPIs", "error");
      return;
    }
    var data = await res.json();
    animateValue(document.getElementById("kpi-total"), data.total ?? 0);
    animateValue(document.getElementById("kpi-running"), data.running ?? 0);
    animateValue(document.getElementById("kpi-stopped"), data.stopped ?? 0);
    animateValue(document.getElementById("kpi-error"), data.error ?? 0);
  } catch (e) {
    showToast("Network error: unable to load KPIs", "error");
  }
}

/* ── Pie / Doughnut Chart (Overall Status) ───────────────────────── */
async function refreshPieChart() {
  try {
    var res = await fetch("/api/kpis");
    if (!res.ok) {
      showToast("Failed to load status chart", "error");
      return;
    }
    var data = await res.json();

    var labels = ["Running", "Stopped", "Error"];
    var values = [data.running || 0, data.stopped || 0, data.error || 0];
    var colors = ["#10b981", "#f59e0b", "#ef4444"];
    var hoverColors = ["#34d399", "#fbbf24", "#f87171"];

    if (!pieChart) {
      removeSkeletons("pie-chart-container");
      showCanvas("statusPieChart");
      var ctx = document.getElementById("statusPieChart").getContext("2d");
      pieChart = new Chart(ctx, {
        type: "doughnut",
        data: {
          labels: labels,
          datasets: [{
            data: values,
            backgroundColor: colors,
            hoverBackgroundColor: hoverColors,
            borderWidth: 0,
            hoverOffset: 8,
          }],
        },
        options: {
          responsive: true,
          maintainAspectRatio: false,
          cutout: "72%",
          animation: { animateRotate: true, animateScale: true, duration: chartAnimationDuration },
          plugins: {
            legend: {
              position: "bottom",
              labels: {
                padding: 20,
                usePointStyle: true,
                pointStyleWidth: 12,
                font: { size: 12, weight: "500" },
              },
            },
            tooltip: {
              backgroundColor: "#ffffff",
              titleColor: "#1e293b",
              bodyColor: "#475569",
              borderColor: "rgba(0,0,0,0.1)",
              borderWidth: 1,
              cornerRadius: 10,
              padding: 14,
              displayColors: true,
              boxPadding: 6,
            },
          },
        },
      });
    } else {
      pieChart.data.datasets[0].data = values;
      pieChart.update("none");
    }
  } catch (e) {
    /* keep chart as-is on network error */
  }
}

/* ── Bar Chart (Region-wise) ─────────────────────────────────────── */
async function refreshBarChart() {
  try {
    var res = await fetch("/api/region-summary");
    if (!res.ok) {
      var err = await res.json();
      showToast(err.error || "Failed to load region summary", "error");
      return;
    }
    var rows = await res.json();

    var labels = rows.map(function(r) { return r.region || "Unknown"; });
    var running = rows.map(function(r) { return r.running || 0; });
    var stopped = rows.map(function(r) { return r.stopped || 0; });
    var errors = rows.map(function(r) { return r.error || 0; });

    if (!barChart) {
      removeSkeletons("bar-chart-container");
      showCanvas("regionBarChart");
      var ctx = document.getElementById("regionBarChart").getContext("2d");
      barChart = new Chart(ctx, {
        type: "bar",
        data: {
          labels: labels,
          datasets: [
            {
              label: "Running",
              data: running,
              backgroundColor: "rgba(16, 185, 129, 0.75)",
              hoverBackgroundColor: "#10b981",
              borderRadius: 6,
              borderSkipped: false,
            },
            {
              label: "Stopped",
              data: stopped,
              backgroundColor: "rgba(245, 158, 11, 0.75)",
              hoverBackgroundColor: "#f59e0b",
              borderRadius: 6,
              borderSkipped: false,
            },
            {
              label: "Error",
              data: errors,
              backgroundColor: "rgba(239, 68, 68, 0.75)",
              hoverBackgroundColor: "#ef4444",
              borderRadius: 6,
              borderSkipped: false,
            },
          ],
        },
        options: {
          responsive: true,
          maintainAspectRatio: false,
          animation: { duration: chartAnimationDuration, easing: "easeOutQuart" },
          scales: {
            x: {
              stacked: true,
              grid: { display: false },
              ticks: { font: { size: 12, weight: "500" } },
            },
            y: {
              stacked: true,
              beginAtZero: true,
              ticks: { stepSize: 1, font: { size: 11 } },
              grid: { color: "rgba(0,0,0,0.04)" },
            },
          },
          plugins: {
            legend: {
              position: "bottom",
              labels: {
                padding: 20,
                usePointStyle: true,
                pointStyleWidth: 12,
                font: { size: 12, weight: "500" },
              },
            },
            tooltip: {
              backgroundColor: "#ffffff",
              titleColor: "#1e293b",
              bodyColor: "#475569",
              borderColor: "rgba(0,0,0,0.1)",
              borderWidth: 1,
              cornerRadius: 10,
              padding: 14,
              displayColors: true,
              boxPadding: 6,
            },
          },
        },
      });
    } else {
      barChart.data.labels = labels;
      barChart.data.datasets[0].data = running;
      barChart.data.datasets[1].data = stopped;
      barChart.data.datasets[2].data = errors;
      barChart.update("none");
    }
  } catch (e) {
    showToast("Network error: unable to load region chart", "error");
  }
}

/* ── Table Error Summary ─────────────────────────────────────────── */
async function refreshTableErrors() {
  try {
    var res = await fetch("/api/table-errors");
    if (!res.ok) {
      var err = await res.json();
      var tbody = document.querySelector("#table-error-summary tbody");
      tbody.innerHTML = '<tr><td colspan="2"><div class="table-empty-state"><i class="bi bi-exclamation-triangle"></i>' + escapeHtml(err.error || "Database error") + '</div></td></tr>';
      return;
    }
    var tables = await res.json();
    var tbody = document.querySelector("#table-error-summary tbody");
    tbody.innerHTML = "";

    if (tables.length === 0) {
      tbody.innerHTML = '<tr><td colspan="2"><div class="table-empty-state"><i class="bi bi-inbox"></i>No table data available</div></td></tr>';
      return;
    }

    tables.forEach(function(t) {
      var tr = document.createElement("tr");
      var pills = t.status_counts
        .map(function(sc) { return tablePill(sc.status, sc.count); })
        .join("");
      tr.innerHTML =
        '<td><span class="table-name">' + escapeHtml(t.table) + "</span></td>" +
        "<td>" + (pills || '<span style="color:#94a3b8">No data</span>') + "</td>";
      tbody.appendChild(tr);
    });
  } catch (e) {
    showToast("Network error: unable to load table errors", "error");
  }
}

/* ── Integration Status Detail ───────────────────────────────────── */
async function refreshIntegrationStatus() {
  try {
    var res = await fetch("/api/integration-status");
    if (!res.ok) {
      var err = await res.json();
      var tbody = document.querySelector("#integration-status-table tbody");
      tbody.innerHTML = '<tr><td colspan="6"><div class="table-empty-state"><i class="bi bi-exclamation-triangle"></i>' + escapeHtml(err.error || "Database error") + '</div></td></tr>';
      document.getElementById("status-count").textContent = "";
      return;
    }
    integrationRows = await res.json();
    renderIntegrationTable(integrationRows);
  } catch (e) {
    showToast("Network error: unable to load integration status", "error");
  }
}

/* Render integration table rows, optionally filtered */
function renderIntegrationTable(rows) {
  var searchTerm = (document.getElementById("status-search").value || "").toLowerCase();

  var filtered = rows;
  if (searchTerm) {
    filtered = rows.filter(function(r) {
      return (r.region || "").toLowerCase().indexOf(searchTerm) !== -1 ||
             (r.integration_name || "").toLowerCase().indexOf(searchTerm) !== -1 ||
             (r.status || "").toLowerCase().indexOf(searchTerm) !== -1;
    });
  }

  var countEl = document.getElementById("status-count");
  if (searchTerm && filtered.length !== rows.length) {
    countEl.textContent = filtered.length + " of " + rows.length + " integrations";
  } else {
    countEl.textContent = rows.length + " integrations";
  }

  var tbody = document.querySelector("#integration-status-table tbody");
  tbody.innerHTML = "";

  if (filtered.length === 0) {
    tbody.innerHTML = '<tr><td colspan="6"><div class="table-empty-state"><i class="bi bi-search"></i>No matching integrations found</div></td></tr>';
    return;
  }

  filtered.forEach(function(r) {
    var tr = document.createElement("tr");
    tr.innerHTML =
      "<td>" + escapeHtml(r.region) + "</td>" +
      "<td><strong>" + escapeHtml(r.integration_name) + "</strong></td>" +
      "<td>" + statusBadge(r.status) + "</td>" +
      "<td>" + formatDate(r.last_run_time) + "</td>" +
      '<td class="error-message-cell" title="' +
        escapeHtml(r.error_message) + '">' +
        escapeHtml(r.error_message || "") +
        (!r.error_message ? '<span style="color:#94a3b8">&ndash;</span>' : "") +
      "</td>" +
      "<td>" + formatDate(r.updated_at) + "</td>";
    tbody.appendChild(tr);
  });
}

/* ── Management Report ────────────────────────────────────────────── */
function formatReportDate(val) {
  if (!val) return "";
  var d = new Date(val);
  if (isNaN(d.getTime())) return escapeHtml(String(val));
  var day = d.getDate();
  var months = ["Jan","Feb","Mar","Apr","May","Jun","Jul","Aug","Sep","Oct","Nov","Dec"];
  return day + "-" + months[d.getMonth()];
}

function buildReportTable(itype, rows, reportDate) {
  var headerClass = "report-section-header-" + itype.toLowerCase();
  var dateStr = reportDate || "";

  var html = '<div class="report-section">';
  html += '<div class="report-section-header ' + headerClass + '">';
  html += escapeHtml(itype);
  if (dateStr) {
    html += '<span class="report-date">Date : ' + escapeHtml(dateStr) + '</span>';
  }
  html += '</div>';
  html += '<div class="table-responsive">';
  html += '<table class="report-table">';
  html += '<thead><tr>';
  html += '<th>Country</th>';
  html += '<th>Integration completed Date</th>';
  html += '<th>Integration current date (Running)</th>';
  html += '<th>Integration running</th>';
  html += '<th>Reason</th>';
  html += '<th>Expected date to be up to date</th>';
  html += '</tr></thead>';
  html += '<tbody>';

  if (rows.length === 0) {
    html += '<tr><td colspan="6" style="text-align:center;color:#94a3b8;padding:24px">No data available</td></tr>';
  } else {
    rows.forEach(function(r) {
      var running = (r.is_running || "").toUpperCase();
      var runningClass = running === "YES" ? "report-running-yes" : "report-running-no";
      var expected = escapeHtml(r.expected_date || "");
      var expectedHtml = expected;
      if (expected.toLowerCase() === "up to date") {
        expectedHtml = '<span class="report-uptodate">' + expected + '</span>';
      }
      html += '<tr>';
      html += '<td><strong>' + escapeHtml(r.country || "") + '</strong></td>';
      html += '<td>' + formatReportDate(r.completed_date) + '</td>';
      html += '<td>' + formatReportDate(r.current_date) + '</td>';
      html += '<td><span class="' + runningClass + '">' + escapeHtml(running || "") + '</span></td>';
      html += '<td>' + escapeHtml(r.reason || "") + '</td>';
      html += '<td>' + expectedHtml + '</td>';
      html += '</tr>';
    });
  }

  html += '</tbody></table></div></div>';
  return html;
}

async function refreshManagementReport() {
  try {
    var res = await fetch("/api/management-report");
    if (!res.ok) {
      var err = await res.json();
      var container = document.getElementById("management-report-container");
      container.innerHTML = '<div class="table-empty-state"><i class="bi bi-exclamation-triangle"></i>' + escapeHtml(err.error || "Database error") + '</div>';
      return;
    }
    var data = await res.json();
    var container = document.getElementById("management-report-container");

    var now = new Date();
    var dd = String(now.getDate()).padStart(2, "0");
    var mm = String(now.getMonth() + 1).padStart(2, "0");
    var yy = String(now.getFullYear()).slice(-2);
    var reportDate = dd + "-" + mm + " " + yy;
    var dateEl = document.getElementById("report-date");
    if (dateEl) dateEl.textContent = "Date: " + reportDate;

    var types = Object.keys(data);
    if (types.length === 0) {
      container.innerHTML = '<div class="table-empty-state"><i class="bi bi-inbox"></i>No management report data available</div>';
      return;
    }

    var html = '<div class="p-4">';
    types.forEach(function(itype) {
      html += buildReportTable(itype, data[itype], reportDate);
    });
    html += '</div>';
    container.innerHTML = html;
  } catch (e) {
    showToast("Network error: unable to load management report", "error");
  }
}

/* ── Connection Banner ────────────────────────────────────────────── */
function showConnectionBanner(message) {
  var existing = document.getElementById("connection-banner");
  if (existing) {
    existing.querySelector(".connection-banner-text").textContent = message;
    existing.style.display = "";
    return;
  }
  var banner = document.createElement("div");
  banner.id = "connection-banner";
  banner.className = "connection-banner";
  banner.innerHTML =
    '<i class="bi bi-exclamation-triangle-fill me-2"></i>' +
    '<span class="connection-banner-text">' + escapeHtml(message) + '</span>' +
    '<span class="ms-2 small">Check your .env database settings and verify the database is reachable.</span>';
  var container = document.querySelector(".container-fluid");
  if (container) container.parentNode.insertBefore(banner, container);
}

function hideConnectionBanner() {
  var banner = document.getElementById("connection-banner");
  if (banner) banner.style.display = "none";
}

/* ── Orchestrator ────────────────────────────────────────────────── */
async function refreshAll() {
  var btn = document.getElementById("refresh-btn");
  var icon = document.getElementById("refresh-icon");
  var el = document.getElementById("last-updated");

  /* Disable button and show spinner while refreshing */
  if (btn) btn.disabled = true;
  if (icon) icon.classList.add("spin");
  el.textContent = "Refreshing\u2026";
  el.classList.add("refreshing");

  /* Check DB connectivity first */
  var dbOk = true;
  try {
    var healthRes = await fetch("/api/health");
    if (!healthRes.ok) {
      var healthData = await healthRes.json();
      showConnectionBanner(healthData.detail || "Unable to connect to the database");
      dbOk = false;
    } else {
      hideConnectionBanner();
    }
  } catch (e) {
    showConnectionBanner("Unable to reach the server");
    dbOk = false;
  }

  if (dbOk) {
    await Promise.all([
      refreshKPIs(),
      refreshPieChart(),
      refreshBarChart(),
      refreshTableErrors(),
      refreshIntegrationStatus(),
      refreshManagementReport(),
    ]);
  }

  el.textContent = "Last updated: " + new Date().toLocaleTimeString();
  el.classList.remove("refreshing");

  /* Re-enable button and stop spinner */
  if (btn) btn.disabled = false;
  if (icon) icon.classList.remove("spin");

  if (!isFirstLoad && dbOk) {
    showToast("Dashboard data refreshed", "success");
  }
  isFirstLoad = false;
}

/* Run on load; subsequent refreshes are triggered by the Refresh button */
document.addEventListener("DOMContentLoaded", function() {
  refreshAll();

  /* Refresh button click handler */
  var refreshBtn = document.getElementById("refresh-btn");
  if (refreshBtn) {
    refreshBtn.addEventListener("click", function() {
      refreshAll();
    });
  }

  /* Search / filter input handler */
  var searchInput = document.getElementById("status-search");
  if (searchInput) {
    searchInput.addEventListener("input", function() {
      renderIntegrationTable(integrationRows);
    });
  }
});
