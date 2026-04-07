// home.js — carrega usuário logado, campanhas ativas e resgates

const MONTHS_PT = [
  'janeiro','fevereiro','março','abril','maio','junho',
  'julho','agosto','setembro','outubro','novembro','dezembro',
];

function fmtDate(iso) {
  const [, m, d] = iso.split('-').map(Number);
  return `${d} de ${MONTHS_PT[m - 1]}`;
}

const UNIDADE_MAP = {
  'vila-mariana':    'Vila Mariana',
  'jardim-paulista': 'Jardim Paulista',
};

function unitLabel(c) {
  if (!c.unidades || c.unidades.length === 0) return 'Todas as unidades';
  if (c.unidades.length === 1) return UNIDADE_MAP[c.unidades[0]] || c.unidades[0];
  return 'Todas as unidades';
}

// IDs das campanhas já resgatadas pelo usuário logado
let resgatados = new Set();

function buildHero(c) {
  const periodo      = `${fmtDate(c.data_inicio)} a ${fmtDate(c.data_fim)}`;
  const jaResgatado  = resgatados.has(c.id);

  const imgEl = c.imagem_path
    ? `<img src="${c.imagem_path}" alt="${c.nome}" class="hero-banner-image" />`
    : `<div class="hero-banner-image hero-banner-placeholder"></div>`;

  const btn = jaResgatado
    ? `<button class="hero-button btn-redeemed" disabled>Já resgatado</button>`
    : `<button class="hero-button" data-campanha-id="${c.id}">Resgatar benefício</button>`;

  return `
    ${imgEl}
    <div class="hero-overlay">
      <h2>${c.nome}</h2>
      <p class="hero-period">${periodo}</p>
      <div class="hero-divider">
        <span></span>
        <i>✦</i>
        <span></span>
      </div>
      <p class="hero-offer">${c.descricao}</p>
      ${btn}
      <img src="/static/img/logo-aromap.png" alt="Aromap" class="hero-mini-logo" />
    </div>`;
}

function buildCard(c) {
  const horario     = c.hora_inicio && c.hora_fim ? `${c.hora_inicio} às ${c.hora_fim}` : null;
  const unidade     = unitLabel(c);
  const jaResgatado = resgatados.has(c.id);

  const imgEl = c.imagem_path
    ? `<img src="${c.imagem_path}" alt="${c.nome}" class="offer-card-image" />`
    : `<div class="offer-card-image offer-card-placeholder"></div>`;

  const btn = jaResgatado
    ? `<button class="offer-btn btn-redeemed" disabled>Já resgatado</button>`
    : `<button class="offer-btn" data-campanha-id="${c.id}">Quero essa oferta</button>`;

  return `
    <article class="offer-card">
      ${imgEl}
      <div class="offer-card-body">
        <h4>${c.nome}</h4>
        ${horario ? `<p class="offer-time">${horario}</p>` : ''}
        <p class="offer-unit">${unidade}</p>
        <p class="offer-desc">${c.descricao}</p>
        ${btn}
      </div>
    </article>`;
}

async function resgatar(btn) {
  const campanhaId = btn.dataset.campanhaId;
  const token      = localStorage.getItem('aromap_token');

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

    const data = await res.json().catch(() => ({}));
    btn.disabled    = false;
    btn.textContent = data.detail || 'Erro ao resgatar';
    setTimeout(() => { btn.textContent = 'Resgatar benefício'; }, 3000);

  } catch {
    btn.disabled    = false;
    btn.textContent = 'Resgatar benefício';
  }
}

