window.Jobs = (() => {
  const THUMBS = ["jt-a", "jt-b", "jt-c", "jt-d", "jt-e", "jt-f", "jt-g", "jt-h", "jt-i", "jt-j", "jt-k", "jt-l", "jt-m", "jt-n", "jt-o"];
  const STEPS = ["Uniquifying", "Vectorizing", "3D Transform", "Hive Check", "Complete"];

  const ICONS = {
    download: '<svg viewBox="0 0 16 16" fill="none" aria-hidden="true"><path d="M8 2v8M5 7l3 3 3-3M3 12h10" stroke="currentColor" stroke-width="1.4" stroke-linecap="round" stroke-linejoin="round"/></svg>',
    delete: '<svg viewBox="0 0 16 16" fill="none" aria-hidden="true"><path d="M3 4h10M5.5 4V3a1 1 0 011-1h3a1 1 0 011 1v1M6.5 7v4M9.5 7v4M4.5 4l.6 8.2a1 1 0 001 1h3.8a1 1 0 001-1L11.5 4" stroke="currentColor" stroke-width="1.4" stroke-linecap="round" stroke-linejoin="round"/></svg>',
    retry: '<svg viewBox="0 0 16 16" fill="none" aria-hidden="true"><path d="M11.5 2.5V5h2.5" stroke="currentColor" stroke-width="1.4" stroke-linecap="round" stroke-linejoin="round"/><path d="M14 5.2A5.5 5.5 0 1 1 4.2 11.8" stroke="currentColor" stroke-width="1.4" stroke-linecap="round" stroke-linejoin="round"/></svg>',
  };

  function shortId(jobId) {
    return "#" + (jobId || "").slice(0, 4).toUpperCase();
  }

  function uiStatus(status) {
    if (status === "done") return "completed";
    if (status === "error") return "error";
    return "processing";
  }

  function statusBadge(status) {
    if (status === "done") return { cls: "status-done", label: "Completed" };
    if (status === "error") return { cls: "status-error", label: "Error" };
    return { cls: "status-processing", label: "Processing" };
  }

  function formatDate(ts) {
    if (!ts) return "—";
    const d = new Date(typeof ts === "number" && ts < 1e12 ? ts * 1000 : ts);
    const now = new Date();
    const sameDay = d.toDateString() === now.toDateString();
    const yesterday = new Date(now);
    yesterday.setDate(yesterday.getDate() - 1);
    const isYesterday = d.toDateString() === yesterday.toDateString();
    const time = d.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
    if (sameDay) return `Today, ${time}`;
    if (isYesterday) return `Yesterday, ${time}`;
    return d.toLocaleDateString([], { month: "short", day: "numeric" }) + ", " + time;
  }

  function avgHive(job) {
    if (job.avg_hive != null) return job.avg_hive;
    if (!job.results?.length) return null;
    const scores = [];
    job.results.forEach(r => {
      if (r.hive_vector != null) scores.push(r.hive_vector);
      if (r.hive_3d != null) scores.push(r.hive_3d);
      if (r.hive_score != null) scores.push(r.hive_score);
    });
    if (!scores.length) return null;
    return Math.round(scores.reduce((a, b) => a + b, 0) / scores.length * 10) / 10;
  }

  function hiveChip(job) {
    const score = avgHive(job);
    const ui = uiStatus(job.status);
    if (ui === "processing" || score == null) {
      return `<span class="score-chip score-warn">—</span>`;
    }
    const cls = score <= 12 ? "score-good" : score <= 18 ? "score-warn" : "score-bad";
    return `<span class="score-chip ${cls}">${score}% AI</span>`;
  }

  function fileUrl(jobId, filename) {
    return `/api/jobs/${jobId}/file/${encodeURIComponent(filename)}`;
  }

  function renderThumbs(job, index) {
    const files = job.files || [];
    if (job.job_id && files.length) {
      return files.slice(0, 3).map(name =>
        `<img class="jt jt-img" src="${fileUrl(job.job_id, name)}" alt="" loading="lazy" />`
      ).join("");
    }

    const a = THUMBS[index % THUMBS.length];
    const b = THUMBS[(index + 1) % THUMBS.length];
    const c = THUMBS[(index + 2) % THUMBS.length];
    return `<span class="jt ${a}"></span><span class="jt ${b}"></span><span class="jt ${c}"></span>`;
  }

  function renderActions(status) {
    const ui = uiStatus(status);
    if (ui === "error") {
      return `<button class="icon-btn icon-btn-sm btn-retry" type="button" aria-label="Retry job">${ICONS.retry}</button>
        <button class="icon-btn icon-btn-sm btn-delete" type="button" aria-label="Delete">${ICONS.delete}</button>`;
    }
    if (ui === "processing") {
      return `<span class="job-action-spacer" aria-hidden="true"></span>
        <button class="icon-btn icon-btn-sm btn-delete" type="button" aria-label="Delete">${ICONS.delete}</button>`;
    }
    return `<button class="icon-btn icon-btn-sm btn-download" type="button" aria-label="Download archive">${ICONS.download}</button>
      <button class="icon-btn icon-btn-sm btn-delete" type="button" aria-label="Delete">${ICONS.delete}</button>`;
  }

  function renderHistoryRow(job, index) {
    const badge = statusBadge(job.status);
    const ui = uiStatus(job.status);
    return `<li class="history-row" data-job-id="${job.job_id}" data-status="${ui}">
      <div class="ht-col ht-job">
        <div class="job-thumbs">${renderThumbs(job, index)}</div>
        <div class="job-info"><span class="job-info-id">Job ${shortId(job.job_id)}</span></div>
      </div>
      <span class="ht-col ht-date">${formatDate(job.created_at)}</span>
      <span class="ht-col ht-files">${job.total || 0} files</span>
      <span class="ht-col ht-score">${hiveChip(job)}</span>
      <span class="ht-col ht-status"><span class="status-badge ${badge.cls}">${badge.label}</span></span>
      <div class="ht-col ht-actions job-actions">${renderActions(job.status)}</div>
    </li>`;
  }

  function renderRecentItem(job, index) {
    const badge = statusBadge(job.status);
    return `<li class="job-item" data-job-id="${job.job_id}" data-status="${uiStatus(job.status)}">
      <div class="job-thumbs">${renderThumbs(job, index)}</div>
      <div class="job-info">
        <span class="job-info-id">Job ${shortId(job.job_id)}</span>
        <span class="job-info-time">${formatDate(job.created_at)}</span>
      </div>
      <span class="job-files">${job.total || 0} files</span>
      <span class="status-badge ${badge.cls}">${badge.label}</span>
      <div class="job-actions">${renderActions(job.status)}</div>
    </li>`;
  }

  function renderResultThumbs(results, total, jobId, files) {
    if (!jobId) return "";

    const pool = files?.length
      ? files
      : (results || []).map(r => r.filename).filter(Boolean);
    if (!pool.length) return "";

    const doneCount = results?.length || 0;
    const maxVisible = 5;
    const visible = pool.slice(0, maxVisible);

    const thumbs = visible.map((name, i) => {
      const done = i < doneCount;
      const cls = done ? "thumb thumb-result" : "thumb thumb-pending";
      return `<div class="${cls}" title="${name}"><img src="${fileUrl(jobId, name)}" alt="" loading="lazy" /></div>`;
    }).join("");

    const remaining = Math.max(0, (total || pool.length) - maxVisible);
    const more = remaining > 0 ? `<div class="thumb thumb-more">+${remaining}</div>` : "";
    return thumbs + more;
  }

  function updateStepper(stepper, stepCurrentLabel, progress, total) {
    if (!stepper || !stepCurrentLabel) return;

    const steps = stepper.querySelectorAll(".step");
    const lines = stepper.querySelectorAll(".step-line");

    let activeIdx = 0;
    if (progress >= total && total > 0) {
      activeIdx = 4;
    } else if (progress > 0) {
      activeIdx = Math.min(3, Math.floor((progress / total) * 4) + 1);
    }

    if (stepCurrentLabel.textContent !== STEPS[activeIdx]) {
      stepCurrentLabel.classList.remove("is-changing");
      void stepCurrentLabel.offsetWidth;
      stepCurrentLabel.textContent = STEPS[activeIdx];
      stepCurrentLabel.classList.add("is-changing");
    }

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

    lines.forEach((line, i) => line.classList.toggle("done", i < activeIdx));
  }

  function updateSidebar(jobId, progress, total, visible) {
    const sidebar = document.getElementById("sidebarJob");
    const title = document.getElementById("sidebarJobTitle");
    const meta = document.getElementById("sidebarJobMeta");
    const bar = document.getElementById("sidebarProgressBar");
    if (!sidebar) return;

    if (!visible) {
      sidebar.classList.add("hidden");
      return;
    }

    sidebar.classList.remove("hidden");
    if (title) title.textContent = "Job " + shortId(jobId);
    if (meta) meta.textContent = `${progress} / ${total} images`;
    if (bar) bar.style.width = (total > 0 ? Math.round(progress / total * 100) : 0) + "%";
  }

  async function fetchJobs() {
    const res = await fetch("/api/jobs");
    if (!res.ok) throw new Error("jobs_fetch_failed");
    const data = await res.json();
    return Array.isArray(data) ? data : (data.jobs || []);
  }

  async function fetchStats() {
    const res = await fetch("/api/stats");
    if (!res.ok) throw new Error("stats_fetch_failed");
    return res.json();
  }

  async function fetchStatus(jobId) {
    const res = await fetch(`/api/status/${jobId}`);
    if (!res.ok) throw new Error("status_fetch_failed");
    return res.json();
  }

  function notifyChanged() {
    document.dispatchEvent(new CustomEvent("jobs:changed"));
  }

  const ACTIVE_JOB_KEY = "itp_active_job";

  function saveActiveJob(jobId, total) {
    sessionStorage.setItem(ACTIVE_JOB_KEY, JSON.stringify({
      jobId,
      total,
      startedAt: Date.now(),
    }));
  }

  function clearActiveJob() {
    sessionStorage.removeItem(ACTIVE_JOB_KEY);
  }

  function getActiveJob() {
    try {
      const raw = sessionStorage.getItem(ACTIVE_JOB_KEY);
      return raw ? JSON.parse(raw) : null;
    } catch {
      return null;
    }
  }

  function freezeProgressUI(root, message) {
    if (!root) return;

    root.classList.add("job-state-error");
    root.querySelector("#stepCurrent")?.classList.add("hidden");

    const stepperEl = root.querySelector("#stepper");
    if (stepperEl) {
      stepperEl.querySelectorAll(".step").forEach(step => {
        step.classList.remove("active", "done");
        const dot = step.querySelector(".step-dot");
        if (dot) {
          dot.className = "step-dot";
          dot.innerHTML = "";
        }
      });
      stepperEl.querySelectorAll(".step-line").forEach(line => line.classList.remove("done"));
    }

    const eta = root.querySelector("#activeEta");
    if (eta) eta.textContent = "Failed";

    root.querySelector(".progress-fill")?.classList.add("progress-fill-error");

    const text = root.querySelector("#jobErrorText");
    if (text) text.textContent = message || "Processing failed.";
    root.querySelector("#jobErrorPanel")?.classList.remove("hidden");
  }

  function resetProgressUI(root) {
    if (!root) return;

    root.classList.remove("job-state-error");
    root.querySelector("#stepCurrent")?.classList.remove("hidden");
    root.querySelector("#jobErrorPanel")?.classList.add("hidden");
    root.querySelector(".progress-fill")?.classList.remove("progress-fill-error");
  }

  async function syncSidebarFromApi() {
    if (!document.getElementById("sidebarJob")) return;

    try {
      const jobs = await fetchJobs();
      const active = jobs.find(j => isActive(j.status));
      if (active) {
        updateSidebar(active.job_id, active.progress, active.total, true);
      } else {
        updateSidebar(null, 0, 0, false);
      }
    } catch {
    }
  }

  function isActive(status) {
    return status === "pending" || status === "processing";
  }

  return {
    STEPS,
    shortId,
    uiStatus,
    statusBadge,
    formatDate,
    avgHive,
    hiveChip,
    renderHistoryRow,
    renderRecentItem,
    renderResultThumbs,
    renderActions,
    updateStepper,
    updateSidebar,
    fetchJobs,
    fetchStats,
    fetchStatus,
    notifyChanged,
    saveActiveJob,
    clearActiveJob,
    getActiveJob,
    freezeProgressUI,
    resetProgressUI,
    syncSidebarFromApi,
    isActive,
  };
})();

document.addEventListener("jobs:changed", () => {
  Jobs.syncSidebarFromApi();
});
