// home.js — carrega dados do usuário logado

(async function () {
  const token = localStorage.getItem("aromap_token");

  if (!token) {
    window.location.href = "/login";
    return;
  }

  // Tenta usar o nome em cache (resposta imediata) e depois confirma com a API
  const cachedName = localStorage.getItem("aromap_name");
  if (cachedName) {
    document.getElementById("userName").textContent = cachedName.split(" ")[0];
  }

  try {
    const res = await fetch("/api/me", {
      headers: {
        "Authorization": `Bearer ${token}`,
        "Content-Type": "application/json",
      },
    });

    if (res.status === 401) {
      localStorage.removeItem("aromap_token");
      localStorage.removeItem("aromap_name");
      window.location.href = "/login";
      return;
    }

    if (res.ok) {
      const data = await res.json();
      // Atualiza o primeiro nome e o cache
      const firstName = data.name.trim().split(" ")[0];
      document.getElementById("userName").textContent = firstName;
      localStorage.setItem("aromap_name", data.name);
    }
  } catch (err) {
    console.error("Erro ao carregar usuário:", err);
  }
})();
