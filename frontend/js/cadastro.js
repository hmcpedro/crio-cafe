const registerForm = document.getElementById('registerForm');
const message      = document.getElementById('message');

registerForm.addEventListener('submit', async (event) => {
  event.preventDefault();

  message.textContent = '';

  const name            = document.getElementById('name').value.trim();
  const email           = document.getElementById('email').value.trim();
  const phone           = document.getElementById('phone').value.trim();
  const password        = document.getElementById('password').value;
  const confirmPassword = document.getElementById('confirmPassword').value;
  const permitirLoc     = document.getElementById('permitirLocalizacao').checked;

  if (!name || !email || !phone || !password || !confirmPassword) {
    message.textContent = 'Preencha todos os campos.';
    return;
  }

  if (password !== confirmPassword) {
    message.textContent = 'As senhas não coincidem.';
    return;
  }

  if (password.length < 6) {
    message.textContent = 'A senha deve ter pelo menos 6 caracteres.';
    return;
  }

  try {
    const res = await fetch('/auth/register', {
      method:  'POST',
      headers: { 'Content-Type': 'application/json' },
      body:    JSON.stringify({ name, email, phone, password, confirm_password: confirmPassword }),
    });

    const data = await res.json();

    if (!res.ok) {
      message.textContent = data.detail || 'Erro ao cadastrar.';
      return;
    }

    // Auto-login: salva token e nome
    localStorage.setItem('aromap_token', data.token);
    localStorage.setItem('aromap_name',  data.name);

    // Se o usuário concedeu permissão de localização, salva a flag no banco.
    // As coordenadas serão capturadas pelo home.js após o redirecionamento.
    if (permitirLoc) {
      try {
        await fetch('/api/me/permissao-localizacao?permitir=true', {
          method:  'PATCH',
          headers: { 'Authorization': `Bearer ${data.token}` },
        });
      } catch { /* silencioso — home.js tentará novamente */ }
    }

    message.textContent = 'Cadastro realizado! Entrando...';
    setTimeout(() => { window.location.href = '/home'; }, 1000);

  } catch (err) {
    message.textContent = 'Erro de conexão com o servidor.';
    console.error(err);
  }
});
