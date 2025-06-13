document.addEventListener("DOMContentLoaded", () => {
  const form = document.getElementById("settings-form");
  const toastContainer = document.getElementById("toast");

  function showToast(message, isError = false) {
    const toast = document.createElement("div");
    toast.textContent = message;
    toast.className = isError ? "toast error" : "toast success";
    toastContainer.appendChild(toast);
    setTimeout(() => {
      toast.remove();
    }, 3000);
  }

  if (!form) return;

  form.addEventListener("submit", async (e) => {
    e.preventDefault();
    const model = document.getElementById("default-model").value;
    const language = document.getElementById("default-language").value;

    try {
      const resp = await fetch("/api/settings", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ default_model: model, default_language: language }),
      });
      const data = await resp.json();
      if (resp.ok) {
        showToast("Settings saved", false);
      } else {
        showToast(data.error || "Error saving settings", true);
      }
    } catch (err) {
      showToast("Network error", true);
    }
  });
});
