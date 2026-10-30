/**
 * Smart IT Ops - Frontend Application Controller
 * Handles REST API communication, WebSocket subscriptions, RBAC UI views,
 * rule-based auto-classification preview, and modal workflows.
 */

// Global State
let currentUser = null;
let authToken = localStorage.getItem("auth_token") || null;
let socket = null;
let currentRole = "ADMIN";

// Determine API Base Prefix and host dynamically
// In production (Vercel), point to the Render backend.
// In local development, use localhost:8000.
const isLocalhost = ["localhost", "127.0.0.1", ""].includes(window.location.hostname);
const isDirectFile = window.location.protocol === "file:";
const RENDER_BACKEND_URL = "https://it-asset-management-system.onrender.com";
const BACKEND_ORIGIN = (isLocalhost || isDirectFile) ? "http://127.0.0.1:8000" : RENDER_BACKEND_URL;
const API_BASE = `${BACKEND_ORIGIN}/api/v1`;
let wsReconnectTimer = null;

// Document Ready Initialization
document.addEventListener("DOMContentLoaded", () => {
  initEventListeners();
  checkAuthAndBootstrap();
});

function initEventListeners() {
  // Tabs Navigation
  document.querySelectorAll(".nav-tab").forEach(tabBtn => {
    tabBtn.addEventListener("click", () => {
      document.querySelectorAll(".nav-tab").forEach(b => b.classList.remove("active"));
      document.querySelectorAll(".tab-pane").forEach(p => p.classList.remove("active"));

      tabBtn.classList.add("active");
      const targetPane = document.getElementById(tabBtn.dataset.tab);
      if (targetPane) targetPane.classList.add("active");

      if (tabBtn.dataset.tab === "availableAssetsTab") {
        loadAvailableAssets();
      } else if (tabBtn.dataset.tab === "assetsTab") {
        loadAssets();
      } else if (tabBtn.dataset.tab === "usersTab") {
        loadUsers();
      }
    });
  });

  // Login Form
  const loginForm = document.getElementById("loginForm");
  if (loginForm) {
    loginForm.addEventListener("submit", handleLoginSubmit);
  }

  // Logout Button
  const logoutBtn = document.getElementById("logoutBtn");
  if (logoutBtn) {
    logoutBtn.addEventListener("click", handleLogout);
  }


  // Modals Openers
  document.getElementById("openNewTicketModalBtn")?.addEventListener("click", () => openModal("newTicketModal"));
  document.getElementById("openNewAssetModalBtn")?.addEventListener("click", () => {
    if (currentUser?.role === "EMPLOYEE") {
      alert("Access denied: Employees cannot register assets.");
      return;
    }
    openModal("newAssetModal");
  });
  document.getElementById("openCreateUserModalBtn")?.addEventListener("click", () => {
    if (currentUser?.role !== "ADMIN") {
      alert("Access denied: Only Admins can create users.");
      return;
    }
    document.getElementById("createUserForm")?.reset();
    document.getElementById("createUserError")?.classList.add("hidden");
    openModal("createUserModal");
  });

  // Forms Submit
  document.getElementById("createTicketForm")?.addEventListener("submit", handleCreateTicket);
  document.getElementById("createAssetForm")?.addEventListener("submit", handleCreateAsset);
  document.getElementById("assignTicketForm")?.addEventListener("submit", handleAssignTicket);
  document.getElementById("resolveTicketForm")?.addEventListener("submit", handleResolveTicket);
  document.getElementById("assignAssetForm")?.addEventListener("submit", handleAssignAsset);
  document.getElementById("createUserForm")?.addEventListener("submit", handleCreateUser);

  // Filters & Refresh
  document.getElementById("ticketStatusFilter")?.addEventListener("change", loadTickets);
  document.getElementById("ticketPriorityFilter")?.addEventListener("change", loadTickets);
  document.getElementById("refreshTicketsBtn")?.addEventListener("click", loadTickets);

  document.getElementById("assetTypeFilter")?.addEventListener("change", loadAssets);
  document.getElementById("assetStatusFilter")?.addEventListener("change", loadAssets);
  document.getElementById("refreshAssetsBtn")?.addEventListener("click", loadAssets);

  document.getElementById("availableAssetTypeFilter")?.addEventListener("change", loadAvailableAssets);
  document.getElementById("refreshAvailableAssetsBtn")?.addEventListener("click", loadAvailableAssets);



  // Live Auto-Classifier Preview in Raise Ticket Modal
  const titleInput = document.getElementById("ticketTitle");
  const descInput = document.getElementById("ticketDescription");
  if (titleInput && descInput) {
    const previewHandler = () => updateClassificationPreview(titleInput.value, descInput.value);
    titleInput.addEventListener("input", previewHandler);
    descInput.addEventListener("input", previewHandler);
  }
}

// =====================================================================
// Authentication & Bootstrap
// =====================================================================

async function checkAuthAndBootstrap() {
  // First verify the server is reachable
  const serverOk = await checkServerHealth();
  if (!serverOk) return;

  if (!authToken) {
    showLoginModal();
    return;
  }

  try {
    const res = await apiRequest("/auth/me");
    if (res && res.data) {
      currentUser = res.data;
      updateUserProfileUI(currentUser);
      initWebSocket();
      bootstrapPortalData();
    } else {
      localStorage.removeItem("auth_token");
      authToken = null;
      showLoginModal();
    }
  } catch (err) {
    console.warn("Auth check failed:", err);
    localStorage.removeItem("auth_token");
    authToken = null;
    showLoginModal();
  }
}

