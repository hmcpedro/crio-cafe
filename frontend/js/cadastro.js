const registerForm = document.getElementById("registerForm");
const message = document.getElementById("message");

registerForm.addEventListener("submit", async (event) => {
  event.preventDefault();

  message.textContent = "";

  const payload = {
    name: document.getElementById("name").value.trim(),
    email: document.getElementById("email").value.trim(),
    phone: document.getElementById("phone").value.trim(),
    password: document.getElementById("password").value,
    confirm_password: document.getElementById("confirmPassword").value,
  };

  try {
    const response = await fetch("/auth/register", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify(payload),
    });

    const data = await response.json();

    if (!response.ok) {
      message.textContent = data.detail || "Erro ao cadastrar.";
      return;
    }

    message.textContent = "Cadastro realizado com sucesso. Redirecionando para o login...";

    setTimeout(() => {
      window.location.href = "/login";
    }, 1500);
  } catch (error) {
    message.textContent = "Erro de conexão com o servidor.";
    console.error(error);
  }
});