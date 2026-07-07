const generateBtn     = document.getElementById("generateBtn");
const generateCount   = document.getElementById("generateCount");
const generateCountRange = document.getElementById("generateCountRange");
const generateCounter = document.getElementById("generateCounter");
const errorMsg        = document.getElementById("errorMsg");

const styleDropzone   = document.getElementById("styleDropzone");
const styleFileInput  = document.getElementById("styleFileInput");
const stylePreviewGrid = document.getElementById("stylePreviewGrid");
const styleRefCounter = document.getElementById("styleRefCounter");
const styleClearBtn   = document.getElementById("styleClearBtn");

const progressCard    = document.getElementById("progressCard");
const progressBar     = document.getElementById("progressBar");
const progressLabel   = document.getElementById("progressLabel");
const activeProgressPct = document.getElementById("activeProgressPct");
const activeEta       = document.getElementById("activeEta");
const activeJobId     = document.getElementById("activeJobId");
const activeJobStatus = document.getElementById("activeJobStatus");
const resultsGrid     = document.getElementById("resultsGrid");
const stepCurrent     = document.getElementById("stepCurrent");
const stepCurrentLabel = document.getElementById("stepCurrentLabel");
const stepper         = document.getElementById("stepper");
const jobWarning      = document.getElementById("jobWarning");

const doneSection     = document.getElementById("doneSection");
const qualityReport   = document.getElementById("qualityReport");
const dlArchive       = document.getElementById("dlArchive");
const continueBtn     = document.getElementById("continueBtn");
const retryJobBtn     = document.getElementById("retryJobBtn");

let pollingTimer  = null;
let jobStartTime  = null;
let currentJobId  = null;
let currentJobTotal = 0;
let currentJobFiles = [];
let styleRefFiles   = [];
let stylePreviewUrls = [];

const MAX_STYLE_REFS = 10;

function syncCountInputs(from) {
  const value = Math.max(1, Math.min(50, Number(from.value || 1)));
  if (generateCount) generateCount.value = value;
  if (generateCountRange) generateCountRange.value = value;
  if (generateCounter) generateCounter.textContent = I18n.generateCounter(value);
}

generateCount?.addEventListener("input", () => syncCountInputs(generateCount));
generateCountRange?.addEventListener("input", () => syncCountInputs(generateCountRange));
syncCountInputs(generateCount || { value: 1 });

function updateStyleRefCounter() {
  if (styleRefCounter) {
    styleRefCounter.textContent = I18n.styleRefCounter(styleRefFiles.length, MAX_STYLE_REFS);
  }
}

function clearStyleRefs() {
  stylePreviewUrls.forEach(url => URL.revokeObjectURL(url));
  stylePreviewUrls = [];
  styleRefFiles = [];
  if (styleFileInput) styleFileInput.value = "";
  if (stylePreviewGrid) {
    stylePreviewGrid.innerHTML = "";
    stylePreviewGrid.classList.add("hidden");
  }
  if (styleClearBtn) styleClearBtn.classList.add("hidden");
  updateStyleRefCounter();
}

function handleStyleFiles(files) {
  errorMsg.textContent = "";
  const valid = files.filter(f => /\.(jpe?g|png)$/i.test(f.name));
  if (!valid.length) {
    errorMsg.textContent = I18n.t("error.invalidFormat");
    return;
  }
  if (valid.length > MAX_STYLE_REFS) {
    errorMsg.textContent = I18n.t("error.maxStyleRefs");
    return;
  }
  clearStyleRefs();
  styleRefFiles = valid;
  stylePreviewGrid.classList.remove("hidden");
  stylePreviewGrid.innerHTML = valid.map(f => {
    const url = URL.createObjectURL(f);
    stylePreviewUrls.push(url);
    return `<div class="preview-item"><img src="${url}" alt="" /><span class="preview-item-name">${f.name}</span></div>`;
  }).join("");
  styleClearBtn?.classList.remove("hidden");
  updateStyleRefCounter();
}

styleDropzone?.addEventListener("click", e => {
  if (e.target.closest("#styleClearBtn")) return;
  styleFileInput?.click();
});
styleDropzone?.addEventListener("dragover", e => {
  e.preventDefault();
  styleDropzone.classList.add("drag-over");
});
styleDropzone?.addEventListener("dragleave", () => styleDropzone.classList.remove("drag-over"));
styleDropzone?.addEventListener("drop", e => {
  e.preventDefault();
  styleDropzone.classList.remove("drag-over");
  handleStyleFiles([...e.dataTransfer.files]);
});
styleFileInput?.addEventListener("change", () => handleStyleFiles([...styleFileInput.files]));
styleClearBtn?.addEventListener("click", e => {
  e.stopPropagation();
  clearStyleRefs();
});
updateStyleRefCounter();