async function checkServerHealth() {
  try {
    const res = await fetch(`${BACKEND_ORIGIN}/health`, { cache: "no-store" });
    return res.ok;
  } catch (err) {
    console.error("Server health check failed:", err);
    const errorBox = document.getElementById("loginError");
    if (errorBox) {
      errorBox.textContent = `Cannot reach server at ${BACKEND_ORIGIN}. Make sure the backend is running: python app/main.py`;
      errorBox.classList.remove("hidden");
    }
    openModal("loginModal");
    return false;
  }
}

async function hashPasswordForTransmission(plainPassword) {
  try {
    if (window.crypto && window.crypto.subtle) {
      const encoder = new TextEncoder();
      const data = encoder.encode(plainPassword);
      const hashBuffer = await crypto.subtle.digest("SHA-256", data);
      const hashArray = Array.from(new Uint8Array(hashBuffer));
      return hashArray.map(b => b.toString(16).padStart(2, "0")).join("");
    }
  } catch (e) {
    console.warn("Client pre-hashing failed, falling back to raw transmission:", e);
  }
  return plainPassword;
}

async function autoDemoLogin(email, password) {
  try {
    const securePassword = await hashPasswordForTransmission(password);
    const res = await fetch(`${API_BASE}/auth/login`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ email, password: securePassword }),
    });
    if (!res.ok) {
      showLoginModal();
      return;
    }
    const json = await res.json();
    if (json.success && json.data) {
      authToken = json.data.access_token;
      localStorage.setItem("auth_token", authToken);
      currentUser = json.data.user;
      updateUserProfileUI(currentUser);
      initWebSocket();
      bootstrapPortalData();
      closeModal("loginModal");
    } else {
      showLoginModal();
    }
  } catch (err) {
    console.warn("autoDemoLogin error:", err);
    showLoginModal();
  }
}

async function handleLoginSubmit(e) {
  e.preventDefault();
  const email = document.getElementById("loginEmail").value.trim();
  const password = document.getElementById("loginPassword").value;
  const errorBox = document.getElementById("loginError");
  const submitBtn = document.getElementById("loginSubmitBtn");
  errorBox.classList.add("hidden");
  if (submitBtn) { submitBtn.disabled = true; submitBtn.textContent = "Connecting..."; }

  try {
    // Pre-flight health check to give a clear connectivity error
    const healthRes = await fetch(`${BACKEND_ORIGIN}/health`, { cache: "no-store" }).catch(() => null);
    if (!healthRes || !healthRes.ok) {
      errorBox.textContent = `Cannot reach server at ${BACKEND_ORIGIN}. Make sure python app/main.py is running.`;
      errorBox.classList.remove("hidden");
      return;
    }

    const securePassword = await hashPasswordForTransmission(password);
    const res = await fetch(`${API_BASE}/auth/login`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ email, password: securePassword }),
    });

    if (!res.ok) {
      let errMsg = "Invalid credentials or request error.";
      try {
        const errorJson = await res.json();
        errMsg = errorJson.detail || errorJson.message || errMsg;
      } catch {
        const text = await res.text();
        if (text) errMsg = text;
      }
      errorBox.textContent = errMsg;
      errorBox.classList.remove("hidden");
      return;
    }

    let json;
    try {
      json = await res.json();
    } catch {
      errorBox.textContent = "Invalid response from server.";
      errorBox.classList.remove("hidden");
      return;
    }

    if (json.success && json.data) {
      authToken = json.data.access_token;
      localStorage.setItem("auth_token", authToken);
      currentUser = json.data.user;
      updateUserProfileUI(currentUser);
      closeModal("loginModal");
      initWebSocket();
      bootstrapPortalData();
    } else {
      errorBox.textContent = json.message || "Invalid credentials.";
      errorBox.classList.remove("hidden");
    }
  } catch (err) {
    console.error("Login request failed:", err);
    errorBox.textContent = `Login failed: ${err.message}`;
    errorBox.classList.remove("hidden");
  } finally {
    if (submitBtn) { submitBtn.disabled = false; submitBtn.textContent = "Authenticate Session"; }
  }
}

function handleLogout() {
  authToken = null;
  currentUser = null;
  localStorage.removeItem("auth_token");
  if (wsReconnectTimer) {
    clearTimeout(wsReconnectTimer);
    wsReconnectTimer = null;
  }
  if (socket) {
    socket.onclose = null;
    socket.close();
    socket = null;
  }
  showLoginModal();
}

function showLoginModal() {
  openModal("loginModal");
}

window.fillLogin = function(email, pwd) {
  document.getElementById("loginEmail").value = email;
  document.getElementById("loginPassword").value = pwd;
};

