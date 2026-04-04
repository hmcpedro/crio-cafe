const loginForm = document.getElementById("loginForm");
const message = document.getElementById("message");

loginForm.addEventListener("submit", async (event) => {
  event.preventDefault();

  message.textContent = "";

  const payload = {
    email: document.getElementById("email").value.trim(),
    password: document.getElementById("password").value,
  };

  const response = await fetch("/auth/login", {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify(payload),
  });

  const data = await response.json();

  if (!response.ok) {
    message.textContent = data.detail || "Erro ao fazer login.";
    return;
  }

  if (data.is_admin) {
    message.textContent = "Login realizado como administrador.";
  } else {
    message.textContent = "Login realizado com sucesso.";
  }
});