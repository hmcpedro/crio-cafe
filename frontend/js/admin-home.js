const MONTHS_PT = [
  'janeiro','fevereiro','março','abril','maio','junho',
  'julho','agosto','setembro','outubro','novembro','dezembro',
];

function fmtDate(iso) {
  const [y, m, d] = iso.split('-').map(Number);
  return `${d} de ${MONTHS_PT[m - 1]}`;
}

function buildCard(c) {
  const statusLabel = { ativa: 'Ativa', agendada: 'Agendada', encerrada: 'Encerrada' }[c.status] || c.status;
  const statusClass = c.status === 'encerrada' ? ' card-status--ended' : '';

  const imgTag = c.imagem_path
    ? `<img src="${c.imagem_path}" alt="${c.nome}" class="card-image" />`
    : `<div class="card-image card-image--placeholder"><span>📅</span></div>`;

  const periodo = `${fmtDate(c.data_inicio)} a ${fmtDate(c.data_fim)}`;

  return `
    <article class="campaign-card">
      <div class="card-image-wrap">
        ${imgTag}
        <div class="card-overlay">
          <div class="card-overlay-top">
            <h2>${c.nome}</h2>
            <p class="card-dates">${periodo}</p>
            <p class="card-status${statusClass}">${statusLabel}</p>
          </div>
          <a href="/admin/campanha-detalhe?id=${c.id}" class="card-details-btn">Ver Detalhes</a>
          <img src="/static/img/logo-aromap.png" alt="Aromap" class="card-mini-logo" />
        </div>
      </div>
      <div class="card-footer">De ${fmtDate(c.data_inicio)} à ${fmtDate(c.data_fim)}</div>
    </article>`;
}

async function loadHome() {
  const grid         = document.getElementById('campaignGrid');
  const listaAtivas  = document.getElementById('listaAtivas');
  const metAtivas    = document.getElementById('metAtivas');
  const metTotal     = document.getElementById('metTotal');
  const metNotifs    = document.getElementById('metNotifs');

  try {
    const res  = await fetch('/api/campanhas');
    const data = await res.json();

    if (!Array.isArray(data) || data.length === 0) {
      grid.innerHTML = '<p class="loading-msg" style="grid-column:1/-1;padding:2rem">Nenhuma campanha cadastrada ainda.</p>';
      if (listaAtivas) listaAtivas.innerHTML = '<li style="color:#999">—</li>';
      return;
    }

    // Cards: últimas 3 (já vêm ordenadas por criado_em DESC)
    const recentes = data.slice(0, 3);
    grid.innerHTML = recentes.map(buildCard).join('');

    // Lista de campanhas ativas
    const ativas = data.filter(c => c.status === 'ativa');
    if (listaAtivas) {
      listaAtivas.innerHTML = ativas.length
        ? ativas.map(c => `<li><a href="/admin/campanha-detalhe?id=${c.id}">${c.nome}</a></li>`).join('')
        : '<li style="color:#999">Nenhuma campanha ativa</li>';
    }

    // Métricas
    const totalNotifs = data.reduce((sum, c) => sum + c.notificacoes.filter(n => n.status === 'enviada').length, 0);
    if (metAtivas) metAtivas.textContent = ativas.length;
    if (metTotal)  metTotal.textContent  = data.length;
    if (metNotifs) metNotifs.textContent = totalNotifs;

  } catch {
    grid.innerHTML = '<p style="grid-column:1/-1;padding:2rem">Erro ao carregar campanhas.</p>';
  }
}

loadHome();
