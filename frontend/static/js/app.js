const dropzone          = document.getElementById("dropzone");
const fileInput         = document.getElementById("fileInput");
const fileList          = document.getElementById("fileList");
const previewGrid       = document.getElementById("previewGrid");
const processBtn        = document.getElementById("processBtn");
const browseBtn         = document.getElementById("browseBtn");
const clearBtn          = document.getElementById("clearBtn");
const fileCounter       = document.getElementById("fileCounter");
const errorMsg          = document.getElementById("errorMsg");

const progressBar       = document.getElementById("progressBar");
const progressLabel     = document.getElementById("progressLabel");
const activeProgressPct = document.getElementById("activeProgressPct");
const activeEta         = document.getElementById("activeEta");
const activeJobId       = document.getElementById("activeJobId");
const activeJobStatus   = document.getElementById("activeJobStatus");
const activeJobHeader   = document.getElementById("activeJobHeader");
const activeJobBody     = document.getElementById("activeJobBody");
const activeJobEmpty    = document.getElementById("activeJobEmpty");
const resultsGrid       = document.getElementById("resultsGrid");
const stepCurrent       = document.getElementById("stepCurrent");
const stepCurrentLabel  = document.getElementById("stepCurrentLabel");
const stepper           = document.getElementById("stepper");
const doneSection       = document.getElementById("doneSection");
const qualityReport     = document.getElementById("qualityReport");
const dlArchive         = document.getElementById("dlArchive");

const recentJobsList    = document.getElementById("recentJobsList");
const recentLoading     = document.getElementById("recentLoading");
const recentEmpty       = document.getElementById("recentEmpty");

const statImages        = document.getElementById("statImages");
const statSuccess       = document.getElementById("statSuccess");
const statFailed        = document.getElementById("statFailed");
const statHive          = document.getElementById("statHive");
const activeJobCard     = document.getElementById("activeJobCard");

let pollingTimer = null;
let jobStartTime = null;
let selectedFiles = [];
let previewUrls = [];

function setUploadEnabled(enabled) {
  if (browseBtn) browseBtn.disabled = !enabled;
  if (clearBtn) clearBtn.disabled = !enabled;
  if (processBtn) processBtn.disabled = !enabled || selectedFiles.length === 0;
}

function clearFiles() {
  previewUrls.forEach(url => URL.revokeObjectURL(url));
  previewUrls = [];
  selectedFiles = [];
  if (fileInput) fileInput.value = "";
  if (fileList) {
    fileList.innerHTML = "";
    fileList.classList.add("hidden");
  }
  if (previewGrid) {
    previewGrid.innerHTML = "";
    previewGrid.classList.add("hidden");
  }
  clearBtn?.classList.add("hidden");
  if (fileCounter) fileCounter.textContent = I18n.fileCounter(0);
  if (errorMsg) errorMsg.textContent = "";
  setUploadEnabled(true);
}

function formatSize(bytes) {
  if (bytes < 1024) return bytes + " B";
  if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + " KB";
  return (bytes / 1024 / 1024).toFixed(1) + " MB";
}

function handleFiles(files) {
  if (!fileInput) return;
  if (errorMsg) errorMsg.textContent = "";

  const valid = files.filter(f => /\.(jpe?g|png)$/i.test(f.name));

  if (valid.length === 0) {
    if (errorMsg) errorMsg.textContent = I18n.t("error.invalidFormat");
    return;
  }
  if (valid.length > 10) {
    if (errorMsg) errorMsg.textContent = I18n.t("error.maxFiles");
    return;
  }

  previewUrls.forEach(url => URL.revokeObjectURL(url));
  previewUrls = [];
  selectedFiles = valid;
  renderSelectedFiles();
  clearBtn?.classList.remove("hidden");
  setUploadEnabled(true);
}

function renderSelectedFiles() {
  if (fileCounter) fileCounter.textContent = I18n.fileCounter(selectedFiles.length);

  if (previewGrid) {
    previewGrid.classList.remove("hidden");
    previewGrid.innerHTML = selectedFiles.map(f => {
      const url = URL.createObjectURL(f);
      previewUrls.push(url);
      return `
        <div class="preview-item">
          <img src="${url}" alt="${f.name}" />
          <span class="preview-item-name">${f.name}</span>
        </div>
      `;
    }).join("");
  }

  if (fileList) {
    fileList.classList.remove("hidden");
    fileList.innerHTML = selectedFiles.map(f => `
      <li class="file-item">
        <span class="file-item-name">${f.name}</span>
        <span class="file-item-size">${formatSize(f.size)}</span>
      </li>
    `).join("");
  }
}

