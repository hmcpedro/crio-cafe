const MONTHS_PT = [
  'janeiro','fevereiro','março','abril','maio','junho',
  'julho','agosto','setembro','outubro','novembro','dezembro',
];

function fmtDate(iso) {
  const [y, m, d] = iso.split('-').map(Number);
  return `${d} de ${MONTHS_PT[m - 1]} de ${y}`;
}

function tipoDescontoLabel(tipo, valor) {
  if (tipo === 'percentual') return valor != null ? `Desconto de ${valor}%` : 'Desconto percentual';
  if (tipo === 'fixo')       return valor != null ? `Desconto de R$ ${valor.toFixed(2)}` : 'Valor fixo';
  return 'Combo especial';
}

function unidadesLabel(unidades) {
  if (!unidades || unidades.length === 0) return '—';
  if (unidades.length > 1) return 'Todas as unidades';
  const map = { 'vila-mariana': 'Vila Mariana', 'jardim-paulista': 'Jardim Paulista' };
  return map[unidades[0]] || unidades[0];
}

function notifLabel(tipo, agendado_para) {
  if (tipo === 'imediata') return 'Imediata (enviada ao salvar)';
  if (tipo === 'manual')   return 'Manual';
  if (tipo === 'agendada' && agendado_para) {
    const dt = new Date(agendado_para);
    return `Agendada para ${dt.toLocaleString('pt-BR')}`;
  }
  return 'Agendada';
}

// ── Status de notificações ────────────────────────────────────────────────────

const STATUS_LABEL = {
  pendente:           { label: 'Pendente',           cls: 'ns-pendente'   },
  aguardando_disparo: { label: 'Aguardando disparo', cls: 'ns-aguardando' },
  enviando:           { label: 'Enviando…',          cls: 'ns-enviando'   },
  enviada:            { label: 'Enviada',             cls: 'ns-enviada'    },
};

function renderNotifStatus(notificacoes) {
  const wrap = document.getElementById('notifStatusWrap');
  if (!wrap) return;

  if (!notificacoes || notificacoes.length === 0) {
    wrap.innerHTML = '<p class="ns-empty">Nenhuma notificação registrada.</p>';
    return;
  }

  const rows = notificacoes.map(n => {
    const s = STATUS_LABEL[n.status] || { label: n.status, cls: 'ns-pendente' };
    const criadoEm = new Date(n.criado_em).toLocaleString('pt-BR');
    const enviadoEm = n.enviado_em
      ? new Date(n.enviado_em).toLocaleString('pt-BR')
      : '—';
    return `
      <div class="ns-row">
        <span class="ns-badge ${s.cls}">${s.label}</span>
        <span class="ns-meta">Tipo: <strong>${n.tipo}</strong></span>
        <span class="ns-meta">Criado: ${criadoEm}</span>
        <span class="ns-meta">Enviado: ${enviadoEm}</span>
      </div>`;
  }).join('');

  wrap.innerHTML = rows;
}

function setNotifLog(msg, tipo = 'info') {
  const el = document.getElementById('notifLog');
  if (!el) return;
  el.textContent = msg;
  el.className   = `notif-log notif-log--${tipo}`;
  el.style.display = msg ? '' : 'none';
}

async function dispararNotificacao(c) {
  if (!confirm(`Enviar notificação WhatsApp para todos os clientes sobre "${c.nome}"?\n\nO notificador.py precisa estar rodando na sua máquina.`)) return;

  const btnNotificar = document.getElementById('btnNotificar');
  btnNotificar.disabled    = true;
  btnNotificar.textContent = 'Enfileirando…';
  setNotifLog('Enviando solicitação ao servidor…', 'info');

  const token = localStorage.getItem('aromap_token');
  let r;
  try {
    r = await fetch(`/api/campanhas/${c.id}/notificar`, {
      method:  'POST',
      headers: token ? { Authorization: `Bearer ${token}` } : {},
    });
  } catch (err) {
    btnNotificar.disabled    = false;
    btnNotificar.textContent = 'Enviar notificação';
    setNotifLog(`Erro de rede: ${err.message}`, 'erro');
    return;
  }

  const data = await r.json().catch(() => ({}));

  if (r.ok) {
    btnNotificar.textContent = 'Disparado ✓';
    setNotifLog(
      `Disparo enfileirado com sucesso. O notificador.py irá enviar as mensagens em breve.\n` +
      `Status atual no banco: aguardando_disparo.\n` +
      `Aguarde ~10 segundos e recarregue a página para ver o status atualizado.`,
      'ok'
    );
    // Recarrega painel de notificações após 12s para refletir status do notificador
    setTimeout(async () => {
      const res2 = await fetch(`/api/campanhas/${c.id}`).catch(() => null);
      if (res2 && res2.ok) {
        const c2 = await res2.json();
        renderNotifStatus(c2.notificacoes);
      }
    }, 12000);
  } else {
    btnNotificar.disabled    = false;
    btnNotificar.textContent = 'Enviar notificação';
    setNotifLog(`Erro ${r.status}: ${data.detail || 'Falha ao disparar notificação.'}`, 'erro');
  }
}

