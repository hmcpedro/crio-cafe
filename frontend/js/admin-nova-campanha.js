// ── Tipo de desconto: placeholder + visibilidade do campo valor ────────────
const discountType  = document.getElementById('discountType');
const discountValue = document.getElementById('discountValue');
const discountLabel = discountValue?.previousElementSibling; // <label>

const DESCONTO_CONFIG = {
  percentual: { placeholder: 'Ex: 20  (para 20%)',   label: 'Valor (%)' },
  fixo:       { placeholder: 'Ex: 5,50  (em R$)',    label: 'Valor (R$)' },
  combo:      { placeholder: '',                      label: 'Valor (opcional)' },
};

function updateDiscountField() {
  const cfg = DESCONTO_CONFIG[discountType.value] || DESCONTO_CONFIG.percentual;
  discountValue.placeholder = cfg.placeholder;
  if (discountLabel) discountLabel.textContent = cfg.label;
  // Combo não exige valor — deixa visível mas limpa e deixa facultativo
  if (discountType.value === 'combo') {
    discountValue.value = '';
    discountValue.style.opacity = '0.5';
    discountValue.required = false;
  } else {
    discountValue.style.opacity = '1';
    discountValue.required = true;
  }
}

if (discountType) {
  discountType.addEventListener('change', updateDiscountField);
  updateDiscountField(); // aplica ao carregar
}

// ── Image upload preview ───────────────────────────────────────────────────
const uploadArea  = document.getElementById('uploadArea');
const imageInput  = document.getElementById('imageInput');
const previewWrap = document.getElementById('uploadPreview');
const previewImg  = document.getElementById('previewImg');
const removeBtn   = document.getElementById('removeImage');

uploadArea.addEventListener('click', () => imageInput.click());

uploadArea.addEventListener('dragover', e => {
  e.preventDefault();
  uploadArea.classList.add('upload-area--drag');
});

uploadArea.addEventListener('dragleave', () => uploadArea.classList.remove('upload-area--drag'));

uploadArea.addEventListener('drop', e => {
  e.preventDefault();
  uploadArea.classList.remove('upload-area--drag');
  const file = e.dataTransfer.files[0];
  if (file) showPreview(file);
});

imageInput.addEventListener('change', () => {
  if (imageInput.files[0]) showPreview(imageInput.files[0]);
});

removeBtn.addEventListener('click', () => {
  imageInput.value = '';
  previewWrap.style.display = 'none';
  uploadArea.style.display = '';
});

function showPreview(file) {
  const reader = new FileReader();
  reader.onload = e => {
    previewImg.src = e.target.result;
    previewWrap.style.display = 'flex';
    uploadArea.style.display = 'none';
  };
  reader.readAsDataURL(file);
}

// ── Weekday toggle styling ─────────────────────────────────────────────────
document.querySelectorAll('.day-toggle input').forEach(cb => {
  cb.addEventListener('change', () => {
    cb.closest('.day-toggle').classList.toggle('day-toggle--active', cb.checked);
  });
});

// ── Notificação: mostrar/esconder campos de agendamento ────────────────────
const notifRadios     = document.querySelectorAll('input[name="notif"]');
const scheduleGroup   = document.getElementById('notifScheduleGroup');

notifRadios.forEach(radio => {
  radio.addEventListener('change', () => {
    scheduleGroup.style.display = radio.value === 'agendado' && radio.checked ? '' : 'none';
    // Re-verifica todos para garantir
    const checked = document.querySelector('input[name="notif"]:checked');
    scheduleGroup.style.display = checked && checked.value === 'agendado' ? '' : 'none';
  });
});

// ── Form submit → POST /api/campanhas ──────────────────────────────────────
document.getElementById('campaignForm').addEventListener('submit', async e => {
  e.preventDefault();

  const msg    = document.getElementById('formMessage');
  const btn    = e.target.querySelector('.btn-submit');
  btn.disabled = true;
  msg.textContent = '';
  msg.className   = 'form-message';

  // Dias da semana: string de 7 chars (Seg→Dom)
  const dayOrder = ['seg', 'ter', 'qua', 'qui', 'sex', 'sab', 'dom'];
  const diasStr  = dayOrder.map(v => {
    const cb = document.querySelector(`.day-toggle input[value="${v}"]`);
    return cb && cb.checked ? '1' : '0';
  }).join('');

  // Unidades selecionadas
  const unidades = Array.from(document.querySelectorAll('.units-check input:checked'))
    .map(el => el.value);

  // Notificação agendada
  const notifVal  = document.querySelector('input[name="notif"]:checked')?.value || 'manual';
  const notifDate = document.getElementById('notifDate')?.value || '';
  const notifTime = document.getElementById('notifTime')?.value || '';
  let notifAgendadaEm = '';
  if (notifVal === 'agendado' && notifDate && notifTime) {
    notifAgendadaEm = `${notifDate}T${notifTime}:00`;
  }

  const tipoDescontoEl = document.getElementById('discountType');
  const tipoDescontoVal = tipoDescontoEl ? tipoDescontoEl.value.trim() : '';

  const fd = new FormData();
  fd.append('nome',            document.getElementById('campName').value.trim());
  fd.append('descricao',       document.getElementById('campDesc').value.trim());
  fd.append('produto_alvo',    document.getElementById('campProduct').value.trim());
  fd.append('tipo_desconto',   tipoDescontoVal);
  fd.append('valor_desconto',  document.getElementById('discountValue').value.trim());
  fd.append('data_inicio',     document.getElementById('startDate').value);
  fd.append('data_fim',        document.getElementById('endDate').value);
  fd.append('hora_inicio',     document.getElementById('startTime').value);
  fd.append('hora_fim',        document.getElementById('endTime').value);
  fd.append('dias_semana',     diasStr);
  fd.append('unidades',        JSON.stringify(unidades));
  fd.append('tipo_notificacao', notifVal === 'imediato' ? 'imediata' : notifVal);
  if (notifAgendadaEm) fd.append('notificacao_agendada_em', notifAgendadaEm);

  if (imageInput.files[0]) {
    fd.append('imagem', imageInput.files[0]);
  }

  const token = localStorage.getItem('aromap_token');

  try {
    const res = await fetch('/api/campanhas', {
      method: 'POST',
      headers: token ? { Authorization: `Bearer ${token}` } : {},
      body: fd,
    });

    const data = await res.json();

    if (!res.ok) {
      const detail = Array.isArray(data.detail)
        ? data.detail.map(e => e.msg || JSON.stringify(e)).join('; ')
        : (data.detail || 'Erro ao criar campanha.');
      msg.textContent = detail;
      msg.className   = 'form-message msg-error';
      btn.disabled    = false;
      return;
    }

    msg.textContent = 'Campanha criada com sucesso! Redirecionando...';
    msg.className   = 'form-message msg-success';
    setTimeout(() => { window.location.href = '/admin/campanhas'; }, 1200);

  } catch {
    msg.textContent = 'Erro de conexão. Verifique o servidor.';
    msg.className   = 'form-message msg-error';
    btn.disabled    = false;
  }
});