generateBtn?.addEventListener("click", async () => {
  if (generateBtn.disabled) return;

  errorMsg.textContent = "";
  generateBtn.disabled = true;

  const count = Number(generateCount?.value || 1);
  const formData = new FormData();
  formData.append("count", String(count));
  styleRefFiles.forEach(f => formData.append("style_refs", f));

  try {
    const res = await fetch("/api/generate", {
      method: "POST",
      body: formData,
    });
    const data = await res.json();

    if (!res.ok) {
      showError(data.error || I18n.t("error.generateFailed"));
      generateBtn.disabled = false;
      return;
    }

    showProgress(data.job_id, data.file_count);
  } catch {
    showError(I18n.t("error.network"));
    generateBtn.disabled = false;
  }
});

continueBtn?.addEventListener("click", async () => {
  if (!currentJobId || continueBtn.disabled) return;

  continueBtn.disabled = true;
  activeJobStatus.textContent = I18n.statusLabel("processing");
  activeJobStatus.className = "status-badge status-processing";
  doneSection.classList.add("hidden");
  stepCurrent.classList.remove("hidden");
  jobStartTime = Date.now();
  Jobs.saveActiveJob(currentJobId, currentJobTotal);

  try {
    const res = await fetch(`/api/jobs/${currentJobId}/continue`, { method: "POST" });
    const data = await res.json();
    if (!res.ok) {
      showError(data.error || I18n.t("error.continueFailed"));
      continueBtn.disabled = false;
      showAwaitingContinue(currentJobId, currentJobTotal, await Jobs.fetchStatus(currentJobId));
      return;
    }
    stopPolling();
    pollingTimer = setInterval(() => pollStatus(currentJobId), 2000);
    pollStatus(currentJobId);
  } catch {
    showError(I18n.t("error.network"));
    continueBtn.disabled = false;
  }
});

if (retryJobBtn) {
  retryJobBtn.addEventListener("click", () => {
    stopPolling();
    Jobs.clearActiveJob();
    Jobs.resetProgressUI(progressCard);
    progressCard.classList.add("hidden");
    generateBtn.disabled = false;
    errorMsg.textContent = "";
  });
}

function stopPolling() {
  if (pollingTimer) {
    clearInterval(pollingTimer);
    pollingTimer = null;
  }
}

function jobProgressMetrics(data) {
  return Jobs.jobProgressMetrics(data);
}