function initUploadZone() {
  if (!dropzone || !fileInput || !browseBtn) return;

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

  clearBtn?.addEventListener("click", clearFiles);

  processBtn?.addEventListener("click", async e => {
    e.stopPropagation();
    if (processBtn.disabled || selectedFiles.length === 0) return;

    if (errorMsg) errorMsg.textContent = "";
    setUploadEnabled(false);

    const formData = new FormData();
    selectedFiles.forEach(f => formData.append("images", f));

    try {
      const res = await fetch("/api/upload", { method: "POST", body: formData });
      const data = await res.json();

      if (!res.ok) {
        if (errorMsg) errorMsg.textContent = data.error || I18n.t("error.uploadFailed");
        setUploadEnabled(true);
        return;
      }

      const fileNames = selectedFiles.map(f => f.name);
      clearFiles();
      startJobFromUpload(data.job_id, data.file_count, fileNames);
    } catch {
      if (errorMsg) errorMsg.textContent = I18n.t("error.network");
      setUploadEnabled(true);
    }
  });
}

function startJobFromUpload(jobId, total, fileNames) {
  Jobs.saveActiveJob(jobId, total);
  jobStartTime = Date.now();
  setUploadEnabled(false);

  activeJobCard?.scrollIntoView({ behavior: "smooth", block: "start" });

  showActivePanel({
    job_id: jobId,
    progress: 0,
    total,
    results: [],
    files: fileNames,
    status: "processing",
  });

  startPolling(jobId, total);
  pollOnce(jobId, total);
  Jobs.notifyChanged();
}

initUploadZone();

document.addEventListener("jobs:changed", () => {
  loadStats();
  loadRecentJobs();
  if (!activeJobCard?.classList.contains("job-state-error")) {
    loadActiveJob();
  }
});

loadStats();
loadRecentJobs();
loadActiveJob();

async function loadStats() {
  try {
    const data = await Jobs.fetchStats();
    if (statImages) statImages.textContent = data.images_processed ?? 0;
    if (statSuccess) statSuccess.textContent = data.successful_jobs ?? 0;
    if (statFailed) statFailed.textContent = data.failed_jobs ?? 0;
    if (statHive) {
      statHive.textContent = data.avg_hive_score != null ? `${data.avg_hive_score}%` : "—";
    }
  } catch {
    if (statImages) statImages.textContent = "—";
    if (statSuccess) statSuccess.textContent = "—";
    if (statFailed) statFailed.textContent = "—";
    if (statHive) statHive.textContent = "—";
  }
}

async function loadRecentJobs() {
  if (!recentJobsList) return;

  recentLoading?.classList.remove("hidden");
  recentEmpty?.classList.add("hidden");
  recentJobsList.innerHTML = "";

  try {
    const jobs = await Jobs.fetchJobs();
    const recent = jobs.slice(0, 5);
    if (recent.length === 0) {
      recentEmpty?.classList.remove("hidden");
    } else {
      recentJobsList.innerHTML = recent.map((job, i) => Jobs.renderRecentItem(job, i)).join("");
    }
  } catch {
    recentEmpty?.classList.remove("hidden");
  } finally {
    recentLoading?.classList.add("hidden");
  }
}

async function loadActiveJob() {
  if (!activeJobBody || !activeJobEmpty) return;
  if (activeJobCard?.classList.contains("job-state-error")) return;

  try {
    const jobs = await Jobs.fetchJobs();
    let active = jobs.find(j => Jobs.isActive(j.status));

    if (!active) {
      const saved = Jobs.getActiveJob();
      if (saved?.jobId) {
        const data = await Jobs.fetchStatus(saved.jobId);
        if (data.status === "done") {
          showJobDone(saved.jobId, data, data.total || saved.total);
          Jobs.clearActiveJob();
          return;
        }
        if (Jobs.isActive(data.status)) {
          active = { job_id: saved.jobId, total: data.total || saved.total, ...data };
        }
      }
    }

    if (!active) {
      stopPolling();
      showActiveEmpty();
      setUploadEnabled(true);
      Jobs.updateSidebar(null, 0, 0, false);
      return;
    }

    setUploadEnabled(false);
    showActivePanel(active);
    Jobs.saveActiveJob(active.job_id, active.total);
    jobStartTime = Date.now();
    startPolling(active.job_id, active.total);
    await pollOnce(active.job_id, active.total);
  } catch {
    stopPolling();
    showActiveEmpty();
    setUploadEnabled(true);
    Jobs.updateSidebar(null, 0, 0, false);
  }
}

function showActiveEmpty() {
  activeJobEmpty?.classList.remove("hidden");
  activeJobBody?.classList.add("hidden");
  activeJobHeader?.classList.add("hidden");
}