// ── Carregamento ──────────────────────────────────────────────────────────────

async function loadDetalhe() {
  const id = new URLSearchParams(window.location.search).get('id');
  if (!id) {
    document.querySelector('.admin-main').innerHTML =
      '<p style="padding:2rem">ID de campanha não informado.</p>';
    return;
  }

  try {
    const res = await fetch(`/api/campanhas/${id}`);
    if (!res.ok) throw new Error('not found');
    const c = await res.json();

    // Título da aba
    document.title = `Aromap - ${c.nome}`;

    // Hero
    const heroImg = document.getElementById('heroImage');
    if (c.imagem_path) {
      heroImg.src = c.imagem_path;
      heroImg.alt = c.nome;
    } else {
      heroImg.closest('.hero-image-wrap').innerHTML = `
        <div class="hero-overlay hero-overlay--noimg">
          <div class="hero-overlay-top">
            <span class="hero-badge badge-${c.status}" id="heroBadge"></span>
            <h1 id="heroTitle"></h1>
            <p class="hero-subtitle" id="heroSubtitle"></p>
          </div>
          <img src="/static/img/logo-aromap.png" alt="Aromap" class="hero-mini-logo" />
        </div>`;
    }

    const badgeLabel = { ativa: 'Ativa', agendada: 'Agendada', encerrada: 'Encerrada' }[c.status] || c.status;
    document.getElementById('heroBadge').textContent  = badgeLabel;
    document.getElementById('heroBadge').className    = `hero-badge badge-${c.status}`;
    document.getElementById('heroTitle').textContent  = c.nome;

    const periodo = `${fmtDate(c.data_inicio)} a ${fmtDate(c.data_fim)}`;
    const horario = c.hora_inicio && c.hora_fim ? ` · ${c.hora_inicio} às ${c.hora_fim}` : '';
    document.getElementById('heroSubtitle').textContent = `${periodo}${horario}`;

    // Informações
    document.getElementById('infoDescricao').textContent  = c.descricao;
    document.getElementById('infoPeriodo').textContent    = periodo;
    document.getElementById('infoHorario').textContent    = c.hora_inicio && c.hora_fim
      ? `${c.hora_inicio} às ${c.hora_fim}` : '—';
    document.getElementById('infoUnidades').textContent   = unidadesLabel(c.unidades);
    document.getElementById('infoBeneficio').textContent  = tipoDescontoLabel(c.tipo_desconto, c.valor_desconto);
    document.getElementById('infoProduto').textContent    = c.produto_alvo;

    // Notificação
    const notifEl = document.getElementById('infoNotificacao');
    if (notifEl) {
      notifEl.textContent = notifLabel(
        c.tipo_notificacao,
        c.notificacao_agendada_em,
      );
    }

    // Botão notificar — disponível para qualquer campanha não encerrada
    const btnNotificar = document.getElementById('btnNotificar');
    if (btnNotificar) {
      if (c.status !== 'encerrada') {
        btnNotificar.style.display = '';
        btnNotificar.addEventListener('click', () => dispararNotificacao(c));
      }
    }

    // Painel de status de notificações
    renderNotifStatus(c.notificacoes);

    // Botão encerrar
    const btnEncerrar = document.getElementById('btnEncerrar');
    if (btnEncerrar) {
      if (c.status === 'encerrada') {
        btnEncerrar.style.display = 'none';
      } else {
        btnEncerrar.addEventListener('click', async () => {
          if (!confirm(`Encerrar a campanha "${c.nome}"?`)) return;
          const token = localStorage.getItem('aromap_token');
          const r = await fetch(`/api/campanhas/${c.id}/encerrar`, {
            method: 'PATCH',
            headers: token ? { Authorization: `Bearer ${token}` } : {},
          });
          if (r.ok) {
            window.location.reload();
          } else {
            alert('Erro ao encerrar campanha.');
          }
        });
      }
    }

  } catch {
    document.querySelector('.admin-main').innerHTML =
      '<p style="padding:2rem">Campanha não encontrada.</p>';
  }
}

loadDetalhe();