function updateUserProfileUI(user) {
  document.getElementById("userName").textContent = user.full_name;
  document.getElementById("userRoleBadge").textContent = user.role;
  document.getElementById("userAvatar").textContent = user.full_name.charAt(0).toUpperCase();

  currentRole = user.role;
  const isEmp = user.role === "EMPLOYEE";

  // 1. Toggle KPI Grids: Admin/Support gets enterprise KPIs, Employee gets personal stats only
  const adminKpi = document.getElementById("adminKpiGrid");
  const empKpi = document.getElementById("employeeKpiGrid");
  if (adminKpi && empKpi) {
    if (isEmp) {
      adminKpi.classList.add("hidden");
      empKpi.classList.remove("hidden");
    } else {
      adminKpi.classList.remove("hidden");
      empKpi.classList.add("hidden");
    }
  }

  // 2. SLA & Reports Tab visibility: Employees should not see enterprise analytics
  const analyticsTabBtn = document.getElementById("tabAnalyticsBtn");
  if (analyticsTabBtn) {
    analyticsTabBtn.style.display = isEmp ? "none" : "";
    if (isEmp && analyticsTabBtn.classList.contains("active")) {
      analyticsTabBtn.classList.remove("active");
      document.getElementById("analyticsTab")?.classList.remove("active");
      document.querySelector('[data-tab="ticketsTab"]')?.classList.add("active");
      document.getElementById("ticketsTab")?.classList.add("active");
    }
  }

  // 2b. Available Assets Tab: Employees cannot see/request available assets
  const availableAssetsTabBtn = document.getElementById("tabAvailableAssetsBtn");
  if (availableAssetsTabBtn) {
    availableAssetsTabBtn.style.display = isEmp ? "none" : "";
    if (isEmp && availableAssetsTabBtn.classList.contains("active")) {
      availableAssetsTabBtn.classList.remove("active");
      document.getElementById("availableAssetsTab")?.classList.remove("active");
      document.querySelector('[data-tab="ticketsTab"]')?.classList.add("active");
      document.getElementById("ticketsTab")?.classList.add("active");
    }
  }

  // 2c. Users Tab (Admin/Support only)
  const usersTabBtn = document.getElementById("tabUsersBtn");
  if (usersTabBtn) {
    usersTabBtn.style.display = isEmp ? "none" : "";
  }

  // 3. Asset & Ticket control buttons
  const registerAssetBtn = document.getElementById("openNewAssetModalBtn");
  if (registerAssetBtn) {
    registerAssetBtn.style.display = isEmp ? "none" : "";
  }
  const exportAssetsCsvBtn = document.getElementById("exportAssetsCsvBtn");
  if (exportAssetsCsvBtn) {
    exportAssetsCsvBtn.style.display = isEmp ? "none" : "";
  }
  const exportTicketsCsvBtn = document.getElementById("exportTicketsCsvBtn");
  if (exportTicketsCsvBtn) {
    exportTicketsCsvBtn.style.display = isEmp ? "none" : "";
  }

  // 4. Panel Titles & Labels
  const tabTicketsLabel = document.getElementById("tabTicketsLabel");
  if (tabTicketsLabel) {
    if (isEmp) tabTicketsLabel.textContent = "My Tickets";
    else if (user.role === "SUPPORT") tabTicketsLabel.textContent = "Assigned Tickets";
    else tabTicketsLabel.textContent = "Support Tickets";
  }
  const tabAssetsLabel = document.getElementById("tabAssetsLabel");
  if (tabAssetsLabel) tabAssetsLabel.textContent = isEmp ? "My Assets" : "Assets";

  const tabAvailableAssetsLabel = document.getElementById("tabAvailableAssetsLabel");
  if (tabAvailableAssetsLabel) tabAvailableAssetsLabel.textContent = "Available Assets";

  const ticketsPanelTitle = document.getElementById("ticketsPanelTitle");
  if (ticketsPanelTitle) {
    if (isEmp) ticketsPanelTitle.textContent = "My Support Tickets";
    else if (user.role === "SUPPORT") ticketsPanelTitle.textContent = "Assigned Support Tickets";
    else ticketsPanelTitle.textContent = "Support Tickets";
  }
  const ticketsPanelSub = document.getElementById("ticketsPanelSub");
  if (ticketsPanelSub) {
    if (isEmp) {
      ticketsPanelSub.textContent = "Track the status and resolution of your reported issues";
    } else if (user.role === "SUPPORT") {
      ticketsPanelSub.textContent = "Incident tickets assigned to you for active resolution";
    } else {
      ticketsPanelSub.textContent = "Manage incident lifecycles, SLA countdowns, and automated classifications";
    }
  }

  const assetsPanelTitle = document.getElementById("assetsPanelTitle");
  if (assetsPanelTitle) assetsPanelTitle.textContent = isEmp ? "My Assets" : "Assets";
  const assetsPanelSub = document.getElementById("assetsPanelSub");
  if (assetsPanelSub) {
    assetsPanelSub.textContent = isEmp
      ? "Hardware equipment currently assigned to you"
      : "Complete enterprise hardware inventory across all lifecycle states";
  }
}


// =====================================================================
// Real-Time Subscriptions (Disabled)
// =====================================================================

function initWebSocket() {
  // Realtime websocket feed removed per user request
}

// =====================================================================
// Data Bootstrapping & API Helpers
// =====================================================================

async function apiRequest(endpoint, method = "GET", body = null) {
  const headers = { "Content-Type": "application/json" };
  if (authToken) {
    headers["Authorization"] = `Bearer ${authToken}`;
  }

  const options = { method, headers };
  if (body) options.body = JSON.stringify(body);

  const res = await fetch(`${API_BASE}${endpoint}`, options);
  if (res.status === 401) {
    handleLogout();
    throw new Error("Unauthorized");
  }
  return await res.json();
}

function bootstrapPortalData() {
  loadTickets();
  loadAssets();
  if (currentUser?.role !== "EMPLOYEE") {
    loadAvailableAssets();
    loadUsers();
  }
  loadAnalytics();
}

// =====================================================================
// Tickets Management
// =====================================================================