function showActivePanel(job) {
  Jobs.resetProgressUI(activeJobCard);
  activeJobEmpty?.classList.add("hidden");
  activeJobBody?.classList.remove("hidden");
  activeJobHeader?.classList.remove("hidden");
  doneSection?.classList.add("hidden");
  if (qualityReport) {
    qualityReport.innerHTML = "";
    qualityReport.classList.add("hidden");
  }
  stepCurrent?.classList.remove("hidden");

  if (activeJobId) activeJobId.textContent = I18n.jobLabel(Jobs.shortId(job.job_id));
  if (activeJobStatus) {
    activeJobStatus.textContent = I18n.statusLabel(job.status || "processing");
    activeJobStatus.className = "status-badge status-processing";
  }

  updateProgressUI(job.progress || 0, job.total || 0, job.step_index ?? 0);
  Jobs.updateSidebar(job.job_id, job.progress || 0, job.total || 0, true, job.step_index ?? 0);
  Jobs.updateStepper(stepper, stepCurrentLabel, job.progress || 0, job.total || 0, job.step_index ?? 0);

  if (resultsGrid) {
    resultsGrid.innerHTML = Jobs.renderResultThumbs(
      job.results,
      job.total,
      job.job_id,
      job.files
    );
  }
}

function startPolling(jobId, total) {
  stopPolling();
  pollingTimer = setInterval(() => pollOnce(jobId, total), 2000);
}

function stopPolling() {
  if (pollingTimer) {
    clearInterval(pollingTimer);
    pollingTimer = null;
  }
}

function showJobDone(jobId, data, total) {
  stopPolling();
  setUploadEnabled(true);
  activeJobEmpty?.classList.add("hidden");
  activeJobBody?.classList.remove("hidden");
  activeJobHeader?.classList.remove("hidden");

  updateProgressUI(total, total, 3, true);
  Jobs.updateStepper(stepper, stepCurrentLabel, total, total, 3, true);

  if (resultsGrid) {
    resultsGrid.innerHTML = Jobs.renderResultThumbs(
      data.results,
      total,
      jobId,
      data.files
    );
  }
  if (activeJobId) activeJobId.textContent = I18n.jobLabel(Jobs.shortId(jobId));
  if (activeJobStatus) {
    activeJobStatus.textContent = I18n.statusLabel("done");
    activeJobStatus.className = "status-badge status-done";
  }
  if (activeEta) activeEta.textContent = I18n.t("progress.complete");
  stepCurrent?.classList.add("hidden");
  if (qualityReport) {
    qualityReport.innerHTML = Jobs.renderQualityReport(data.results);
    qualityReport.classList.toggle("hidden", !data.results?.length);
  }
  doneSection?.classList.remove("hidden");
  if (dlArchive) dlArchive.href = `/api/download/${jobId}`;
  Jobs.updateSidebar(null, 0, 0, false);
}

async function pollOnce(jobId, total) {
  try {
    const data = await Jobs.fetchStatus(jobId);
    const t = data.total || total;

    if (data.status === "error") {
      stopPolling();
      Jobs.clearActiveJob();
      if (activeJobStatus) {
        activeJobStatus.textContent = I18n.statusLabel("error");
        activeJobStatus.className = "status-badge status-error";
      }
      Jobs.freezeProgressUI(activeJobCard, data.error || I18n.t("progress.processingFailed"));
      setUploadEnabled(true);
      Jobs.updateSidebar(null, 0, 0, false);
      Jobs.notifyChanged();
      return;
    }

    if (data.status === "done") {
      Jobs.clearActiveJob();
      showJobDone(jobId, data, t);
      Jobs.notifyChanged();
      return;
    }

    updateProgressUI(data.progress, t, data.step_index ?? 0);

    if (resultsGrid) {
      resultsGrid.innerHTML = Jobs.renderResultThumbs(
        data.results,
        t,
        jobId,
        data.files
      );
    }

    Jobs.updateStepper(stepper, stepCurrentLabel, data.progress, t, data.step_index ?? 0);
    Jobs.updateSidebar(jobId, data.progress, t, true, data.step_index ?? 0);
  } catch {
  }
}

function updateProgressUI(progress, total, stepIndex = 0, isDone = false) {
  const pct = Jobs.progressPct(progress, total, stepIndex, isDone);
  if (progressBar) progressBar.style.width = pct + "%";
  if (progressLabel) progressLabel.textContent = I18n.progressImages(progress, total);
  if (activeProgressPct) activeProgressPct.textContent = pct + "%";

  if (progress < total && jobStartTime) {
    const elapsed = (Date.now() - jobStartTime) / 1000;
    const perItem = progress > 0 ? elapsed / progress : elapsed || 1;
    const remaining = Math.max(0, Math.round((total - progress) * perItem));
    const mins = Math.floor(remaining / 60);
    const secs = remaining % 60;
    if (activeEta) {
      activeEta.textContent = progress === 0
        ? I18n.t("progress.etaCalculating")
        : I18n.t("progress.eta", { mins, secs });
    }
  } else if (progress >= total && activeEta) {
    activeEta.textContent = I18n.t("progress.complete");
  }
}

document.addEventListener("i18n:changed", () => {
  loadRecentJobs();
  if (selectedFiles.length) renderSelectedFiles();
  else if (fileCounter) fileCounter.textContent = I18n.fileCounter(0);
});

window.addEventListener("beforeunload", stopPolling);
