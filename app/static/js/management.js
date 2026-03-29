/* ══════════════════════════════════════════════════════════════════════
   Management Dashboard Page Logic
   ══════════════════════════════════════════════════════════════════════ */
"use strict";

/* ── Helpers ──────────────────────────────────────────────────────── */
function escapeHtml(text) {
  if (text === null || text === undefined) return "";
  var d = document.createElement("div");
  d.appendChild(document.createTextNode(String(text)));
  return d.innerHTML;
}

function showToast(message, type) {
  var container = document.getElementById("toast-container");
  if (!container) return;
  var icons = {
    success: "bi-check-circle-fill",
    error: "bi-exclamation-circle-fill",
    info: "bi-info-circle-fill",
  };
  var toast = document.createElement("div");
  toast.className = "toast-item toast-" + (type || "info");
  toast.innerHTML = '<i class="bi ' + (icons[type] || icons.info) + '"></i>' + escapeHtml(message);
  container.appendChild(toast);
  setTimeout(function() {
    toast.classList.add("toast-out");
    setTimeout(function() { toast.remove(); }, 300);
  }, 3000);
}

function tablePill(status, count) {
  var s = (status || "unknown").toLowerCase();
  return '<span class="table-pill table-pill-' + s + '">' +
    escapeHtml(status) + ": " + count + "</span>";
}

function formatReportDate(val) {
  if (!val) return "";
  var d = new Date(val);
  if (isNaN(d.getTime())) return escapeHtml(String(val));
  var day = d.getDate();
  var months = ["Jan","Feb","Mar","Apr","May","Jun","Jul","Aug","Sep","Oct","Nov","Dec"];
  return day + "-" + months[d.getMonth()];
}

/* ── Management Report ────────────────────────────────────────────── */
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

function refreshManagementReport() {
  fetch("/api/management-report")
    .then(function(res) {
      if (!res.ok) {
        return res.json().then(function(err) {
          var container = document.getElementById("mgmt-report-container");
          container.innerHTML = '<div class="table-empty-state"><i class="bi bi-exclamation-triangle"></i>' + escapeHtml(err.error || "Database error") + '</div>';
          throw new Error("API error");
        });
      }
      return res.json();
    })
    .then(function(data) {
      var container = document.getElementById("mgmt-report-container");

      var now = new Date();
      var dd = String(now.getDate()).padStart(2, "0");
      var mm = String(now.getMonth() + 1).padStart(2, "0");
      var yy = String(now.getFullYear()).slice(-2);
      var reportDate = dd + "-" + mm + " " + yy;

      var types = Object.keys(data);
      if (types.length === 0) {
        container.innerHTML = '<div class="table-empty-state"><i class="bi bi-inbox"></i>No management report data available</div>';
        updateKPIs(data);
        return;
      }

      var html = '<div class="p-4">';
      types.forEach(function(itype) {
        html += buildReportTable(itype, data[itype], reportDate);
      });
      html += '</div>';
      container.innerHTML = html;

      updateKPIs(data);
    })
    .catch(function(e) {
      if (e.message !== "API error") {
        showToast("Network error: unable to load management report", "error");
      }
    });
}

/* ── KPI calculation from management report data ──────────────────── */
function updateKPIs(data) {
  var countries = new Set();
  var running = 0;
  var notRunning = 0;
  var upToDate = 0;

  Object.keys(data).forEach(function(itype) {
    data[itype].forEach(function(row) {
      countries.add(row.country);
      var isRunning = (row.is_running || "").toUpperCase();
      if (isRunning === "YES") {
        running++;
      } else {
        notRunning++;
      }
      if ((row.expected_date || "").toLowerCase() === "up to date") {
        upToDate++;
      }
    });
  });

  document.getElementById("mgmt-kpi-countries").textContent = countries.size;
  document.getElementById("mgmt-kpi-running").textContent = running;
  document.getElementById("mgmt-kpi-notrunning").textContent = notRunning;
  document.getElementById("mgmt-kpi-uptodate").textContent = upToDate;
}

/* ── Table Summary ────────────────────────────────────────────────── */
function refreshTableSummary() {
  fetch("/api/table-errors")
    .then(function(res) {
      if (!res.ok) {
        return res.json().then(function(err) {
          var tbody = document.querySelector("#mgmt-table-summary tbody");
          tbody.innerHTML = '<tr><td colspan="2"><div class="table-empty-state"><i class="bi bi-exclamation-triangle"></i>' + escapeHtml(err.error || "Database error") + '</div></td></tr>';
          throw new Error("API error");
        });
      }
      return res.json();
    })
    .then(function(tables) {
      var tbody = document.querySelector("#mgmt-table-summary tbody");
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
    })
    .catch(function(e) {
      if (e.message !== "API error") {
        showToast("Network error: unable to load table summary", "error");
      }
    });
}

/* ── Orchestrator ────────────────────────────────────────────────── */
function refreshAll() {
  var ts = document.getElementById("mgmt-last-updated");
  if (ts) ts.textContent = "Refreshing\u2026";

  refreshManagementReport();
  refreshTableSummary();

  if (ts) ts.textContent = "Updated: " + new Date().toLocaleString();
}

document.addEventListener("DOMContentLoaded", function() {
  refreshAll();

  var refreshBtn = document.getElementById("btn-mgmt-refresh");
  if (refreshBtn) {
    refreshBtn.addEventListener("click", refreshAll);
  }
});
