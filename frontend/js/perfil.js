// perfil.js — integração com o backend

// ── Utilitários de autenticação ────────────────────────────────────────────

function getToken() {
  return localStorage.getItem("aromap_token");
}

function authHeaders() {
  return {
    "Content-Type": "application/json",
    "Authorization": `Bearer ${getToken()}`,
  };
}

function redirectToLogin() {
  localStorage.removeItem("aromap_token");
  localStorage.removeItem("aromap_name");
  window.location.href = "/login";
}

async function apiFetch(path, options = {}) {
  const res = await fetch(path, {
    ...options,
    headers: { ...authHeaders(), ...(options.headers || {}) },
  });
  if (res.status === 401) { redirectToLogin(); return null; }
  return res;
}

// ── Iniciais do avatar ─────────────────────────────────────────────────────

function getInitials(name) {
  return name
    .trim()
    .split(" ")
    .filter(Boolean)
    .slice(0, 2)
    .map(w => w[0].toUpperCase())
    .join("");
}

const avatarEl  = document.getElementById("avatarInitials");
const nameInput = document.getElementById("name");

nameInput.addEventListener("input", () => {
  avatarEl.textContent = getInitials(nameInput.value) || "?";
});

// ── Carregar perfil ────────────────────────────────────────────────────────

async function loadProfile() {
  if (!getToken()) { redirectToLogin(); return; }

  const res = await apiFetch("/api/me");
  if (!res || !res.ok) return;

  const data = await res.json();

  document.getElementById("profileName").textContent  = data.name;
  document.getElementById("profileEmail").textContent = data.email;
  document.getElementById("profileSince").textContent = `Membro desde ${data.member_since}`;

  nameInput.value                         = data.name;
  document.getElementById("email").value = data.email;
  document.getElementById("phone").value = data.phone;

  avatarEl.textContent = getInitials(data.name);
}

// ── Carregar preferências ──────────────────────────────────────────────────

async function loadPreferencias() {
  const res = await apiFetch("/api/me/preferencias");
  if (!res || !res.ok) return;

  const data = await res.json();

  document.getElementById("pref-cafes-quentes").checked    = data.cafes_quentes;
  document.getElementById("pref-cafes-gelados").checked    = data.cafes_gelados;
  document.getElementById("pref-paes-salgados").checked    = data.paes_salgados;
  document.getElementById("pref-doces-sobremesas").checked = data.doces_sobremesas;
  document.getElementById("pref-notif-email").checked      = data.notif_email;
}

// ── Formulário de dados pessoais ───────────────────────────────────────────

document.getElementById("profileForm").addEventListener("submit", async (e) => {
  e.preventDefault();
  const msg = document.getElementById("formMessage");
  msg.textContent = "";
  msg.className   = "form-message";

  const body = {
    name:  nameInput.value.trim(),
    phone: document.getElementById("phone").value.trim(),
  };

  const res = await apiFetch("/api/me", { method: "PATCH", body: JSON.stringify(body) });
  if (!res) return;

  const data = await res.json();

  if (!res.ok) {
    msg.textContent = data.detail || "Erro ao salvar dados.";
    msg.classList.add("msg-error");
    return;
  }

  document.getElementById("profileName").textContent = data.name;
  avatarEl.textContent = getInitials(data.name);

  msg.textContent = "Dados salvos com sucesso.";
  msg.classList.add("msg-success");
  setTimeout(() => { msg.textContent = ""; msg.className = "form-message"; }, 3000);
});

// ── Formulário de senha ────────────────────────────────────────────────────

