const dropzone       = document.getElementById("dropzone");
const fileInput      = document.getElementById("fileInput");
const fileList       = document.getElementById("fileList");
const previewGrid    = document.getElementById("previewGrid");
const processBtn     = document.getElementById("processBtn");
const browseBtn      = document.getElementById("browseBtn");
const clearBtn       = document.getElementById("clearBtn");
const fileCounter    = document.getElementById("fileCounter");
const errorMsg       = document.getElementById("errorMsg");

const progressCard   = document.getElementById("progressCard");
const progressBar    = document.getElementById("progressBar");
const progressLabel  = document.getElementById("progressLabel");
const activeProgressPct = document.getElementById("activeProgressPct");
const activeEta      = document.getElementById("activeEta");
const activeJobId    = document.getElementById("activeJobId");
const activeJobStatus = document.getElementById("activeJobStatus");
const resultsGrid    = document.getElementById("resultsGrid");
const stepCurrent    = document.getElementById("stepCurrent");
const stepCurrentLabel = document.getElementById("stepCurrentLabel");
const stepper        = document.getElementById("stepper");

const doneSection    = document.getElementById("doneSection");
const qualityReport  = document.getElementById("qualityReport");
const dlArchive      = document.getElementById("dlArchive");
const retryJobBtn    = document.getElementById("retryJobBtn");

let selectedFiles = [];
let pollingTimer  = null;
let jobStartTime  = null;
let previewUrls   = [];
let currentJobId  = null;
let currentJobTotal = 0;
let currentJobFiles = [];

browseBtn.addEventListener("click", e => {
  e.stopPropagation();
  fileInput.click();
});

dropzone.addEventListener("click", e => {
  if (e.target.closest(".btn") || e.target.closest(".file-list") || e.target.closest(".preview-grid")) return;
  fileInput.click();
});

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

clearBtn.addEventListener("click", () => {
  clearFiles();
});

if (retryJobBtn) {
  retryJobBtn.addEventListener("click", () => {
    stopPolling();
    Jobs.clearActiveJob();
    Jobs.resetProgressUI(progressCard);
    progressCard.classList.add("hidden");
    processBtn.disabled = false;
    browseBtn.disabled = false;
    clearBtn.disabled = false;
    errorMsg.textContent = "";
  });
}

function stopPolling() {
  if (pollingTimer) {
    clearInterval(pollingTimer);
    pollingTimer = null;
  }
}

function clearFiles() {
  previewUrls.forEach(url => URL.revokeObjectURL(url));
  previewUrls = [];
  selectedFiles = [];
  fileInput.value = "";
  fileList.innerHTML = "";
  previewGrid.innerHTML = "";
  fileList.classList.add("hidden");
  previewGrid.classList.add("hidden");
  clearBtn.classList.add("hidden");
  processBtn.disabled = true;
  fileCounter.textContent = I18n.fileCounter(0);
  errorMsg.textContent = "";
}

function handleFiles(files) {
  errorMsg.textContent = "";

  const valid = files.filter(f => /\.(jpe?g|png)$/i.test(f.name));

  if (valid.length === 0) {
    errorMsg.textContent = I18n.t("error.invalidFormat");
    return;
  }
  if (valid.length > 10) {
    errorMsg.textContent = I18n.t("error.maxFiles");
    return;
  }

  previewUrls.forEach(url => URL.revokeObjectURL(url));
  previewUrls = [];
  selectedFiles = valid;
  renderFiles();
  processBtn.disabled = false;
  clearBtn.classList.remove("hidden");
}

