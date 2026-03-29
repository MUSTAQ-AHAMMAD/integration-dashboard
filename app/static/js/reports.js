/* ══════════════════════════════════════════════════════════════════════
   Integration & Transaction Report Pages – Shared Logic
   ══════════════════════════════════════════════════════════════════════ */
"use strict";

/* ── Helpers ──────────────────────────────────────────────────────── */
function escapeHtml(text) {
  if (text === null || text === undefined) return "";
  var d = document.createElement("div");
  d.appendChild(document.createTextNode(String(text)));
  return d.innerHTML;
}

function statusBadge(status) {
  var s = (status || "unknown").toLowerCase();
  return '<span class="status-badge status-badge-' + s + '">' + escapeHtml(status) + "</span>";
}

function formatVal(val) {
  if (val === null || val === undefined || val === "") return '<span class="text-muted">&ndash;</span>';
  return escapeHtml(String(val));
}

function showToast(message, type) {
  var container = document.getElementById("toast-container");
  if (!container) return;
  var toast = document.createElement("div");
  toast.className = "dashboard-toast dashboard-toast-" + (type || "info");
  toast.textContent = message;
  container.appendChild(toast);
  setTimeout(function() { toast.remove(); }, 4000);
}

/* ── Load Regions ─────────────────────────────────────────────────── */
function loadRegions(callback) {
  fetch("/api/regions")
    .then(function(r) { return r.json(); })
    .then(function(regions) {
      var sel = document.getElementById("region-filter");
      if (!sel) return;
      /* keep "All Regions" option */
      while (sel.options.length > 1) sel.remove(1);
      regions.forEach(function(reg) {
        var opt = document.createElement("option");
        opt.value = reg;
        opt.textContent = reg;
        sel.appendChild(opt);
      });
      if (callback) callback();
    })
    .catch(function() {
      showToast("Failed to load regions", "error");
    });
}

/* ── Generic table loader ─────────────────────────────────────────── */
function loadTableData(url, tableId, columns, countId) {
  var region = document.getElementById("region-filter").value;
  var fetchUrl = region ? url + "?region=" + encodeURIComponent(region) : url;

  fetch(fetchUrl)
    .then(function(r) { return r.json(); })
    .then(function(rows) {
      var tbody = document.querySelector("#" + tableId + " tbody");
      if (!tbody) return;

      if (countId) {
        var badge = document.getElementById(countId);
        if (badge) badge.textContent = rows.length + " rows";
      }

      if (!rows.length) {
        tbody.innerHTML = '<tr><td colspan="' + columns.length + '" class="text-center text-muted">No data found</td></tr>';
        return;
      }

      var html = "";
      rows.forEach(function(row) {
        html += "<tr>";
        columns.forEach(function(col) {
          if (col === "status") {
            html += "<td>" + statusBadge(row[col]) + "</td>";
          } else {
            html += "<td>" + formatVal(row[col]) + "</td>";
          }
        });
        html += "</tr>";
      });
      tbody.innerHTML = html;
    })
    .catch(function() {
      showToast("Failed to load data for " + tableId, "error");
    });
}

/* ── Sales Integration Status ─────────────────────────────────────── */
function loadSalesIntegrationStatus() {
  fetch("/api/sales-integration-detail")
    .then(function(r) { return r.json(); })
    .then(function(rows) {
      var tbody = document.querySelector("#sales-status-table tbody");
      if (!tbody) return;

      var region = document.getElementById("region-filter").value;
      var filtered = region
        ? rows.filter(function(r) { return r.region && r.region.toLowerCase() === region.toLowerCase(); })
        : rows;

      if (!filtered.length) {
        tbody.innerHTML = '<tr><td colspan="3" class="text-center text-muted">No data found</td></tr>';
        return;
      }

      var html = "";
      filtered.forEach(function(row) {
        var statusClass = (row.status || "").toLowerCase() === "running" ? "status-badge-running" :
                          (row.status || "").toLowerCase() === "idle" ? "status-badge-stopped" : "status-badge-error";
        var statusLabel = (row.status || "").toLowerCase() === "idle" ? "IDLE (Stopped)" : escapeHtml(row.status);
        html += "<tr>";
        html += "<td>" + escapeHtml(row.region) + "</td>";
        html += "<td>" + escapeHtml(row.integ_mode) + "</td>";
        html += '<td><span class="status-badge ' + statusClass + '">' + statusLabel + "</span></td>";
        html += "</tr>";
      });
      tbody.innerHTML = html;
    })
    .catch(function() {
      showToast("Failed to load sales integration status", "error");
    });
}

/* ── Integration Report Initializer ───────────────────────────────── */
function initIntegrationReport() {
  loadRegions(function() {
    refreshIntegrationReport();
  });

  document.getElementById("region-filter").addEventListener("change", refreshIntegrationReport);
  document.getElementById("btn-refresh").addEventListener("click", refreshIntegrationReport);
}

function refreshIntegrationReport() {
  var ts = document.getElementById("report-last-updated");
  if (ts) ts.textContent = "Refreshing\u2026";

  loadSalesIntegrationStatus();

  loadTableData("/api/reports/invoice-headers", "invoice-header-table",
    ["row_id", "request_id", "status", "message", "request_date",
     "bill_to_cust_name", "bill_to_location", "business_unit",
     "txn_source", "gl_date", "txn_number", "region"],
    "invoice-header-count");

  loadTableData("/api/reports/invoice-lines", "invoice-line-table",
    ["row_id", "request_id", "status", "message", "request_date",
     "invoice_number", "line_number", "item_number", "description",
     "quantity", "unit_selling_price", "currency_code", "region"],
    "invoice-line-count");

  if (ts) ts.textContent = "Updated: " + new Date().toLocaleString();
}

/* ── Transaction Report Initializer ───────────────────────────────── */
function initTransactionReport() {
  loadRegions(function() {
    refreshTransactionReport();
  });

  document.getElementById("region-filter").addEventListener("change", refreshTransactionReport);
  document.getElementById("btn-refresh").addEventListener("click", refreshTransactionReport);
}

function refreshTransactionReport() {
  var ts = document.getElementById("report-last-updated");
  if (ts) ts.textContent = "Refreshing\u2026";

  loadTableData("/api/reports/misc-receipts", "misc-receipt-table",
    ["row_id", "request_id", "status", "message", "request_date",
     "receipt_number", "receipt_method_name", "amount", "currency_code",
     "gl_date", "receipt_date", "exchange_date", "region"],
    "misc-receipt-count");

  loadTableData("/api/reports/standard-receipts", "standard-receipt-table",
    ["row_id", "request_id", "status", "message", "request_date",
     "receipt_number", "amount", "currency_code",
     "gl_date", "receipt_date", "exchange_date", "region"],
    "standard-receipt-count");

  loadTableData("/api/reports/apply-receipts", "apply-receipt-table",
    ["row_id", "request_id", "status", "message", "request_date",
     "txn_number", "receipt_number", "amount_applied", "currency_code",
     "accounting_date", "application_date", "region"],
    "apply-receipt-count");

  loadTableData("/api/reports/inv-txn", "inv-txn-table",
    ["row_id", "request_id", "status", "message", "request_date",
     "organization_name", "item_number", "txn_source_name",
     "sunbinventory", "txn_date", "txn_qty", "region"],
    "inv-txn-count");

  if (ts) ts.textContent = "Updated: " + new Date().toLocaleString();
}
