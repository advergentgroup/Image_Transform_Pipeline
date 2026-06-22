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
const dlArchive      = document.getElementById("dlArchive");

const STEPS = ["Uniquifying", "Vectorizing", "3D Transform", "Hive Check", "Complete"];

let selectedFiles = [];
let pollingTimer  = null;
let jobStartTime  = null;
let previewUrls   = [];
let currentJobId  = null;

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
  fileCounter.textContent = "0 / 10 files";
  errorMsg.textContent = "";
}

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

  previewUrls.forEach(url => URL.revokeObjectURL(url));
  previewUrls = [];
  selectedFiles = valid;
  renderFiles();
  processBtn.disabled = false;
  clearBtn.classList.remove("hidden");
}

function renderFiles() {
  fileCounter.textContent = `${selectedFiles.length} / 10 files`;

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
      showError(data.error || "Upload failed.");
      processBtn.disabled = false;
      browseBtn.disabled = false;
      clearBtn.disabled = false;
      return;
    }

    showProgress(data.job_id, data.file_count);

  } catch {
    showError("Network error. Please try again.");
    processBtn.disabled = false;
    browseBtn.disabled = false;
    clearBtn.disabled = false;
  }
});

function showProgress(jobId, total) {
  currentJobId = jobId;
  jobStartTime = Date.now();
  const shortId = "#" + jobId.slice(0, 4).toUpperCase();

  progressCard.classList.remove("hidden");
  progressCard.scrollIntoView({ behavior: "smooth", block: "start" });

  activeJobId.textContent = "Job " + shortId;
  activeJobStatus.textContent = "Processing";
  activeJobStatus.className = "status-badge status-processing";
  doneSection.classList.add("hidden");
  stepCurrent.classList.remove("hidden");

  updateProgressUI(0, total);
  resultsGrid.innerHTML = "";
  updateStepper(0, total);
  Jobs.updateSidebar(jobId, 0, total, true);

  pollingTimer = setInterval(() => pollStatus(jobId, total), 2000);
}

function updateProgressUI(progress, total) {
  const pct = total > 0 ? Math.round((progress / total) * 100) : 0;
  progressBar.style.width = pct + "%";
  if (currentJobId) Jobs.updateSidebar(currentJobId, progress, total, true);
  progressLabel.textContent = `${progress} / ${total} images`;
  activeProgressPct.textContent = pct + "%";

  if (progress < total && jobStartTime) {
    const elapsed = (Date.now() - jobStartTime) / 1000;
    const perItem = progress > 0 ? elapsed / progress : elapsed || 1;
    const remaining = Math.max(0, Math.round((total - progress) * perItem));
    const mins = Math.floor(remaining / 60);
    const secs = remaining % 60;
    activeEta.textContent = progress === 0 ? "ETA calculating…" : `ETA ${mins}m ${secs}s`;
  } else if (progress >= total) {
    activeEta.textContent = "Complete";
  }
}

function animateStepLabel(el, text) {
  if (!el || el.textContent === text) return;
  el.classList.remove("is-changing");
  void el.offsetWidth;
  el.textContent = text;
  el.classList.add("is-changing");
}

function updateStepper(progress, total) {
  const steps = stepper.querySelectorAll(".step");
  const lines = stepper.querySelectorAll(".step-line");

  let activeIdx = 0;
  if (progress >= total && total > 0) {
    activeIdx = 4;
  } else if (progress > 0) {
    const ratio = progress / total;
    activeIdx = Math.min(3, Math.floor(ratio * 4) + 1);
  }

  animateStepLabel(stepCurrentLabel, STEPS[activeIdx]);

  steps.forEach((step, i) => {
    step.classList.remove("done", "active");
    const dot = step.querySelector(".step-dot");
    if (i < activeIdx) {
      step.classList.add("done");
      if (dot && !dot.querySelector("svg")) {
        dot.innerHTML = '<svg viewBox="0 0 12 12" fill="none"><path d="M2.5 6l2.5 2.5 4.5-5" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/></svg>';
      }
    } else if (i === activeIdx) {
      step.classList.add("active");
      if (dot) {
        dot.innerHTML = "";
        dot.className = "step-dot step-dot-glow";
      }
    } else if (dot) {
      dot.className = "step-dot";
      dot.innerHTML = "";
    }
  });

  lines.forEach((line, i) => {
    line.classList.toggle("done", i < activeIdx);
  });
}

async function pollStatus(jobId, total) {
  try {
    const res  = await fetch(`/api/status/${jobId}`);
    const data = await res.json();

    updateProgressUI(data.progress, total);
    renderResults(data.results, total);
    updateStepper(data.progress, total);

    if (data.status === "done") {
      clearInterval(pollingTimer);
      showDone(jobId);
      Jobs.notifyChanged();
    }

    if (data.status === "error") {
      clearInterval(pollingTimer);
      activeJobStatus.textContent = "Error";
      activeJobStatus.className = "status-badge status-error";
      showError(data.error || "Processing failed.");
      processBtn.disabled = false;
      browseBtn.disabled = false;
      clearBtn.disabled = false;
      Jobs.updateSidebar(null, 0, 0, false);
      Jobs.notifyChanged();
    }

  } catch {
  }
}

function renderResults(results, total) {
  if (!results || results.length === 0) return;

  const remaining = Math.max(0, total - results.length);
  const thumbs = results.map((r, i) =>
    `<div class="thumb thumb-result" style="background:linear-gradient(135deg,hsl(${i * 47},70%,50%),hsl(${i * 47 + 30},60%,35%))" title="${r.filename}"></div>`
  ).join("");

  const more = remaining > 0
    ? `<div class="thumb thumb-more">+${remaining}</div>`
    : "";

  resultsGrid.innerHTML = thumbs + more;
}

function showDone(jobId) {
  activeJobStatus.textContent = "Completed";
  activeJobStatus.className = "status-badge status-done";
  activeEta.textContent = "Complete";
  stepCurrent.classList.add("hidden");
  updateStepper(999, 1);
  doneSection.classList.remove("hidden");
  dlArchive.href = `/api/download/${jobId}`;
  Jobs.updateSidebar(null, 0, 0, false);
}

function showError(msg) {
  errorMsg.textContent = msg;
}
