const loginForm = document.getElementById("loginForm");
const message = document.getElementById("message");

loginForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  message.textContent = "";

  const payload = {
    email: document.getElementById("email").value.trim(),
    password: document.getElementById("password").value,
  };

  try {
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

    // Persiste o token e o nome para uso nas outras páginas
    localStorage.setItem("aromap_token", data.token);
    localStorage.setItem("aromap_name",  data.name);

    if (data.is_admin) {
      window.location.href = "/admin";
    } else {
      window.location.href = "/home";
    }
  } catch (error) {
    console.error(error);
    message.textContent = "Erro de conexão com o servidor.";
  }
});