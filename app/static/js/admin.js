/* ══════════════════════════════════════════════════════════════════════
   User Management Admin Page Logic
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
  var toast = document.createElement("div");
  toast.className = "dashboard-toast dashboard-toast-" + (type || "info");
  toast.textContent = message;
  container.appendChild(toast);
  setTimeout(function() { toast.remove(); }, 4000);
}

function showAlert(containerId, message, type) {
  var container = document.getElementById(containerId);
  if (!container) return;
  container.innerHTML = '<div class="alert alert-' + (type || "info") + ' alert-dismissible fade show">' +
    escapeHtml(message) +
    '<button type="button" class="btn-close" data-bs-dismiss="alert"></button></div>';
}

var PAGE_LABELS = {
  "dashboard": "Dashboard",
  "integration_report": "Integration Report",
  "transaction_report": "Transaction Report"
};

/* ── Load Users ───────────────────────────────────────────────────── */
function loadUsers() {
  fetch("/api/admin/users")
    .then(function(r) { return r.json(); })
    .then(function(users) {
      var tbody = document.querySelector("#users-table tbody");
      var badge = document.getElementById("user-count");
      if (badge) badge.textContent = users.length + " users";

      if (!users.length) {
        tbody.innerHTML = '<tr><td colspan="4" class="text-center text-muted">No users found</td></tr>';
        return;
      }

      var html = "";
      users.forEach(function(user) {
        var pages = (user.allowed_pages || []).map(function(p) {
          return '<span class="badge bg-secondary me-1">' + escapeHtml(PAGE_LABELS[p] || p) + '</span>';
        }).join("");

        html += "<tr>";
        html += "<td>" + escapeHtml(user.username) + "</td>";
        html += '<td><span class="badge ' + (user.role === "admin" ? "bg-primary" : "bg-info") + '">' + escapeHtml(user.role) + "</span></td>";
        html += "<td>" + pages + "</td>";
        html += '<td>' +
          '<button class="btn btn-sm btn-outline-primary me-1" onclick="editUser(\'' + user.id + '\')"><i class="bi bi-pencil"></i></button>' +
          '<button class="btn btn-sm btn-outline-danger" onclick="deleteUser(\'' + user.id + '\', \'' + escapeHtml(user.username) + '\')"><i class="bi bi-trash"></i></button>' +
          "</td>";
        html += "</tr>";
      });
      tbody.innerHTML = html;
    })
    .catch(function() {
      showToast("Failed to load users", "error");
    });
}

/* ── Create User ──────────────────────────────────────────────────── */
document.addEventListener("DOMContentLoaded", function() {
  loadUsers();

  document.getElementById("create-user-form").addEventListener("submit", function(e) {
    e.preventDefault();

    var pages = [];
    if (document.getElementById("page-dashboard").checked) pages.push("dashboard");
    if (document.getElementById("page-integration").checked) pages.push("integration_report");
    if (document.getElementById("page-transaction").checked) pages.push("transaction_report");

    var data = {
      username: document.getElementById("new-username").value.trim(),
      password: document.getElementById("new-password").value,
      role: document.getElementById("new-role").value,
      allowed_pages: pages
    };

    fetch("/api/admin/users", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(data)
    })
    .then(function(r) {
      if (!r.ok) return r.json().then(function(d) { throw new Error(d.error || "Failed to create user"); });
      return r.json();
    })
    .then(function() {
      showAlert("create-user-alert", "User created successfully!", "success");
      document.getElementById("create-user-form").reset();
      document.getElementById("page-dashboard").checked = true;
      document.getElementById("page-integration").checked = true;
      document.getElementById("page-transaction").checked = true;
      loadUsers();
    })
    .catch(function(err) {
      showAlert("create-user-alert", err.message, "danger");
    });
  });

  /* ── Save Edited User ──────────────────────────────────────────── */
  document.getElementById("btn-save-user").addEventListener("click", function() {
    var userId = document.getElementById("edit-user-id").value;
    var pages = [];
    if (document.getElementById("edit-page-dashboard").checked) pages.push("dashboard");
    if (document.getElementById("edit-page-integration").checked) pages.push("integration_report");
    if (document.getElementById("edit-page-transaction").checked) pages.push("transaction_report");

    var data = {
      username: document.getElementById("edit-username").value.trim(),
      role: document.getElementById("edit-role").value,
      allowed_pages: pages
    };

    var pw = document.getElementById("edit-password").value;
    if (pw) data.password = pw;

    fetch("/api/admin/users/" + userId, {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(data)
    })
    .then(function(r) {
      if (!r.ok) return r.json().then(function(d) { throw new Error(d.error || "Failed to update user"); });
      return r.json();
    })
    .then(function() {
      bootstrap.Modal.getInstance(document.getElementById("editUserModal")).hide();
      showToast("User updated successfully", "success");
      loadUsers();
    })
    .catch(function(err) {
      showAlert("edit-user-alert", err.message, "danger");
    });
  });
});

/* ── Edit User (open modal) ───────────────────────────────────────── */
function editUser(userId) {
  fetch("/api/admin/users")
    .then(function(r) { return r.json(); })
    .then(function(users) {
      var user = users.find(function(u) { return u.id === userId; });
      if (!user) {
        showToast("User not found", "error");
        return;
      }

      document.getElementById("edit-user-id").value = user.id;
      document.getElementById("edit-username").value = user.username;
      document.getElementById("edit-password").value = "";
      document.getElementById("edit-role").value = user.role;

      var pages = user.allowed_pages || [];
      document.getElementById("edit-page-dashboard").checked = pages.indexOf("dashboard") >= 0;
      document.getElementById("edit-page-integration").checked = pages.indexOf("integration_report") >= 0;
      document.getElementById("edit-page-transaction").checked = pages.indexOf("transaction_report") >= 0;

      new bootstrap.Modal(document.getElementById("editUserModal")).show();
    });
}

/* ── Delete User ──────────────────────────────────────────────────── */
function deleteUser(userId, username) {
  if (!confirm("Are you sure you want to delete user '" + username + "'?")) return;

  fetch("/api/admin/users/" + userId, { method: "DELETE" })
    .then(function(r) {
      if (!r.ok) return r.json().then(function(d) { throw new Error(d.error || "Failed to delete user"); });
      return r.json();
    })
    .then(function() {
      showToast("User deleted", "success");
      loadUsers();
    })
    .catch(function(err) {
      showToast(err.message, "error");
    });
}