async function loadTickets() {
  const statusFilter = document.getElementById("ticketStatusFilter")?.value || "";
  const priorityFilter = document.getElementById("ticketPriorityFilter")?.value || "";

  let url = "/tickets";
  const params = [];
  if (statusFilter) params.push(`status_filter=${statusFilter}`);
  if (priorityFilter) params.push(`priority_filter=${priorityFilter}`);
  if (params.length) url += `?${params.join("&")}`;

  try {
    const res = await apiRequest(url);
    const tbody = document.getElementById("ticketsTableBody");
    if (!tbody) return;

    if (currentUser?.role === "EMPLOYEE") {
      const openCount = (res.data || []).filter(t => t.status !== "CLOSED" && t.status !== "RESOLVED").length;
      const empTicketsEl = document.getElementById("kpiEmpTickets");
      if (empTicketsEl) empTicketsEl.textContent = openCount;
    }

    if (!res.data || res.data.length === 0) {
      let emptyMsg = "No support tickets found.";
      if (currentUser?.role === "EMPLOYEE") {
        emptyMsg = "You have not raised any support tickets.";
      } else if (currentUser?.role === "SUPPORT") {
        emptyMsg = "No support tickets are currently assigned to you.";
      }
      tbody.innerHTML = `<tr><td colspan="9" class="text-center text-muted" style="padding: 30px;">${emptyMsg}</td></tr>`;
      return;
    }

    tbody.innerHTML = res.data.map(t => {
      const isBreached = new Date(t.sla_deadline) < new Date() && t.status !== "RESOLVED" && t.status !== "CLOSED";
      const slaClass = isBreached ? "badge-breached" : "badge-active";
      const deadlineStr = new Date(t.sla_deadline).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });

      return `
        <tr>
          <td><strong>${t.ticket_id}</strong></td>
          <td>${escapeHtml(t.title)}</td>
          <td><span class="badge badge-low">${t.category}</span></td>
          <td><span class="badge badge-${t.priority.toLowerCase()}">${t.priority}</span></td>
          <td><span class="badge-status badge-status-${t.status.toLowerCase()}">${t.status}</span></td>
          <td><span class="badge ${slaClass}">${deadlineStr} ${isBreached ? '⚠️ BREACHED' : '✓ Active'}</span></td>
          <td>${renderEmployeeLink(t.created_by)}</td>
          <td>${renderEmployeeLink(t.assigned_to)}</td>
          <td>
            <div style="display:flex; gap: 4px;">
              ${renderTicketActionButtons(t)}
            </div>
          </td>
        </tr>
      `;
    }).join("");
  } catch (err) {
    console.error("Failed loading tickets:", err);
  }
}

function renderTicketActionButtons(t) {
  const role = currentUser?.role || "EMPLOYEE";
  let btns = "";

  if (t.status === "OPEN" && (role === "ADMIN" || role === "SUPPORT")) {
    btns += `<button class="btn btn-xs btn-primary" onclick="openAssignTicketModal('${t.ticket_id}')">Assign</button>`;
  }
  if (t.status === "ASSIGNED" && (role === "ADMIN" || role === "SUPPORT")) {
    btns += `<button class="btn btn-xs btn-secondary" onclick="progressTicket('${t.ticket_id}')">Start</button>`;
  }
  if (t.status === "IN_PROGRESS" && (role === "ADMIN" || role === "SUPPORT")) {
    btns += `<button class="btn btn-xs btn-success" onclick="openResolveTicketModal('${t.ticket_id}')">Resolve</button>`;
  }
  if (t.status === "RESOLVED" && (role === "ADMIN" || role === "EMPLOYEE" || role === "SUPPORT")) {
    btns += `<button class="btn btn-xs btn-subtle" onclick="closeTicket('${t.ticket_id}')">Close</button>`;
  }
  return btns || `<span class="text-muted">-</span>`;
}

// Client-Side Rule-Based Classification Preview
function updateClassificationPreview(title, desc) {
  const text = `${title} ${desc}`.toLowerCase();
  let cat = "Other";
  let prio = "LOW";
  let slaHours = 24;

  if (/\b(laptop|monitor|screen|keyboard|mouse|printer|hardware|battery)\b/.test(text)) {
    cat = "Hardware";
  } else if (/\b(wifi|network|ethernet|internet|vpn|dns)\b/.test(text)) {
    cat = "Network";
  } else if (/\b(password|login|credentials|access|permission|mfa)\b/.test(text)) {
    cat = "Access";
  } else if (/\b(windows|office|excel|install|crash|software|bug)\b/.test(text)) {
    cat = "Software";
  }

  if (/\b(outage|critical|production|entire floor|emergency)\b/.test(text)) {
    prio = "CRITICAL";
    slaHours = 2;
  } else if (/\b(not starting|cannot work|deadline|crash|broken)\b/.test(text)) {
    prio = "HIGH";
    slaHours = 4;
  } else if (/\b(slow|glitch|warning|flickering|partial)\b/.test(text)) {
    prio = "MEDIUM";
    slaHours = 8;
  }

  document.getElementById("autoCatPreview").textContent = cat;
  document.getElementById("autoPrioPreview").textContent = `${prio} (Rule-Based)`;
  document.getElementById("autoSlaPreview").textContent = `${slaHours} Hours SLA Window`;
}

async function handleCreateTicket(e) {
  e.preventDefault();
  const title = document.getElementById("ticketTitle").value.trim();
  const description = document.getElementById("ticketDescription").value.trim();

  try {
    const res = await apiRequest("/tickets", "POST", { title, description });
    if (res.success) {
      closeModal("newTicketModal");
      document.getElementById("createTicketForm").reset();
      loadTickets();
      loadAnalytics();
    } else {
      alert(res.message || "Could not create ticket.");
    }
  } catch (err) {
    alert("Error creating ticket: " + err.message);
  }
}

window.openAssignTicketModal = function(ticketId) {
  document.getElementById("assignTargetTicketId").value = ticketId;
  openModal("assignTicketModal");
};

