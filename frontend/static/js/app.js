/* app.js — Image Transform MVP frontend */

const dropzone    = document.getElementById("dropzone");
const fileInput   = document.getElementById("fileInput");
const fileList    = document.getElementById("fileList");
const processBtn  = document.getElementById("processBtn");
const errorMsg    = document.getElementById("errorMsg");

const uploadSection   = document.getElementById("uploadSection");
const progressSection = document.getElementById("progressSection");
const doneSection     = document.getElementById("doneSection");

const progressBar   = document.getElementById("progressBar");
const progressLabel = document.getElementById("progressLabel");
const resultsGrid   = document.getElementById("resultsGrid");

const dlVector = document.getElementById("dlVector");
const dl3d     = document.getElementById("dl3d");
const resetBtn = document.getElementById("resetBtn");

let selectedFiles = [];
let pollingTimer  = null;

// ── File selection ─────────────────────────────────────────────────────────

dropzone.addEventListener("click", () => fileInput.click());

dropzone.addEventListener("dragover", e => {
  e.preventDefault();
  dropzone.classList.add("drag-over");
});

dropzone.addEventListener("dragleave", () => dropzone.classList.remove("drag-over"));

dropzone.addEventListener("drop", e => {
  e.preventDefault();
  dropzone.classList.remove("drag-over");
  handleFiles([...e.dataTransfer.files]);
});

fileInput.addEventListener("change", () => handleFiles([...fileInput.files]));

function handleFiles(files) {
  errorMsg.textContent = "";

  const valid = files.filter(f => /\.(jpe?g|png)$/i.test(f.name));

  if (valid.length === 0) {
    errorMsg.textContent = "Please upload JPG or PNG files.";
    return;
  }
  if (valid.length > 10) {
    errorMsg.textContent = "Maximum 10 files per upload.";
    return;
  }

  selectedFiles = valid;
  renderFileList();
  processBtn.disabled = false;
}

function renderFileList() {
  fileList.innerHTML = selectedFiles.map(f => `
    <li class="file-item">
      <span class="file-item-name">📄 ${f.name}</span>
      <span class="file-item-size">${formatSize(f.size)}</span>
    </li>
  `).join("");
}

function formatSize(bytes) {
  if (bytes < 1024) return bytes + " B";
  if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + " KB";
  return (bytes / 1024 / 1024).toFixed(1) + " MB";
}

// ── Upload & start pipeline ────────────────────────────────────────────────

processBtn.addEventListener("click", async () => {
  errorMsg.textContent = "";
  processBtn.disabled = true;

  const formData = new FormData();
  selectedFiles.forEach(f => formData.append("images", f));

  try {
    const res = await fetch("/api/upload", { method: "POST", body: formData });
    const data = await res.json();

    if (!res.ok) {
      showError(data.error || "Upload failed.");
      processBtn.disabled = false;
      return;
    }

    showProgress(data.job_id, data.file_count);

  } catch (err) {
    showError("Network error. Please try again.");
    processBtn.disabled = false;
  }
});

// ── Progress polling ───────────────────────────────────────────────────────

function showProgress(jobId, total) {
  uploadSection.classList.add("hidden");
  progressSection.classList.remove("hidden");
  progressLabel.textContent = `0 / ${total} images done`;
  progressBar.style.width = "0%";
  resultsGrid.innerHTML = "";

  pollingTimer = setInterval(() => pollStatus(jobId, total), 2000);
}

async function pollStatus(jobId, total) {
  try {
    const res  = await fetch(`/api/status/${jobId}`);
    const data = await res.json();

    // Update progress bar
    const pct = total > 0 ? Math.round((data.progress / total) * 100) : 0;
    progressBar.style.width = pct + "%";
    progressLabel.textContent = `${data.progress} / ${total} images done`;

    // Render new result cards
    renderResults(data.results);

    if (data.status === "done") {
      clearInterval(pollingTimer);
      showDone(jobId);
    }

    if (data.status === "error") {
      clearInterval(pollingTimer);
      showError(data.error || "Processing failed.");
      progressSection.classList.add("hidden");
      uploadSection.classList.remove("hidden");
      processBtn.disabled = false;
    }

  } catch {
    // Network hiccup — keep polling
  }
}

function renderResults(results) {
  resultsGrid.innerHTML = results.map(r => {
    const vScore = r.hive_vector;
    const dScore = r.hive_3d;
    return `
      <div class="result-card">
        <span class="result-name">✓ ${r.filename}</span>
        <div class="result-scores">
          <span class="score-chip ${scoreClass(vScore)}" title="Vector — Hivedetect AI score">
            ⬡ ${formatScore(vScore)}
          </span>
          <span class="score-chip ${scoreClass(dScore)}" title="3D — Hivedetect AI score">
            ◈ ${formatScore(dScore)}
          </span>
        </div>
      </div>
    `;
  }).join("");
}

function scoreClass(score) {
  if (score < 0)   return "score-warn";   // check failed
  if (score <= 10) return "score-good";   // target
  if (score <= 30) return "score-warn";
  return "score-bad";
}

function formatScore(score) {
  if (score < 0) return "N/A";
  return score.toFixed(1) + "% AI";
}

// ── Done state ─────────────────────────────────────────────────────────────

function showDone(jobId) {
  progressSection.classList.add("hidden");
  doneSection.classList.remove("hidden");
  dlVector.href = `/api/download/${jobId}/vector`;
  dl3d.href     = `/api/download/${jobId}/3d`;
}

// ── Reset ──────────────────────────────────────────────────────────────────

resetBtn.addEventListener("click", () => {
  selectedFiles = [];
  fileList.innerHTML = "";
  fileInput.value = "";
  errorMsg.textContent = "";
  processBtn.disabled = true;

  doneSection.classList.add("hidden");
  progressSection.classList.add("hidden");
  uploadSection.classList.remove("hidden");
});

// ── Helpers ────────────────────────────────────────────────────────────────

function showError(msg) {
  errorMsg.textContent = msg;
}
