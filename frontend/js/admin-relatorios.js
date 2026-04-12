const MONTHS_PT = [
  'janeiro','fevereiro','março','abril','maio','junho',
  'julho','agosto','setembro','outubro','novembro','dezembro',
];

function fmtShort(iso) {
  // "2026-04-10" → "10 abr"
  const [, m, d] = iso.split('-').map(Number);
  return `${d} ${MONTHS_PT[m - 1].slice(0, 3)}`;
}

function fmtPeriodoShort(c) {
  return `${fmtShort(c.data_inicio)}–${fmtShort(c.data_fim)}`;
}

// ── Filtro por período ─────────────────────────────────────────────────────
function campanhasDoPeriodo(data, periodo) {
  const now   = new Date();
  const corte = new Date(now);

  if (periodo === 'mes')    corte.setMonth(now.getMonth() - 1);
  else if (periodo === '3m') corte.setMonth(now.getMonth() - 3);
  else if (periodo === 'ano') corte.setFullYear(now.getFullYear() - 1);
  else return data; // tudo

  return data.filter(c => new Date(c.criado_em) >= corte);
}

// ── Builders ──────────────────────────────────────────────────────────────
function buildTableRow(c) {
  const statusLabel = { ativa: 'Ativa', agendada: 'Agendada', encerrada: 'Encerrada' }[c.status] || c.status;
  const badgeClass  = `badge-${c.status}`;
  const rowClass    = c.status === 'encerrada' ? ' class="row-dim"' : '';

  const notificados = c.total_notificados ?? 0;
  const resgates    = c.total_resgates    ?? 0;
  const taxa        = notificados > 0 ? ((resgates / notificados) * 100).toFixed(1) + '%' : '—';
  const taxaPct     = notificados > 0 ? Math.min((resgates / notificados) * 100, 100) : 0;

  const fillClass = c.status === 'encerrada' ? ' bar-fill--dim' : '';

  return `
    <tr${rowClass}>
      <td class="td-name">
        <a href="/admin/campanha-detalhe?id=${c.id}" style="color:inherit;text-decoration:none">${c.nome}</a>
      </td>
      <td><span class="${badgeClass}">${statusLabel}</span></td>
      <td>${fmtPeriodoShort(c)}</td>
      <td>${notificados}</td>
      <td>${resgates}</td>
      <td>${taxa}</td>
      <td class="td-bar"><div class="bar-track"><div class="bar-fill${fillClass}" style="width:${taxaPct}%"></div></div></td>
    </tr>`;
}

function buildUnitCard(nome, slug, campanhas) {
  const campanhasDaUnidade = campanhas.filter(c =>
    !c.unidades || c.unidades.length === 0 || c.unidades.includes(slug)
  );
  const totalNotificados = campanhasDaUnidade.reduce((s, c) => s + (c.total_notificados ?? 0), 0);
  const totalResgates    = campanhasDaUnidade.reduce((s, c) => s + (c.total_resgates    ?? 0), 0);
  const ativas           = campanhasDaUnidade.filter(c => c.status === 'ativa').length;
  const taxaPct          = totalNotificados > 0 ? Math.min((totalResgates / totalNotificados) * 100, 100) : 0;

  return `
    <div class="unit-card">
      <h3>${nome}</h3>
      <div class="unit-stats">
        <div class="unit-stat">
          <strong>${totalNotificados}</strong>
          <span>Notificados</span>
        </div>
        <div class="unit-stat">
          <strong>${totalResgates}</strong>
          <span>Resgates</span>
        </div>
        <div class="unit-stat unit-stat--accent">
          <strong>${ativas}</strong>
          <span>Campanhas ativas</span>
        </div>
      </div>
      <div class="unit-bar-wrap">
        <div class="unit-bar-track">
          <div class="unit-bar-fill" style="width:${taxaPct.toFixed(1)}%"></div>
        </div>
      </div>
    </div>`;
}

// ── Renderização principal ─────────────────────────────────────────────────
let _allData = [];

function render(periodo) {
  const campanhas = campanhasDoPeriodo(_allData, periodo);

  // Métricas gerais
  const ativas            = campanhas.filter(c => c.status === 'ativa').length;
  const totalNotificados  = campanhas.reduce((s, c) => s + (c.total_notificados ?? 0), 0);
  const totalResgates     = campanhas.reduce((s, c) => s + (c.total_resgates    ?? 0), 0);

  document.getElementById('metNotifs').textContent   = totalNotificados;
  document.getElementById('metEnviadas').textContent = totalResgates;
  document.getElementById('metAtivas').textContent   = ativas;
  document.getElementById('metTotal').textContent    = campanhas.length;

  // Tabela
  const tbody = document.getElementById('reportTbody');
  tbody.innerHTML = campanhas.length
    ? campanhas.map(buildTableRow).join('')
    : '<tr><td colspan="7" style="text-align:center;padding:2rem;color:#999">Nenhuma campanha no período selecionado.</td></tr>';

  // Engajamento por unidade
  const unitsGrid = document.getElementById('unitsGrid');
  unitsGrid.innerHTML =
    buildUnitCard('Vila Mariana',    'vila-mariana',    campanhas) +
    buildUnitCard('Jardim Paulista', 'jardim-paulista', campanhas);
}

async function loadRelatorios() {
  try {
    const res  = await fetch('/api/campanhas');
    _allData   = await res.json();
    if (!Array.isArray(_allData)) _allData = [];
    render('mes');
  } catch {
    document.getElementById('reportTbody').innerHTML =
      '<tr><td colspan="7" style="padding:2rem;color:#999">Erro ao carregar dados.</td></tr>';
  }
}

// ── Filtro de período ──────────────────────────────────────────────────────
document.querySelectorAll('.period-btn').forEach(btn => {
  btn.addEventListener('click', () => {
    document.querySelectorAll('.period-btn').forEach(b => b.classList.remove('active'));
    btn.classList.add('active');
    render(btn.dataset.period);
  });
});

loadRelatorios();