async function handleAssignTicket(e) {
  e.preventDefault();
  const ticketId = document.getElementById("assignTargetTicketId").value;
  const assigned_to = document.getElementById("assignSupportUserId").value;
  const comments = document.getElementById("assignComments").value;

  try {
    await apiRequest(`/tickets/${ticketId}/assign`, "POST", { assigned_to, comments });
    closeModal("assignTicketModal");
    loadTickets();
  } catch (err) {
    alert("Assignment failed: " + err.message);
  }
}

window.progressTicket = async function(ticketId) {
  try {
    await apiRequest(`/tickets/${ticketId}/progress`, "POST");
    loadTickets();
  } catch (err) {
    alert("Could not start work: " + err.message);
  }
};

window.openResolveTicketModal = function(ticketId) {
  document.getElementById("resolveTargetTicketId").value = ticketId;
  openModal("resolveTicketModal");
};

async function handleResolveTicket(e) {
  e.preventDefault();
  const ticketId = document.getElementById("resolveTargetTicketId").value;
  const resolution = document.getElementById("resolveExplanation").value;

  try {
    await apiRequest(`/tickets/${ticketId}/resolve`, "POST", { resolution });
    closeModal("resolveTicketModal");
    document.getElementById("resolveTicketForm").reset();
    loadTickets();
    loadAnalytics();
  } catch (err) {
    alert("Could not resolve ticket: " + err.message);
  }
}

window.closeTicket = async function(ticketId) {
  if (!confirm(`Are you sure you want to close ticket ${ticketId}?`)) return;
  try {
    await apiRequest(`/tickets/${ticketId}/close`, "POST");
    loadTickets();
    loadAnalytics();
  } catch (err) {
    alert("Could not close ticket: " + err.message);
  }
};

// =====================================================================
// Asset Management
// =====================================================================

async function loadAssets() {
  const assetType = document.getElementById("assetTypeFilter")?.value || "";
  const statusFilter = document.getElementById("assetStatusFilter")?.value || "";

  let url = "/assets";
  const params = [];
  if (assetType) params.push(`asset_type=${assetType}`);
  if (statusFilter) params.push(`status_filter=${statusFilter}`);
  if (params.length) url += `?${params.join("&")}`;

  try {
    const res = await apiRequest(url);
    const tbody = document.getElementById("assetsTableBody");
    if (!tbody) return;

    if (currentUser?.role === "EMPLOYEE") {
      const empAssetsEl = document.getElementById("kpiEmpAssets");
      if (empAssetsEl) empAssetsEl.textContent = (res.data || []).length;
    }

    if (!res.data || res.data.length === 0) {
      const emptyMsg = currentUser?.role === "EMPLOYEE" ? "You currently have no hardware assets assigned." : "No hardware assets found.";
      tbody.innerHTML = `<tr><td colspan="9" class="text-center text-muted" style="padding: 30px;">${emptyMsg}</td></tr>`;
      return;
    }

    tbody.innerHTML = res.data.map(a => {
      const statusBadge = `badge-${a.status.toLowerCase()}`;
      const specsSummary = a.specs ? Object.entries(a.specs).map(([k, v]) => `${k}: ${v}`).join(", ") : "-";

      return `
        <tr>
          <td><strong>${a.asset_id}</strong></td>
          <td><span class="badge badge-low">${a.type}</span></td>
          <td>${escapeHtml(a.brand)} ${escapeHtml(a.model)}</td>
          <td><code>${escapeHtml(a.serial_number)}</code></td>
          <td><span class="badge ${statusBadge}">${a.status}</span></td>
          <td>${renderEmployeeLink(a.assigned_to)}</td>
          <td><small class="text-secondary">${escapeHtml(specsSummary)}</small></td>
          <td>$${a.purchase_cost}</td>
          <td>
            <div style="display:flex; gap: 4px;">
              ${renderAssetActionButtons(a)}
            </div>
          </td>
        </tr>
      `;
    }).join("");
  } catch (err) {
    console.error("Failed loading assets:", err);
  }
}

function renderAssetActionButtons(a) {
  const role = currentUser?.role || "EMPLOYEE";
  if (role !== "ADMIN" && role !== "SUPPORT") {
    return `<span class="badge badge-assigned">Assigned to You</span>`;
  }

  let btns = "";
  if (a.status === "AVAILABLE") {
    btns += `<button class="btn btn-xs btn-primary" onclick="openAssignAssetModal('${a.asset_id}')">Assign</button>`;
  }
  if (a.status === "ASSIGNED") {
    btns += `<button class="btn btn-xs btn-secondary" onclick="returnAsset('${a.asset_id}')">Return</button>`;
  }
  if (a.status !== "RETIRED" && role === "ADMIN") {
    btns += `<button class="btn btn-xs btn-outline-danger" onclick="retireAsset('${a.asset_id}')">Retire</button>`;
  }
  return btns || `<span class="text-muted">-</span>`;
}

async function handleCreateAsset(e) {
  e.preventDefault();
  const asset_id = document.getElementById("assetIdInput").value.trim();
  const asset_type = document.getElementById("assetTypeSelect").value;
  const brand = document.getElementById("assetBrandInput").value.trim();
  const model = document.getElementById("assetModelInput").value.trim();
  const serial_number = document.getElementById("assetSerialInput").value.trim();
  const purchase_cost = parseFloat(document.getElementById("assetCostInput").value) || 0;
  const purchase_date = document.getElementById("assetDateInput").value;

  try {
    const res = await apiRequest("/assets", "POST", {
      asset_id,
      asset_type,
      brand,
      model,
      serial_number,
      purchase_date,
      purchase_cost,
    });
    if (res.success) {
      closeModal("newAssetModal");
      document.getElementById("createAssetForm").reset();
      refreshAllAssetViews();
    } else {
      alert(res.message || "Could not register asset.");
    }
  } catch (err) {
    alert("Asset registration error: " + err.message);
  }
}

