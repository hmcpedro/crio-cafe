const MONTHS_PT = [
  'janeiro','fevereiro','março','abril','maio','junho',
  'julho','agosto','setembro','outubro','novembro','dezembro',
];

function fmtDate(iso) {
  // "2025-05-20" → "20 de maio de 2025"
  const [y, m, d] = iso.split('-').map(Number);
  return `${d} de ${MONTHS_PT[m - 1]} de ${y}`;
}

function fmtPeriodo(c) {
  return `${fmtDate(c.data_inicio)} a ${fmtDate(c.data_fim)}`;
}

function unidadesLabel(unidades) {
  if (!unidades || unidades.length === 0) return '—';
  if (unidades.length > 1) return 'Todas as unidades';
  const map = { 'vila-mariana': 'Vila Mariana', 'jardim-paulista': 'Jardim Paulista' };
  return map[unidades[0]] || unidades[0];
}

function buildCard(c) {
  const badgeClass  = `badge-${c.status}`;
  const badgeLabel  = { ativa: 'Ativa', agendada: 'Agendada', encerrada: 'Encerrada' }[c.status] || c.status;
  const imgContent  = c.imagem_path
    ? `<img src="${c.imagem_path}" alt="${c.nome}" class="camp-image${c.status === 'encerrada' ? ' camp-image--dim' : ''}" />`
    : `<span class="placeholder-cal">📅</span>`;
  const wrapExtra   = c.imagem_path ? '' : ' camp-placeholder';

  return `
    <article class="camp-card" data-status="${c.status}">
      <div class="camp-image-wrap${wrapExtra}">
        ${imgContent}
        <span class="status-badge ${badgeClass}">${badgeLabel}</span>
      </div>
      <div class="camp-body">
        <h3>${c.nome}</h3>
        <p class="camp-period">${fmtPeriodo(c)}</p>
        <p class="camp-desc">${c.descricao}</p>
        <div class="camp-footer">
          <span class="camp-unit">${unidadesLabel(c.unidades)}</span>
          <a href="/admin/campanha-detalhe?id=${c.id}" class="btn-details">Ver Detalhes</a>
        </div>
      </div>
    </article>`;
}

async function loadCampanhas() {
  const grid      = document.getElementById('campaignsGrid');
  const noResults = document.getElementById('noResults');

  grid.innerHTML = '<p class="loading-msg">Carregando campanhas...</p>';

  try {
    const res  = await fetch('/api/campanhas');
    const data = await res.json();

    grid.innerHTML = '';

    if (!Array.isArray(data) || data.length === 0) {
      noResults.style.display = 'block';
      return;
    }

    data.forEach(c => { grid.innerHTML += buildCard(c); });

    // Re-ativa filtros sobre os cards renderizados
    activateFilters();

  } catch {
    grid.innerHTML = '<p class="loading-msg">Erro ao carregar campanhas.</p>';
  }
}

function activateFilters() {
  const chips     = document.querySelectorAll('.filter-chip');
  const noResults = document.getElementById('noResults');

  function applyFilter(filter) {
    const cards   = document.querySelectorAll('.camp-card');
    let visible   = 0;
    cards.forEach(card => {
      const show = filter === 'all' || card.dataset.status === filter;
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

loadCampanhas();