function renderFiles() {
  fileCounter.textContent = I18n.fileCounter(selectedFiles.length);

  previewGrid.classList.remove("hidden");
  previewGrid.innerHTML = selectedFiles.map((f, i) => {
    const url = URL.createObjectURL(f);
    previewUrls.push(url);
    return `
      <div class="preview-item">
        <img src="${url}" alt="${f.name}" />
        <span class="preview-item-name">${f.name}</span>
      </div>
    `;
  }).join("");

  fileList.classList.remove("hidden");
  fileList.innerHTML = selectedFiles.map(f => `
    <li class="file-item">
      <span class="file-item-name">${f.name}</span>
      <span class="file-item-size">${formatSize(f.size)}</span>
    </li>
  `).join("");
}

function formatSize(bytes) {
  if (bytes < 1024) return bytes + " B";
  if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + " KB";
  return (bytes / 1024 / 1024).toFixed(1) + " MB";
}

processBtn.addEventListener("click", async e => {
  e.stopPropagation();
  if (processBtn.disabled) return;

  errorMsg.textContent = "";
  processBtn.disabled = true;
  browseBtn.disabled = true;
  clearBtn.disabled = true;

  const formData = new FormData();
  selectedFiles.forEach(f => formData.append("images", f));

  try {
    const res = await fetch("/api/upload", { method: "POST", body: formData });
    const data = await res.json();

    if (!res.ok) {
      showError(data.error || I18n.t("error.uploadFailed"));
      processBtn.disabled = false;
      browseBtn.disabled = false;
      clearBtn.disabled = false;
      return;
    }

    showProgress(data.job_id, data.file_count);

  } catch {
    showError(I18n.t("error.network"));
    processBtn.disabled = false;
    browseBtn.disabled = false;
    clearBtn.disabled = false;
  }
});

function showProgress(jobId, total, initial) {
  currentJobId = jobId;
  currentJobTotal = total;
  currentJobFiles = initial?.files?.length
    ? initial.files
    : selectedFiles.map(f => f.name);
  const saved = Jobs.getActiveJob();
  jobStartTime = saved?.startedAt || Date.now();
  const shortId = "#" + jobId.slice(0, 4).toUpperCase();

  Jobs.saveActiveJob(jobId, total);
  Jobs.resetProgressUI(progressCard);
  progressCard.classList.remove("hidden");

  if (!initial) {
    progressCard.scrollIntoView({ behavior: "smooth", block: "start" });
  }

  activeJobId.textContent = I18n.jobLabel(shortId);
  activeJobStatus.textContent = I18n.statusLabel("processing");
  activeJobStatus.className = "status-badge status-processing";
  doneSection.classList.add("hidden");
  if (qualityReport) {
    qualityReport.innerHTML = "";
    qualityReport.classList.add("hidden");
  }
  stepCurrent.classList.remove("hidden");

  const progress = initial?.progress || 0;
  const results = initial?.results || [];

  updateProgressUI(progress, total, initial?.step_index ?? 0);
  renderResults(results, total, currentJobFiles);
  Jobs.updateStepper(stepper, stepCurrentLabel, progress, total, initial?.step_index ?? 0);
  Jobs.updateSidebar(jobId, progress, total, true);

  stopPolling();
  pollingTimer = setInterval(() => pollStatus(jobId, total), 2000);
}

function updateProgressUI(progress, total, stepIndex = 0, isDone = false) {
  const pct = Jobs.progressPct(progress, total, stepIndex, isDone);
  progressBar.style.width = pct + "%";
  if (currentJobId) Jobs.updateSidebar(currentJobId, progress, total, true, stepIndex, isDone);
  progressLabel.textContent = I18n.progressImages(progress, total);
  activeProgressPct.textContent = pct + "%";

  if (progress < total && jobStartTime) {
    const elapsed = (Date.now() - jobStartTime) / 1000;
    const perItem = progress > 0 ? elapsed / progress : elapsed || 1;
    const remaining = Math.max(0, Math.round((total - progress) * perItem));
    const mins = Math.floor(remaining / 60);
    const secs = remaining % 60;
    activeEta.textContent = progress === 0
      ? I18n.t("progress.etaCalculating")
      : I18n.t("progress.eta", { mins, secs });
  } else if (progress >= total) {
    activeEta.textContent = I18n.t("progress.complete");
  }
}