window.openAssignAssetModal = function(assetId) {
  document.getElementById("assignTargetAssetId").value = assetId;
  openModal("assignAssetModal");
};

async function handleAssignAsset(e) {
  e.preventDefault();
  const assetId = document.getElementById("assignTargetAssetId").value;
  const user_id = document.getElementById("assignEmployeeId").value;
  const notes = document.getElementById("assignAssetNotes").value;

  try {
    await apiRequest(`/assets/${assetId}/assign`, "POST", { user_id, notes });
    closeModal("assignAssetModal");
    refreshAllAssetViews();
  } catch (err) {
    alert("Assignment error: " + err.message);
  }
}

window.returnAsset = async function(assetId) {
  if (!confirm(`Return asset ${assetId} to inventory?`)) return;
  try {
    await apiRequest(`/assets/${assetId}/return`, "POST");
    refreshAllAssetViews();
  } catch (err) {
    alert("Return error: " + err.message);
  }
};

window.retireAsset = async function(assetId) {
  if (!confirm(`Decommission and retire asset ${assetId}?`)) return;
  try {
    await apiRequest(`/assets/${assetId}`, "DELETE");
    refreshAllAssetViews();
  } catch (err) {
    alert("Retire error: " + err.message);
  }
};

// =====================================================================
// Available Assets Management
// =====================================================================

window.loadAvailableAssets = async function() {
  const tbody = document.getElementById("availableAssetsTableBody");
  const countBadge = document.getElementById("availableAssetsCountBadge");
  const assetType = document.getElementById("availableAssetTypeFilter")?.value || "";

  let url = "/assets?status_filter=AVAILABLE";
  if (assetType) url += `&asset_type=${encodeURIComponent(assetType)}`;

  try {
    const res = await apiRequest(url);
    if (!tbody) return;

    if (!res || !res.data) {
      tbody.innerHTML = `<tr><td colspan="8" class="text-center text-muted" style="padding: 30px;">No available hardware assets found.</td></tr>`;
      if (countBadge) countBadge.textContent = "0 Available";
      return;
    }

    const availableAssets = (res.data || []).filter(a => a.status === "AVAILABLE");
    if (countBadge) {
      countBadge.textContent = `${availableAssets.length} Available`;
    }

    if (availableAssets.length === 0) {
      tbody.innerHTML = `<tr><td colspan="8" class="text-center text-muted" style="padding: 30px;">No available hardware assets found.</td></tr>`;
      return;
    }

    tbody.innerHTML = availableAssets.map(a => {
      let specsSummary = "-";
      if (a.specs) {
        if (typeof a.specs === "object" && a.specs !== null) {
          specsSummary = Object.entries(a.specs).map(([k, v]) => `${k}: ${v}`).join(", ");
        } else {
          try {
            const parsed = JSON.parse(a.specs);
            specsSummary = Object.entries(parsed).map(([k, v]) => `${k}: ${v}`).join(", ");
          } catch {
            specsSummary = String(a.specs);
          }
        }
      }

      const cost = typeof a.purchase_cost === "number" ? a.purchase_cost.toFixed(2) : (a.purchase_cost || "0.00");

      return `
        <tr>
          <td><strong>${escapeHtml(a.asset_id)}</strong></td>
          <td><span class="badge badge-low">${escapeHtml(a.type || a.asset_type || "Hardware")}</span></td>
          <td>${escapeHtml(a.brand || "")} ${escapeHtml(a.model || "")}</td>
          <td><code>${escapeHtml(a.serial_number || "-")}</code></td>
          <td><span class="badge badge-available">AVAILABLE</span></td>
          <td><small class="text-secondary">${escapeHtml(specsSummary)}</small></td>
          <td>$${cost}</td>
          <td>
            <div style="display:flex; gap: 4px;">
              ${renderAvailableAssetActionButtons(a)}
            </div>
          </td>
        </tr>
      `;
    }).join("");
  } catch (err) {
    console.error("Failed loading available assets:", err);
    if (tbody) {
      tbody.innerHTML = `
        <tr>
          <td colspan="8" class="text-center text-muted" style="padding: 30px; color: var(--color-critical-text);">
            Error loading available assets: ${escapeHtml(err.message || "Failed to fetch")}.
            <div style="margin-top: 10px;">
              <button type="button" class="btn btn-xs btn-primary" onclick="loadAvailableAssets()">Retry</button>
            </div>
          </td>
        </tr>
      `;
    }
  }
};

function renderAvailableAssetActionButtons(a) {
  const role = currentUser?.role || "EMPLOYEE";
  if (role !== "ADMIN" && role !== "SUPPORT") {
    return `<span class="badge badge-available">Ready to Request</span>`;
  }

  let btns = `<button class="btn btn-xs btn-primary" onclick="openAssignAssetModal('${a.asset_id}')">Assign</button>`;
  if (role === "ADMIN") {
    btns += `<button class="btn btn-xs btn-outline-danger" onclick="retireAsset('${a.asset_id}')">Retire</button>`;
  }
  return btns;
}

window.handleOpenNewAssetModal = window.triggerRegisterAsset = function() {
  if (currentUser?.role === "EMPLOYEE") {
    alert("Access denied: Employees cannot register assets.");
    return;
  }
  openModal("newAssetModal");
};

// =====================================================================
// Employee Assets Modal & Bulk Return
// =====================================================================

let currentViewingEmpId = "";

