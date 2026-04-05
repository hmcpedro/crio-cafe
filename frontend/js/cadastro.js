const registerForm = document.getElementById("registerForm");
const message = document.getElementById("message");

registerForm.addEventListener("submit", async (event) => {
  event.preventDefault();

  message.textContent = "";

  const name = document.getElementById("name").value.trim();
  const email = document.getElementById("email").value.trim();
  const phone = document.getElementById("phone").value.trim();
  const password = document.getElementById("password").value;
  const confirmPassword = document.getElementById("confirmPassword").value;

  // Validações client-side
  if (!name || !email || !phone || !password || !confirmPassword) {
    message.textContent = "Preencha todos os campos.";
    return;
  }

  if (password !== confirmPassword) {
    message.textContent = "As senhas não coincidem.";
    return;
  }

  if (password.length < 6) {
    message.textContent = "A senha deve ter pelo menos 6 caracteres.";
    return;
  }

  const payload = { name, email, phone, password, confirm_password: confirmPassword };

  try {
    const response = await fetch("/auth/register", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });

    const data = await response.json();

    if (!response.ok) {
      message.textContent = data.detail || "Erro ao cadastrar.";
      return;
    }

    message.textContent = "Cadastro realizado com sucesso. Redirecionando...";

    setTimeout(() => {
      window.location.href = "/login";
    }, 1500);

  } catch (error) {
    message.textContent = "Erro de conexão com o servidor.";
    console.error(error);
  }
});