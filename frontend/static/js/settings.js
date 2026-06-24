const PROMPT_FIELDS = [
  "KONTEXT_3D_PROMPT",
  "LEGACY_UNIQUE_PROMPT",
  "LEGACY_PIXAR_PROMPT",
  "NEGATIVE_PROMPT",
];

const fieldMap = {
  KONTEXT_3D_PROMPT: "promptKontext3d",
  LEGACY_UNIQUE_PROMPT: "promptLegacyUnique",
  LEGACY_PIXAR_PROMPT: "promptLegacyPixar",
  NEGATIVE_PROMPT: "promptNegative",
};

const form = document.getElementById("settingsForm");
const statusEl = document.getElementById("settingsStatus");
const resetBtn = document.getElementById("settingsResetBtn");

async function loadSettings() {
  const res = await fetch("/api/settings");
  if (!res.ok) throw new Error("settings_load_failed");
  const data = await res.json();
  const prompts = data.prompts || {};
  PROMPT_FIELDS.forEach(key => {
    const el = document.getElementById(fieldMap[key]);
    if (el) el.value = prompts[key] || "";
  });
}

function collectPrompts() {
  const prompts = {};
  PROMPT_FIELDS.forEach(key => {
    const el = document.getElementById(fieldMap[key]);
    if (el) prompts[key] = el.value;
  });
  return prompts;
}

function showStatus(key, isError = false) {
  if (!statusEl) return;
  statusEl.textContent = I18n.t(key);
  statusEl.classList.remove("hidden", "settings-status-error", "settings-status-ok");
  statusEl.classList.add(isError ? "settings-status-error" : "settings-status-ok");
  setTimeout(() => statusEl.classList.add("hidden"), 3000);
}

form?.addEventListener("submit", async e => {
  e.preventDefault();
  try {
    const res = await fetch("/api/settings", {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ prompts: collectPrompts() }),
    });
    if (!res.ok) throw new Error("save_failed");
    showStatus("settings.saved");
  } catch {
    showStatus("settings.saveError", true);
  }
});

resetBtn?.addEventListener("click", async () => {
  if (!confirm(I18n.t("settings.resetConfirm"))) return;
  PROMPT_FIELDS.forEach(key => {
    const el = document.getElementById(fieldMap[key]);
    if (el) el.value = "";
  });
  try {
    const res = await fetch("/api/settings", {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ prompts: collectPrompts() }),
    });
    if (!res.ok) throw new Error("reset_failed");
    await loadSettings();
    showStatus("settings.resetDone");
  } catch {
    showStatus("settings.saveError", true);
  }
});

loadSettings().catch(() => showStatus("settings.loadError", true));