window.renderEmployeeLink = function(empId) {
  if (!empId) return `<span class="text-muted">Unassigned</span>`;
  const isMe = currentUser && empId === currentUser.user_id;
  const label = isMe ? `${empId} (You)` : empId;
  return `
    <button type="button" class="emp-id-btn" onclick="openEmployeeAssetsModal('${escapeHtml(empId)}')" title="Click to view assigned assets for ${escapeHtml(empId)}">
      <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5">
        <path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2"></path>
        <circle cx="12" cy="7" r="4"></circle>
      </svg>
      <span>${escapeHtml(label)}</span>
    </button>
  `;
};

window.promptEmployeeLookup = function() {
  const empId = prompt("Enter Employee ID to view assigned assets (e.g. EMP-101):", "EMP-101");
  if (empId && empId.trim()) {
    openEmployeeAssetsModal(empId.trim());
  }
};

window.openEmployeeAssetsModal = async function(employeeId) {
  if (!employeeId) return;
  currentViewingEmpId = employeeId;

  const empIdSpan = document.getElementById("empAssetsModalEmpId");
  const subEl = document.getElementById("empAssetsModalSub");
  const alertEl = document.getElementById("empAssetsAlert");
  const tbody = document.getElementById("empAssetsTableBody");
  const selectAllCb = document.getElementById("empAssetsSelectAll");
  const selectAllBtn = document.getElementById("empAssetsSelectAllBtn");

  if (empIdSpan) empIdSpan.textContent = employeeId;
  if (subEl) subEl.textContent = `All active assets assigned to ${employeeId}. Select items to return back to available inventory.`;
  if (alertEl) {
    alertEl.className = "alert hidden";
    alertEl.textContent = "";
  }
  if (selectAllCb) {
    selectAllCb.checked = false;
    selectAllCb.indeterminate = false;
    selectAllCb.disabled = true;
  }
  if (selectAllBtn) selectAllBtn.textContent = "Select All";
  updateEmpAssetSelectionCount(0, 0);

  if (tbody) {
    tbody.innerHTML = `<tr><td colspan="7" class="text-center loading-cell" style="padding: 24px;">Loading assigned assets for ${escapeHtml(employeeId)}...</td></tr>`;
  }

  openModal("employeeAssetsModal");

  try {
    const res = await apiRequest(`/assets?assigned_to=${encodeURIComponent(employeeId)}`);
    // Filter to assets that are assigned to this employee
    const assignedAssets = (res.data || []).filter(a => a.assigned_to === employeeId && a.status === "ASSIGNED");

    if (assignedAssets.length === 0) {
      tbody.innerHTML = `<tr><td colspan="7" class="text-center text-muted" style="padding: 28px;">No hardware assets are currently assigned to <strong>${escapeHtml(employeeId)}</strong>.</td></tr>`;
      if (selectAllCb) selectAllCb.disabled = true;
      if (selectAllBtn) selectAllBtn.disabled = true;
      updateEmpAssetSelectionCount(0, 0);
      return;
    }

    if (selectAllCb) selectAllCb.disabled = false;
    if (selectAllBtn) selectAllBtn.disabled = false;

    tbody.innerHTML = assignedAssets.map(a => {
      const specsSummary = a.specs ? Object.entries(a.specs).map(([k, v]) => `${k}: ${v}`).join(", ") : "-";
      return `
        <tr>
          <td style="text-align: center;">
            <input type="checkbox" class="emp-asset-checkbox" value="${escapeHtml(a.asset_id)}" onchange="handleEmpAssetCheckboxChange()" style="cursor: pointer; transform: scale(1.15);">
          </td>
          <td><strong>${escapeHtml(a.asset_id)}</strong></td>
          <td><span class="badge badge-low">${escapeHtml(a.type)}</span></td>
          <td>${escapeHtml(a.brand)} ${escapeHtml(a.model)}</td>
          <td><code>${escapeHtml(a.serial_number)}</code></td>
          <td><small class="text-secondary">${escapeHtml(specsSummary)}</small></td>
          <td>
            <button type="button" class="btn btn-xs btn-outline-danger" onclick="returnSingleEmpAsset('${escapeHtml(a.asset_id)}')">Return</button>
          </td>
        </tr>
      `;
    }).join("");

    updateEmpAssetSelectionCount(0, assignedAssets.length);
  } catch (err) {
    console.error("Failed loading employee assets:", err);
    if (tbody) {
      tbody.innerHTML = `<tr><td colspan="7" class="text-center text-muted" style="padding: 20px; color: var(--color-critical-text);">Error loading assets: ${escapeHtml(err.message)}</td></tr>`;
    }
  }
};

window.handleSelectAllEmpAssets = function(masterCheckbox) {
  const checkboxes = document.querySelectorAll(".emp-asset-checkbox");
  checkboxes.forEach(cb => { cb.checked = masterCheckbox.checked; });
  syncEmpAssetSelectionState();
};

window.toggleSelectAllBtnClick = function() {
  const checkboxes = document.querySelectorAll(".emp-asset-checkbox");
  if (checkboxes.length === 0) return;
  const anyUnchecked = Array.from(checkboxes).some(cb => !cb.checked);
  checkboxes.forEach(cb => { cb.checked = anyUnchecked; });
  syncEmpAssetSelectionState();
};

window.handleEmpAssetCheckboxChange = function() {
  syncEmpAssetSelectionState();
};

function syncEmpAssetSelectionState() {
  const checkboxes = document.querySelectorAll(".emp-asset-checkbox");
  const checked = Array.from(checkboxes).filter(cb => cb.checked);
  const masterCb = document.getElementById("empAssetsSelectAll");
  const selectAllBtn = document.getElementById("empAssetsSelectAllBtn");

  if (masterCb) {
    masterCb.checked = checkboxes.length > 0 && checked.length === checkboxes.length;
    masterCb.indeterminate = checked.length > 0 && checked.length < checkboxes.length;
  }

  if (selectAllBtn) {
    selectAllBtn.textContent = (checked.length === checkboxes.length && checkboxes.length > 0) ? "Deselect All" : "Select All";
  }

  updateEmpAssetSelectionCount(checked.length, checkboxes.length);
}

