const MONTHS_PT = [
  'janeiro','fevereiro','março','abril','maio','junho',
  'julho','agosto','setembro','outubro','novembro','dezembro',
];

function fmtDate(iso) {
  const [, m, d] = iso.split('-').map(Number);
  return `${d} de ${MONTHS_PT[m - 1]}`;
}

function fmtPeriodo(c) {
  return `${fmtDate(c.data_inicio)} a ${fmtDate(c.data_fim)}`;
}

const UNIDADE_MAP = {
  'vila-mariana':    { label: 'Vila Mariana',   filter: 'vilamariana' },
  'jardim-paulista': { label: 'Jardim Paulista', filter: 'jardimpaulista' },
};

// IDs das campanhas já resgatadas pelo usuário logado
let resgatados = new Set();

function getToken() {
  return localStorage.getItem('aromap_token');
}

function buildCard(c) {
  const isAtiva     = c.status === 'ativa';
  const jaResgatado = resgatados.has(c.id);

  const badgeClass = isAtiva ? 'badge-active'  : 'badge-scheduled';
  const badgeLabel = isAtiva ? 'Ativa agora'   : 'Em breve';

  const imgContent  = c.imagem_path
    ? `<img src="${c.imagem_path}" alt="${c.nome}" class="offer-img" />`
    : `<div class="placeholder-icon">🗓</div>`;
  const imgWrapClass = c.imagem_path
    ? 'offer-image-wrap'
    : 'offer-image-wrap offer-image-placeholder';

  const horario      = c.hora_inicio && c.hora_fim ? `${c.hora_inicio} às ${c.hora_fim}` : 'A definir';
  const horarioClass = c.hora_inicio ? 'offer-time-row' : 'offer-time-row offer-time-muted';

  const unitFilter = c.unidades && c.unidades.length === 1
    ? (UNIDADE_MAP[c.unidades[0]]?.filter || 'outras')
    : 'todas';

  const unitLabel = c.unidades && c.unidades.length === 1
    ? (UNIDADE_MAP[c.unidades[0]]?.label || c.unidades[0])
    : 'Todas as unidades';

  let btn;
  if (!isAtiva) {
    btn = `<button class="offer-btn-full btn-disabled" disabled>Disponível em breve</button>`;
  } else if (jaResgatado) {
    btn = `<button class="offer-btn-full btn-redeemed" disabled>Já resgatado</button>`;
  } else {
    btn = `<button class="offer-btn-full" data-campanha-id="${c.id}" aria-label="Resgatar oferta ${c.nome}">Resgatar benefício</button>`;
  }

  return `
    <article class="offer-card-full" data-unit="${unitFilter}" data-status="${isAtiva ? 'active' : 'scheduled'}">
      <div class="${imgWrapClass}">
        ${imgContent}
        <span class="offer-badge ${badgeClass}">${badgeLabel}</span>
      </div>
      <div class="offer-body">
        <div class="offer-meta">
          <span class="offer-unit-tag">📍 ${unitLabel}</span>
          <span class="offer-period-tag">${fmtPeriodo(c)}</span>
        </div>
        <h3>${c.nome}</h3>
        <p class="offer-desc-full">${c.descricao}</p>
        <div class="${horarioClass}">
          <span class="clock-icon">🕒</span>
          <span>${horario}</span>
        </div>
        ${btn}
      </div>
    </article>`;
}

async function resgatar(btn) {
  const campanhaId = btn.dataset.campanhaId;
  const token      = getToken();

  if (!token) { window.location.href = '/login'; return; }

  btn.disabled    = true;
  btn.textContent = 'Aguarde...';

  try {
    const res = await fetch(`/api/campanhas/${campanhaId}/resgatar`, {
      method:  'POST',
      headers: { 'Authorization': `Bearer ${token}` },
    });

    if (res.status === 401) {
      localStorage.removeItem('aromap_token');
      window.location.href = '/login';
      return;
    }

    if (res.status === 201 || res.status === 409) {
      btn.textContent = res.status === 201 ? 'Resgatado ✓' : 'Já resgatado';
      btn.classList.add('btn-redeemed');
      resgatados.add(campanhaId);
      return;
    }

    // Erro inesperado — reabilita o botão
    const data = await res.json().catch(() => ({}));
    btn.disabled    = false;
    btn.textContent = data.detail || 'Erro ao resgatar';
    setTimeout(() => { btn.textContent = 'Resgatar benefício'; }, 3000);

  } catch {
    btn.disabled    = false;
    btn.textContent = 'Resgatar benefício';
  }
}