function showProgress(jobId, total, initial) {
  currentJobId = jobId;
  currentJobTotal = total;
  currentJobFiles = initial?.files || [];
  const saved = Jobs.getActiveJob();
  jobStartTime = saved?.startedAt || Date.now();
  const shortId = "#" + jobId.slice(0, 4).toUpperCase();

  Jobs.saveActiveJob(jobId, total);
  Jobs.resetProgressUI(progressCard);
  progressCard.classList.remove("hidden");
  if (jobWarning) {
    jobWarning.textContent = "";
    jobWarning.classList.add("hidden");
  }

  if (!initial) {
    progressCard.scrollIntoView({ behavior: "smooth", block: "start" });
  }

  activeJobId.textContent = I18n.jobLabel(shortId);
  activeJobStatus.textContent = I18n.statusLabel("processing");
  activeJobStatus.className = "status-badge status-processing";
  doneSection.classList.add("hidden");
  if (continueBtn) continueBtn.classList.add("hidden");
  if (qualityReport) {
    qualityReport.innerHTML = "";
    qualityReport.classList.add("hidden");
  }
  stepCurrent.classList.remove("hidden");

  const metrics = initial ? jobProgressMetrics(initial) : { progress: 0, total, stepIndex: 0 };
  updateProgressUI(metrics.progress, metrics.total, metrics.stepIndex);
  renderResults(initial?.results || [], metrics.total, currentJobFiles);
  Jobs.updateStepper(stepper, stepCurrentLabel, metrics.progress, metrics.total, metrics.stepIndex);
  Jobs.updateSidebar(jobId, metrics.progress, metrics.total, true, metrics.stepIndex);

  stopPolling();
  pollingTimer = setInterval(() => pollStatus(jobId), 2000);
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

async function pollStatus(jobId) {
  try {
    const data = await Jobs.fetchStatus(jobId);
    const metrics = jobProgressMetrics(data);
    currentJobFiles = data.files || currentJobFiles;

    if (data.status === "error") {
      stopPolling();
      showFailed(data.error || I18n.t("progress.processingFailed"));
      Jobs.notifyChanged();
      return;
    }

    if (data.status === "awaiting_continue") {
      stopPolling();
      showAwaitingContinue(jobId, data.total, data);
      Jobs.notifyChanged();
      return;
    }

    if (data.status === "done") {
      stopPolling();
      renderResults(data.results, metrics.total, data.files);
      showDone(jobId, metrics.total, data);
      Jobs.notifyChanged();
      return;
    }

    updateProgressUI(metrics.progress, metrics.total, metrics.stepIndex);
    renderResults(data.results, metrics.total, data.files);
    Jobs.updateStepper(stepper, stepCurrentLabel, metrics.progress, metrics.total, metrics.stepIndex);
  } catch {
  }
}

function showWarning(message) {
  if (!jobWarning || !message) return;
  jobWarning.textContent = message;
  jobWarning.classList.remove("hidden");
}

function showAwaitingContinue(jobId, total, data) {
  const metrics = jobProgressMetrics({ ...data, phase: "reference" });
  updateProgressUI(metrics.progress, metrics.total, 1, false);
  renderResults(data.results, metrics.total, data.files);
  Jobs.updateStepper(stepper, stepCurrentLabel, metrics.progress, metrics.total, 1);

  activeJobStatus.textContent = I18n.statusLabel("awaiting_continue");
  activeJobStatus.className = "status-badge status-awaiting";
  activeEta.textContent = I18n.t("progress.reviewReady");
  stepCurrent.classList.add("hidden");

  if (data.warning) showWarning(data.warning);

  doneSection.classList.remove("hidden");
  dlArchive.href = `/api/download/${jobId}`;
  if (continueBtn) {
    continueBtn.classList.remove("hidden");
    continueBtn.disabled = false;
  }
  if (qualityReport) {
    qualityReport.innerHTML = Jobs.renderQualityReport(data.results);
    qualityReport.classList.toggle("hidden", !data.results?.length);
  }

  Jobs.updateSidebar(null, 0, 0, false);
}

function showFailed(message) {
  Jobs.clearActiveJob();
  activeJobStatus.textContent = I18n.statusLabel("error");
  activeJobStatus.className = "status-badge status-error";
  Jobs.freezeProgressUI(progressCard, message);
  Jobs.updateSidebar(null, 0, 0, false);
  generateBtn.disabled = false;
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

function showDone(jobId, total, data) {
  Jobs.clearActiveJob();
  const metrics = jobProgressMetrics(data);
  activeJobStatus.textContent = I18n.statusLabel("done");
  activeJobStatus.className = "status-badge status-done";
  activeEta.textContent = I18n.t("progress.complete");
  updateProgressUI(metrics.progress, metrics.total, 3, true);
  Jobs.updateStepper(stepper, stepCurrentLabel, metrics.progress, metrics.total, 3, true);
  stepCurrent.classList.add("hidden");

  if (data.warning) showWarning(data.warning);

  if (qualityReport) {
    qualityReport.innerHTML = Jobs.renderQualityReport(data.results);
    qualityReport.classList.toggle("hidden", !data.results?.length);
  }

  doneSection.classList.remove("hidden");
  dlArchive.href = `/api/download/${jobId}`;
  if (continueBtn) continueBtn.classList.add("hidden");
  generateBtn.disabled = false;
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

    if (data.status === "awaiting_continue") {
      progressCard.classList.remove("hidden");
      activeJobId.textContent = I18n.jobLabel(Jobs.shortId(saved.jobId));
      currentJobId = saved.jobId;
      currentJobTotal = total;
      showAwaitingContinue(saved.jobId, total, data);
      return;
    }

    if (data.status === "done") {
      progressCard.classList.remove("hidden");
      activeJobId.textContent = I18n.jobLabel(Jobs.shortId(saved.jobId));
      currentJobId = saved.jobId;
      renderResults(data.results, total, data.files);
      showDone(saved.jobId, total, data);
      return;
    }

    if (Jobs.isActive(data.status)) {
      showProgress(saved.jobId, total, data);
      pollStatus(saved.jobId);
    } else {
      Jobs.clearActiveJob();
    }
  } catch {
    Jobs.clearActiveJob();
  }
}

document.addEventListener("i18n:changed", () => {
  syncCountInputs(generateCount || { value: 1 });
  updateStyleRefCounter();
});

resumeActiveJob();
window.addEventListener("beforeunload", stopPolling);