async function loadCampanhas(token) {
  const heroBanner    = document.getElementById('heroBanner');
  const offersSection = document.getElementById('offersSection');
  const offersGrid    = document.getElementById('offersGrid');

  try {
    const [campanhasRes, resgatesRes] = await Promise.all([
      fetch('/api/campanhas'),
      fetch('/api/me/resgates', { headers: { 'Authorization': `Bearer ${token}` } }),
    ]);

    if (resgatesRes.ok) {
      const resgateData = await resgatesRes.json();
      resgatados = new Set(resgateData.map(r => r.campanha_id));
    }

    const data   = await campanhasRes.json();
    const ativas = Array.isArray(data) ? data.filter(c => c.status === 'ativa') : [];

    // Hero: campanha ativa mais recente
    if (ativas.length > 0) {
      heroBanner.innerHTML     = buildHero(ativas[0]);
      heroBanner.style.display = '';

      const heroBtn = heroBanner.querySelector('button[data-campanha-id]');
      if (heroBtn) heroBtn.addEventListener('click', () => resgatar(heroBtn));
    } else {
      heroBanner.style.display = 'none';
    }

    // Grid "Ativas agora": campanhas ativas restantes (até 3)
    const gridCampanhas = ativas.slice(1, 4);
    if (gridCampanhas.length > 0) {
      offersGrid.innerHTML        = gridCampanhas.map(buildCard).join('');
      offersSection.style.display = '';

      offersGrid.querySelectorAll('button[data-campanha-id]').forEach(btn => {
        btn.addEventListener('click', () => resgatar(btn));
      });
    } else {
      offersSection.style.display = 'none';
    }

  } catch (err) {
    console.error('Erro ao carregar campanhas:', err);
    heroBanner.style.display    = 'none';
    offersSection.style.display = 'none';
  }
}

// ── Localização ───────────────────────────────────────────────────────────────

const LOC_INTERVAL_MS  = 5 * 60 * 1000;  // envia a cada 5 minutos no máximo
let   _locWatchId      = null;
let   _locLastSent     = 0;

async function enviarLocalizacao(lat, lon, token) {
  const agora = Date.now();
  if (agora - _locLastSent < LOC_INTERVAL_MS) return; // evita spam
  _locLastSent = agora;

  try {
    const res = await fetch('/api/me/localizacao', {
      method:  'POST',
      headers: { 'Authorization': `Bearer ${token}`, 'Content-Type': 'application/json' },
      body:    JSON.stringify({ latitude: lat, longitude: lon }),
    });
    if (res.ok) {
      console.log(`[Localização] Enviada: ${lat.toFixed(5)}, ${lon.toFixed(5)}`);
    } else {
      console.warn('[Localização] Falha ao enviar:', res.status);
    }
  } catch (err) {
    console.warn('[Localização] Erro de rede:', err.message);
  }
}

async function ativarPermissaoLocalizacao(token) {
  try {
    await fetch('/api/me/permissao-localizacao?permitir=true', {
      method:  'PATCH',
      headers: { 'Authorization': `Bearer ${token}` },
    });
  } catch { /* silencioso */ }
}

function iniciarTracking(token) {
  if (!('geolocation' in navigator)) {
    console.info('[Localização] Geolocation não suportado neste browser.');
    return;
  }

  navigator.geolocation.getCurrentPosition(
    async pos => {
      await ativarPermissaoLocalizacao(token);
      await enviarLocalizacao(pos.coords.latitude, pos.coords.longitude, token);

      // Continua atualizando enquanto a página estiver aberta
      _locWatchId = navigator.geolocation.watchPosition(
        pos => enviarLocalizacao(pos.coords.latitude, pos.coords.longitude, token),
        err => console.info('[Localização] watchPosition erro:', err.message),
        { enableHighAccuracy: true, maximumAge: 60000, timeout: 15000 },
      );
    },
    err => {
      // Usuário negou ou não tem GPS — não bloqueia nada no sistema
      console.info('[Localização] Permissão negada ou indisponível:', err.message);
    },
    { enableHighAccuracy: true, timeout: 15000 },
  );
}

// ── Init ──────────────────────────────────────────────────────────────────────

(async function () {
  const token = localStorage.getItem('aromap_token');

  if (!token) {
    window.location.href = '/login';
    return;
  }

  const cachedName = localStorage.getItem('aromap_name');
  if (cachedName) {
    document.getElementById('userName').textContent = cachedName.split(' ')[0];
  }

  try {
    const res = await fetch('/api/me', {
      headers: {
        'Authorization': `Bearer ${token}`,
        'Content-Type':  'application/json',
      },
    });

    if (res.status === 401) {
      localStorage.removeItem('aromap_token');
      localStorage.removeItem('aromap_name');
      window.location.href = '/login';
      return;
    }

    if (res.ok) {
      const data      = await res.json();
      const firstName = data.name.trim().split(' ')[0];
      document.getElementById('userName').textContent = firstName;
      localStorage.setItem('aromap_name', data.name);
    }
  } catch (err) {
    console.error('Erro ao carregar usuário:', err);
  }

  // Inicia tracking de localização (pede permissão ao browser)
  iniciarTracking(token);

  loadCampanhas(token);
})();