async function loadOfertas() {
  const token = getToken();
  if (!token) { window.location.href = '/login'; return; }

  const grid      = document.getElementById('offersGrid');
  const noResults = document.getElementById('noResults');

  grid.innerHTML = '<p style="padding:1rem;grid-column:1/-1">Carregando ofertas...</p>';

  try {
    const [campanhasRes, resgatesRes] = await Promise.all([
      fetch('/api/campanhas'),
      fetch('/api/me/resgates', { headers: { 'Authorization': `Bearer ${token}` } }),
    ]);

    if (resgatesRes.status === 401) {
      localStorage.removeItem('aromap_token');
      window.location.href = '/login';
      return;
    }

    if (resgatesRes.ok) {
      const resgateData = await resgatesRes.json();
      resgatados = new Set(resgateData.map(r => r.campanha_id));
    }

    const data     = await campanhasRes.json();
    const visiveis = Array.isArray(data)
      ? data.filter(c => c.status === 'ativa' || c.status === 'agendada')
      : [];

    grid.innerHTML = '';

    if (visiveis.length === 0) {
      noResults.style.display = 'block';
      return;
    }

    grid.innerHTML = visiveis.map(buildCard).join('');

    // Listener direto em cada botão de resgate
    grid.querySelectorAll('button[data-campanha-id]').forEach(btn => {
      btn.addEventListener('click', () => resgatar(btn));
    });

    activateFilters();

  } catch {
    grid.innerHTML = '<p style="padding:1rem;grid-column:1/-1">Erro ao carregar ofertas.</p>';
  }
}

function activateFilters() {
  const chips     = document.querySelectorAll('.filter-chip');
  const noResults = document.getElementById('noResults');

  function applyFilter(filter) {
    const cards = document.querySelectorAll('.offer-card-full');
    let visible = 0;
    cards.forEach(card => {
      let show = false;
      if (filter === 'all')            show = true;
      else if (filter === 'active')    show = card.dataset.status === 'active';
      else if (filter === 'scheduled') show = card.dataset.status === 'scheduled';
      else                             show = card.dataset.unit === filter;
      card.style.display = show ? '' : 'none';
      if (show) visible++;
    });
    noResults.style.display = visible === 0 ? 'block' : 'none';
  }

  chips.forEach(chip => {
    chip.addEventListener('click', () => {
      chips.forEach(c => c.classList.remove('active'));
      chip.classList.add('active');
      applyFilter(chip.dataset.filter);
    });
  });
}

// ── Localização ───────────────────────────────────────────────────────────────
// Mantém a posição atualizada enquanto o usuário navega pelas ofertas

(function iniciarTracking() {
  const token = getToken();
  if (!token || !('geolocation' in navigator)) return;

  let lastSent = 0;
  const INTERVAL_MS = 5 * 60 * 1000;

  function enviar(lat, lon) {
    const agora = Date.now();
    if (agora - lastSent < INTERVAL_MS) return;
    lastSent = agora;
    fetch('/api/me/localizacao', {
      method:  'POST',
      headers: { 'Authorization': `Bearer ${token}`, 'Content-Type': 'application/json' },
      body:    JSON.stringify({ latitude: lat, longitude: lon }),
    }).catch(() => {});
  }

  navigator.geolocation.getCurrentPosition(
    pos => {
      enviar(pos.coords.latitude, pos.coords.longitude);
      navigator.geolocation.watchPosition(
        p => enviar(p.coords.latitude, p.coords.longitude),
        () => {},
        { enableHighAccuracy: true, maximumAge: 60000, timeout: 15000 },
      );
    },
    () => {},
    { enableHighAccuracy: true, timeout: 15000 },
  );
})();

loadOfertas();
