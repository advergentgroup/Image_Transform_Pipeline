window.Jobs = (() => {
  const THUMBS = ["jt-a", "jt-b", "jt-c", "jt-d", "jt-e", "jt-f", "jt-g", "jt-h", "jt-i", "jt-j", "jt-k", "jt-l", "jt-m", "jt-n", "jt-o"];

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
    if (status === "done") return { cls: "status-done", label: I18n.statusLabel("done") };
    if (status === "error") return { cls: "status-error", label: I18n.statusLabel("error") };
    return { cls: "status-processing", label: I18n.statusLabel("processing") };
  }

  function formatDate(ts) {
    if (!ts) return "—";
    const d = new Date(typeof ts === "number" && ts < 1e12 ? ts * 1000 : ts);
    const now = new Date();
    const sameDay = d.toDateString() === now.toDateString();
    const yesterday = new Date(now);
    yesterday.setDate(yesterday.getDate() - 1);
    const isYesterday = d.toDateString() === yesterday.toDateString();
    const time = d.toLocaleTimeString(I18n.locale(), { hour: "2-digit", minute: "2-digit" });
    if (sameDay) return I18n.t("date.today", { time });
    if (isYesterday) return I18n.t("date.yesterday", { time });
    return d.toLocaleDateString(I18n.locale(), { month: "short", day: "numeric" }) + ", " + time;
  }

  function secondHiveKey(result) {
    if (result.hive_turnaround != null) return "hive_turnaround";
    if (result.hive_3d != null) return "hive_3d";
    return null;
  }

  function avgHive(job) {
    if (job.avg_hive != null) return job.avg_hive;
    if (!job.results?.length) return null;
    const scores = [];
    job.results.forEach(r => {
      if (r.hive_vector != null) scores.push(r.hive_vector);
      if (r.hive_turnaround != null) scores.push(r.hive_turnaround);
      else if (r.hive_3d != null) scores.push(r.hive_3d);
      if (r.hive_score != null) scores.push(r.hive_score);
    });
    if (!scores.length) return null;
    return Math.round(scores.reduce((a, b) => a + b, 0) / scores.length * 10) / 10;
  }

  function hiveScoreClass(score) {
    if (score == null || score < 0) return "score-warn";
    if (score <= 12) return "score-good";
    if (score <= 18) return "score-warn";
    return "score-bad";
  }

  function resultRowAvg(result) {
    const scores = [];
    if (result.hive_vector != null && result.hive_vector >= 0) scores.push(result.hive_vector);
    const k2 = secondHiveKey(result);
    if (k2 && result[k2] >= 0) scores.push(result[k2]);
    if (!scores.length) return null;
    return Math.round(scores.reduce((a, b) => a + b, 0) / scores.length * 10) / 10;
  }

  function formatHiveScoreLine(score, label) {
    if (score == null) {
      return `<span class="hive-score-line score-pending">${label}: —</span>`;
    }
    if (score < 0) {
      return `<span class="hive-score-line score-failed">${label}: ${I18n.t("hive.checkFailed")}</span>`;
    }
    const cls = hiveScoreClass(score);
    return `<span class="hive-score-line ${cls}">${label}: ${I18n.t("job.hiveAi", { score })}</span>`;
  }

  function renderQualityCell(score) {
    if (score == null) return `<span class="score-chip score-warn">—</span>`;
    if (score < 0) return `<span class="score-chip score-warn">${I18n.t("hive.checkFailed")}</span>`;
    const cls = hiveScoreClass(score);
    return `<span class="score-chip ${cls}">${I18n.t("job.hiveAi", { score })}</span>`;
  }

  function renderQualityReport(results) {
    if (!results?.length) return "";

    const hasTurnaround = results.some(r => r.hive_turnaround != null);
    const col2Label = hasTurnaround ? I18n.t("hive.colTurnaround") : I18n.t("hive.col3d");

    const rows = results.map(r => {
      const avg = resultRowAvg(r);
      const k2 = secondHiveKey(r);
      const name = r.filename || "—";
      return `<tr>
        <td class="qr-file" title="${name}">${name}</td>
        <td>${renderQualityCell(r.hive_vector)}</td>
        <td>${renderQualityCell(k2 ? r[k2] : null)}</td>
        <td>${renderQualityCell(avg)}</td>
      </tr>`;
    }).join("");

    return `<div class="quality-report">
      <h3 class="quality-report-title">${I18n.t("hive.qualityReport")}</h3>
      <div class="quality-table-wrap">
        <table class="quality-table">
          <thead>
            <tr>
              <th>${I18n.t("hive.colFile")}</th>
              <th>${I18n.t("hive.colVector")}</th>
              <th>${col2Label}</th>
              <th>${I18n.t("hive.colAvg")}</th>
            </tr>
          </thead>
          <tbody>${rows}</tbody>
        </table>
      </div>
    </div>`;
  }

  function hiveChip(job) {
    const score = avgHive(job);
    const ui = uiStatus(job.status);
    if (ui === "processing" || score == null) {
      return `<span class="score-chip score-warn">—</span>`;
    }
    const cls = hiveScoreClass(score);
    return `<span class="score-chip ${cls}">${I18n.t("job.hiveAi", { score })}</span>`;
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
      return `<button class="icon-btn icon-btn-sm btn-retry" type="button" aria-label="${I18n.t("aria.retryJob")}">${ICONS.retry}</button>
        <button class="icon-btn icon-btn-sm btn-delete" type="button" aria-label="${I18n.t("aria.delete")}">${ICONS.delete}</button>`;
    }
    if (ui === "processing") {
      return `<span class="job-action-spacer" aria-hidden="true"></span>
        <button class="icon-btn icon-btn-sm btn-delete" type="button" aria-label="${I18n.t("aria.delete")}">${ICONS.delete}</button>`;
    }
    return `<button class="icon-btn icon-btn-sm btn-download" type="button" aria-label="${I18n.t("aria.downloadArchive")}">${ICONS.download}</button>
      <button class="icon-btn icon-btn-sm btn-delete" type="button" aria-label="${I18n.t("aria.delete")}">${ICONS.delete}</button>`;
  }

  function renderHistoryRow(job, index) {
    const badge = statusBadge(job.status);
    const ui = uiStatus(job.status);
    return `<li class="history-row" data-job-id="${job.job_id}" data-status="${ui}">
      <div class="ht-col ht-job">
        <div class="job-thumbs">${renderThumbs(job, index)}</div>
        <div class="job-info"><span class="job-info-id">${I18n.jobLabel(shortId(job.job_id))}</span></div>
      </div>
      <span class="ht-col ht-date">${formatDate(job.created_at)}</span>
      <span class="ht-col ht-files">${I18n.t("job.files", { count: job.total || 0 })}</span>
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
        <span class="job-info-id">${I18n.jobLabel(shortId(job.job_id))}</span>
        <span class="job-info-time">${formatDate(job.created_at)}</span>
      </div>
      <span class="job-files">${I18n.t("job.files", { count: job.total || 0 })}</span>
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

    const resultByFile = {};
    (results || []).forEach(r => {
      if (r.filename) resultByFile[r.filename] = r;
    });

    const vectorLabel = I18n.t("hive.vector");
    const hasTurnaround = (results || []).some(r => r.hive_turnaround != null);
    const secondLabel = hasTurnaround ? I18n.t("hive.turnaround") : I18n.t("hive.threed");

    const cards = pool.map(name => {
      const result = resultByFile[name];
      const done = !!result;
      const cardCls = done ? "result-card result-card-done" : "result-card result-card-pending";
      const k2 = done ? secondHiveKey(result) : null;
      const scoresHtml = done
        ? `<div class="result-card-scores">
            ${formatHiveScoreLine(result.hive_vector, vectorLabel)}
            ${formatHiveScoreLine(k2 ? result[k2] : null, secondLabel)}
          </div>`
        : `<div class="result-card-scores result-card-scores-pending">${I18n.t("hive.pending")}</div>`;

      return `<div class="${cardCls}">
        <div class="result-card-thumb">
          <img src="${fileUrl(jobId, name)}" alt="" loading="lazy" />
        </div>
        <div class="result-card-meta">
          <span class="result-card-name" title="${name}">${name}</span>
          ${scoresHtml}
        </div>
      </div>`;
    }).join("");

    return `<div class="result-cards">${cards}</div>`;
  }

  function progressPct(progress, total, stepIndex = 0, isDone = false) {
    if (!total || total <= 0) return 0;
    if (isDone) return 100;
    const unitsDone = progress * 4 + Math.min(4, Math.max(0, stepIndex));
    return Math.min(99, Math.round(unitsDone / (total * 4) * 100));
  }

  function updateStepper(stepper, stepCurrentLabel, progress, total, stepIndex, isDone = false) {
    if (!stepper || !stepCurrentLabel) return;

    const steps = stepper.querySelectorAll(".step");
    const lines = stepper.querySelectorAll(".step-line");

    let activeIdx = 0;
    if (isDone) {
      activeIdx = 4;
    } else if (typeof stepIndex === "number") {
      activeIdx = Math.min(4, Math.max(0, stepIndex));
    } else if (progress > 0) {
      activeIdx = Math.min(3, Math.floor((progress / total) * 4) + 1);
    }

    const stepLabel = I18n.step(activeIdx);
    if (stepCurrentLabel.textContent !== stepLabel) {
      stepCurrentLabel.classList.remove("is-changing");
      void stepCurrentLabel.offsetWidth;
      stepCurrentLabel.textContent = stepLabel;
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

  function updateSidebar(jobId, progress, total, visible, stepIndex = 0, isDone = false) {
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
    if (title) title.textContent = I18n.jobLabel(shortId(jobId));
    if (meta) meta.textContent = I18n.progressImages(progress, total);
    if (bar) bar.style.width = progressPct(progress, total, stepIndex, isDone) + "%";
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
    if (eta) eta.textContent = I18n.t("progress.failed");

    root.querySelector(".progress-fill")?.classList.add("progress-fill-error");

    const text = root.querySelector("#jobErrorText");
    if (text) text.textContent = message || I18n.t("progress.processingFailed");
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
    shortId,
    uiStatus,
    statusBadge,
    formatDate,
    avgHive,
    hiveScoreClass,
    resultRowAvg,
    hiveChip,
    renderQualityReport,
    renderHistoryRow,
    renderRecentItem,
    renderResultThumbs,
    renderActions,
    progressPct,
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

document.addEventListener("i18n:changed", () => {
  Jobs.syncSidebarFromApi();
});