document.getElementById("passwordForm").addEventListener("submit", async (e) => {
  e.preventDefault();
  const msg     = document.getElementById("passwordMessage");
  const newPw   = document.getElementById("newPassword").value;
  const confirm = document.getElementById("confirmNewPassword").value;

  msg.textContent = "";
  msg.className   = "form-message";

  if (newPw.length < 6) {
    msg.textContent = "A nova senha deve ter pelo menos 6 caracteres.";
    msg.classList.add("msg-error");
    return;
  }

  if (newPw !== confirm) {
    msg.textContent = "As senhas não coincidem.";
    msg.classList.add("msg-error");
    return;
  }

  const body = {
    current_password: document.getElementById("currentPassword").value,
    new_password:     newPw,
    confirm_password: confirm,
  };

  const res = await apiFetch("/api/me/password", { method: "PATCH", body: JSON.stringify(body) });
  if (!res) return;

  if (res.status === 204) {
    msg.textContent = "Senha alterada com sucesso.";
    msg.classList.add("msg-success");
    e.target.reset();
    setTimeout(() => { msg.textContent = ""; msg.className = "form-message"; }, 3000);
    return;
  }

  const data = await res.json();
  msg.textContent = data.detail || "Erro ao alterar senha.";
  msg.classList.add("msg-error");
});

// ── Salvar preferências ────────────────────────────────────────────────────

document.getElementById("savePrefs").addEventListener("click", async () => {
  const msg = document.getElementById("prefsMessage");
  msg.textContent = "";
  msg.className   = "form-message";

  const body = {
    cafes_quentes:    document.getElementById("pref-cafes-quentes").checked,
    cafes_gelados:    document.getElementById("pref-cafes-gelados").checked,
    paes_salgados:    document.getElementById("pref-paes-salgados").checked,
    doces_sobremesas: document.getElementById("pref-doces-sobremesas").checked,
    notif_email:      document.getElementById("pref-notif-email").checked,
  };

  const res = await apiFetch("/api/me/preferencias", { method: "PUT", body: JSON.stringify(body) });
  if (!res) return;

  if (res.ok) {
    msg.textContent = "Preferências salvas.";
    msg.classList.add("msg-success");
    setTimeout(() => { msg.textContent = ""; msg.className = "form-message"; }, 3000);
  } else {
    const data = await res.json();
    msg.textContent = data.detail || "Erro ao salvar preferências.";
    msg.classList.add("msg-error");
  }
});

// ── Logout ─────────────────────────────────────────────────────────────────

document.querySelector(".btn-logout")?.addEventListener("click", (e) => {
  e.preventDefault();
  redirectToLogin();
});

// ── Histórico de resgates ──────────────────────────────────────────────────

const MONTHS_PT = [
  'janeiro','fevereiro','março','abril','maio','junho',
  'julho','agosto','setembro','outubro','novembro','dezembro',
];

function fmtDateTime(iso) {
  const dt    = new Date(iso);
  const day   = dt.getDate();
  const month = MONTHS_PT[dt.getMonth()];
  const hh    = String(dt.getHours()).padStart(2, '0');
  const mm    = String(dt.getMinutes()).padStart(2, '0');
  return `${day} de ${month}, ${hh}h${mm}`;
}

async function loadHistorico() {
  const list  = document.getElementById('historyList');
  const empty = document.getElementById('historyEmpty');

  const res = await apiFetch('/api/me/resgates');
  if (!res || !res.ok) return;

  const data = await res.json();

  if (data.length === 0) {
    empty.style.display = 'block';
    return;
  }

  list.innerHTML = data.map(r => {
    const isExpired  = r.campanha_status === 'encerrada';
    const dotClass   = isExpired ? 'history-dot history-dot-expired' : 'history-dot';
    const statusCls  = isExpired ? 'history-status status-expired'   : 'history-status status-used';
    const statusText = isExpired ? 'Expirado' : 'Resgatado';

    return `
      <li class="history-item">
        <div class="${dotClass}"></div>
        <div class="history-info">
          <span class="history-title">${r.campanha_nome}</span>
          <span class="history-date">${fmtDateTime(r.resgatado_em)}</span>
        </div>
        <span class="${statusCls}">${statusText}</span>
      </li>`;
  }).join('');
}

// ── Init ───────────────────────────────────────────────────────────────────

loadProfile();
loadPreferencias();
loadHistorico();
