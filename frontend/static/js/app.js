const dropzone          = document.getElementById("dropzone");
const browseBtn         = document.getElementById("browseBtn");
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
const dlArchive         = document.getElementById("dlArchive");

const recentJobsList    = document.getElementById("recentJobsList");
const recentLoading     = document.getElementById("recentLoading");
const recentEmpty       = document.getElementById("recentEmpty");

const statImages        = document.getElementById("statImages");
const statSuccess       = document.getElementById("statSuccess");
const statFailed        = document.getElementById("statFailed");
const statHive          = document.getElementById("statHive");

let pollingTimer = null;
let jobStartTime = null;

if (browseBtn && dropzone) {
  browseBtn.addEventListener("click", e => {
    e.stopPropagation();
    window.location.href = "/new-job";
  });

  dropzone.addEventListener("click", e => {
    if (e.target.closest(".btn") || e.target.closest("a") || e.target.closest(".file-list")) return;
    window.location.href = "/new-job";
  });
}

document.addEventListener("jobs:changed", () => {
  loadStats();
  loadRecentJobs();
  loadActiveJob();
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

  try {
    const jobs = await Jobs.fetchJobs();
    const active = jobs.find(j => Jobs.isActive(j.status));

    if (!active) {
      stopPolling();
      showActiveEmpty();
      Jobs.updateSidebar(null, 0, 0, false);
      return;
    }

    showActivePanel(active);
    jobStartTime = Date.now();
    startPolling(active.job_id, active.total);
    await pollOnce(active.job_id, active.total);
  } catch {
    stopPolling();
    showActiveEmpty();
    Jobs.updateSidebar(null, 0, 0, false);
  }
}

function showActiveEmpty() {
  activeJobEmpty?.classList.remove("hidden");
  activeJobBody?.classList.add("hidden");
  activeJobHeader?.classList.add("hidden");
}

function showActivePanel(job) {
  activeJobEmpty?.classList.add("hidden");
  activeJobBody?.classList.remove("hidden");
  activeJobHeader?.classList.remove("hidden");
  doneSection?.classList.add("hidden");
  stepCurrent?.classList.remove("hidden");

  if (activeJobId) activeJobId.textContent = "Job " + Jobs.shortId(job.job_id);
  if (activeJobStatus) {
    activeJobStatus.textContent = "Processing";
    activeJobStatus.className = "status-badge status-processing";
  }

  updateProgressUI(job.progress || 0, job.total || 0);
  Jobs.updateSidebar(job.job_id, job.progress || 0, job.total || 0, true);
  Jobs.updateStepper(stepper, stepCurrentLabel, job.progress || 0, job.total || 0);

  if (resultsGrid) {
    resultsGrid.innerHTML = Jobs.renderResultThumbs(job.results, job.total);
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

async function pollOnce(jobId, total) {
  try {
    const data = await Jobs.fetchStatus(jobId);
    const t = data.total || total;

    updateProgressUI(data.progress, t);

    if (resultsGrid) {
      resultsGrid.innerHTML = Jobs.renderResultThumbs(data.results, t);
    }

    Jobs.updateStepper(stepper, stepCurrentLabel, data.progress, t);
    Jobs.updateSidebar(jobId, data.progress, t, Jobs.isActive(data.status));

    if (data.status === "done") {
      stopPolling();
      if (activeJobStatus) {
        activeJobStatus.textContent = "Completed";
        activeJobStatus.className = "status-badge status-done";
      }
      if (activeEta) activeEta.textContent = "Complete";
      stepCurrent?.classList.add("hidden");
      doneSection?.classList.remove("hidden");
      if (dlArchive) dlArchive.href = `/api/download/${jobId}`;
      Jobs.updateSidebar(null, 0, 0, false);
      Jobs.notifyChanged();
    }

    if (data.status === "error") {
      stopPolling();
      if (activeJobStatus) {
        activeJobStatus.textContent = "Error";
        activeJobStatus.className = "status-badge status-error";
      }
      if (activeEta) activeEta.textContent = "Failed";
      Jobs.updateSidebar(null, 0, 0, false);
      Jobs.notifyChanged();
    }
  } catch {
  }
}

function updateProgressUI(progress, total) {
  const pct = total > 0 ? Math.round((progress / total) * 100) : 0;
  if (progressBar) progressBar.style.width = pct + "%";
  if (progressLabel) progressLabel.textContent = `${progress} / ${total} images`;
  if (activeProgressPct) activeProgressPct.textContent = pct + "%";

  if (progress < total && jobStartTime) {
    const elapsed = (Date.now() - jobStartTime) / 1000;
    const perItem = progress > 0 ? elapsed / progress : elapsed || 1;
    const remaining = Math.max(0, Math.round((total - progress) * perItem));
    const mins = Math.floor(remaining / 60);
    const secs = remaining % 60;
    if (activeEta) {
      activeEta.textContent = progress === 0 ? "ETA calculating…" : `ETA ${mins}m ${secs}s`;
    }
  } else if (progress >= total && activeEta) {
    activeEta.textContent = "Complete";
  }
}

window.addEventListener("beforeunload", stopPolling);