async function pollStatus(jobId, total) {
  try {
    const res  = await fetch(`/api/status/${jobId}`);
    const data = await res.json();

    if (data.status === "error") {
      stopPolling();
      showFailed(data.error || I18n.t("progress.processingFailed"));
      Jobs.notifyChanged();
      return;
    }

    if (data.status === "done") {
      stopPolling();
      renderResults(data.results, total, data.files);
      showDone(jobId, total, data.results);
      Jobs.notifyChanged();
      return;
    }

    updateProgressUI(data.progress, total, data.step_index ?? 0);
    renderResults(data.results, total, data.files);
    Jobs.updateStepper(stepper, stepCurrentLabel, data.progress, total, data.step_index ?? 0);

  } catch {
  }
}

function showFailed(message) {
  Jobs.clearActiveJob();
  activeJobStatus.textContent = I18n.statusLabel("error");
  activeJobStatus.className = "status-badge status-error";
  Jobs.freezeProgressUI(progressCard, message);
  Jobs.updateSidebar(null, 0, 0, false);
  processBtn.disabled = false;
  browseBtn.disabled = false;
  clearBtn.disabled = false;
}

function renderResults(results, total, files) {
  if (!currentJobId || !resultsGrid) return;
  resultsGrid.innerHTML = Jobs.renderResultThumbs(
    results || [],
    total,
    currentJobId,
    files || currentJobFiles
  );
}

function showDone(jobId, total, results) {
  Jobs.clearActiveJob();
  activeJobStatus.textContent = I18n.statusLabel("done");
  activeJobStatus.className = "status-badge status-done";
  activeEta.textContent = I18n.t("progress.complete");
  updateProgressUI(total, total, 4, true);
  Jobs.updateStepper(stepper, stepCurrentLabel, total, total, 4, true);
  stepCurrent.classList.add("hidden");
  if (qualityReport) {
    qualityReport.innerHTML = Jobs.renderQualityReport(results);
    qualityReport.classList.toggle("hidden", !results?.length);
  }
  doneSection.classList.remove("hidden");
  dlArchive.href = `/api/download/${jobId}`;
  Jobs.updateSidebar(null, 0, 0, false);
}

function showError(msg) {
  errorMsg.textContent = msg;
}

async function resumeActiveJob() {
  const saved = Jobs.getActiveJob();
  if (!saved?.jobId || !progressCard) return;

  try {
    const data = await Jobs.fetchStatus(saved.jobId);
    const total = data.total || saved.total;

    if (data.status === "error") {
      Jobs.clearActiveJob();
      progressCard.classList.remove("hidden");
      activeJobId.textContent = I18n.jobLabel(Jobs.shortId(saved.jobId));
      showFailed(data.error || I18n.t("progress.processingFailed"));
      Jobs.notifyChanged();
      return;
    }

    if (data.status === "done") {
      progressCard.classList.remove("hidden");
      activeJobId.textContent = I18n.jobLabel(Jobs.shortId(saved.jobId));
      updateProgressUI(data.progress, total, 4, true);
      renderResults(data.results, total, data.files);
      showDone(saved.jobId, total, data.results);
      return;
    }

    if (Jobs.isActive(data.status)) {
      showProgress(saved.jobId, total, data);
      pollStatus(saved.jobId, total);
    } else {
      Jobs.clearActiveJob();
    }
  } catch {
    Jobs.clearActiveJob();
  }
}

document.addEventListener("i18n:changed", () => {
  if (selectedFiles.length) renderFiles();
  else if (fileCounter) fileCounter.textContent = I18n.fileCounter(0);
});

resumeActiveJob();

if (new URLSearchParams(window.location.search).get("pick") === "1") {
  history.replaceState(null, "", window.location.pathname);
  requestAnimationFrame(() => fileInput.click());
}

window.addEventListener("beforeunload", stopPolling);