function updateEmpAssetSelectionCount(checkedCount, totalCount) {
  const counterEl = document.getElementById("empAssetsSelectedCounter");
  const countSpan = document.getElementById("empAssetsReturnBtnCount");
  const returnBtn = document.getElementById("returnSelectedAssetsBtn");

  if (counterEl) {
    counterEl.textContent = `${checkedCount} of ${totalCount} selected`;
    counterEl.className = checkedCount > 0 ? "badge badge-assigned" : "badge badge-low";
  }
  if (countSpan) {
    countSpan.textContent = checkedCount;
  }
  if (returnBtn) {
    returnBtn.disabled = checkedCount === 0;
  }
}

window.returnSingleEmpAsset = async function(assetId) {
  if (!confirm(`Return asset ${assetId} to inventory?`)) return;
  try {
    await apiRequest(`/assets/${assetId}/return`, "POST");
    await refreshAllAssetViews();
    if (currentViewingEmpId) {
      openEmployeeAssetsModal(currentViewingEmpId);
    }
  } catch (err) {
    alert("Return error: " + err.message);
  }
};

window.handleReturnSelectedAssets = async function() {
  const checkedCbs = document.querySelectorAll(".emp-asset-checkbox:checked");
  const assetIds = Array.from(checkedCbs).map(cb => cb.value);
  if (assetIds.length === 0) return;

  if (!confirm(`Return ${assetIds.length} selected asset(s) assigned to ${currentViewingEmpId} back to available inventory?`)) {
    return;
  }

  const returnBtn = document.getElementById("returnSelectedAssetsBtn");
  const alertEl = document.getElementById("empAssetsAlert");
  if (returnBtn) returnBtn.disabled = true;

  try {
    const res = await apiRequest("/assets/return-batch", "POST", { asset_ids: assetIds });
    if (alertEl) {
      alertEl.className = "alert alert-success";
      alertEl.textContent = res.message || `Successfully returned ${assetIds.length} asset(s).`;
      alertEl.classList.remove("hidden");
    }

    await refreshAllAssetViews();
    setTimeout(() => {
      if (currentViewingEmpId) {
        openEmployeeAssetsModal(currentViewingEmpId);
      }
    }, 700);
  } catch (err) {
    console.error("Batch return error:", err);
    if (alertEl) {
      alertEl.className = "alert alert-danger";
      alertEl.textContent = "Error returning assets: " + err.message;
      alertEl.classList.remove("hidden");
    }
    if (returnBtn) returnBtn.disabled = false;
  }
};

async function refreshAllAssetViews() {
  await Promise.all([
    loadAssets(),
    loadAvailableAssets(),
    loadAnalytics(),
  ]);
}

// =====================================================================
// Analytics & SLA Reporting
// =====================================================================

async function loadAnalytics() {
  if (currentRole === "EMPLOYEE") {
    // Employees do not have permission to view enterprise SLA analytics
    return;
  }
  try {
    const slaRes = await apiRequest("/reports/sla");
    const assetsRes = await apiRequest("/assets");
    const ticketsRes = await apiRequest("/tickets");

    if (assetsRes.data) {
      document.getElementById("kpiTotalAssets").textContent = assetsRes.data.length;
      const assignedCount = assetsRes.data.filter(a => a.status === "ASSIGNED").length;
      document.getElementById("kpiAssignedAssets").textContent = `${assignedCount} assigned`;
    }

    if (ticketsRes.data) {
      const openCount = ticketsRes.data.filter(t => t.status !== "CLOSED" && t.status !== "RESOLVED").length;
      const criticalCount = ticketsRes.data.filter(t => t.priority === "CRITICAL" && t.status !== "CLOSED").length;
      document.getElementById("kpiOpenTickets").textContent = openCount;
      document.getElementById("kpiCriticalTickets").textContent = `${criticalCount} critical SLA`;
    }

    if (slaRes.data) {
      const s = slaRes.data;
      document.getElementById("kpiSlaCompliance").textContent = `${s.compliance_rate_percent}%`;
      document.getElementById("kpiBreachedCount").textContent = `${s.breached_count} breaches`;
      document.getElementById("kpiAvgResolution").textContent = `${s.average_resolution_hours}h`;

      // Fill Analytics tab grid
      document.getElementById("slaSumTotal").textContent = s.total_tickets;
      document.getElementById("slaSumActive").textContent = s.active_tickets;
      document.getElementById("slaSumResolved").textContent = s.resolved_tickets;
      document.getElementById("slaSumBreached").textContent = s.breached_count;
      document.getElementById("slaSumRate").textContent = `${s.compliance_rate_percent}%`;
      document.getElementById("slaSumAvgHours").textContent = `${s.average_resolution_hours} hrs`;
    }
  } catch (err) {
    console.error("Failed loading analytics:", err);
  }
}

// =====================================================================


// =====================================================================
// UI Modal Helpers
// =====================================================================

window.openModal = function(id) {
  const modal = document.getElementById(id);
  if (modal) modal.classList.remove("hidden");
};

window.closeModal = function(id) {
  const modal = document.getElementById(id);
  if (modal) modal.classList.add("hidden");
};

window.hideModal = window.closeModal;
window.showModal = window.openModal;

function escapeHtml(str) {
  if (!str) return "";
  return String(str).replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;").replace(/"/g, "&quot;");
}
