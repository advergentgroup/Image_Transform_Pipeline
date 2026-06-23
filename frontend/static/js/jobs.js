document.addEventListener("click", async e => {
  const downloadBtn = e.target.closest(".btn-download");
  if (downloadBtn) {
    const row = downloadBtn.closest(".job-item, .history-row");
    const jobId = row?.dataset.jobId;
    if (jobId && /^[0-9a-f-]{36}$/i.test(jobId)) {
      window.location.href = `/api/download/${jobId}`;
    }
    return;
  }

  const retryBtn = e.target.closest(".btn-retry");
  if (retryBtn) {
    window.location.href = "/new-job";
    return;
  }

  const btn = e.target.closest(".btn-delete");
  if (!btn) return;

  const row = btn.closest(".job-item, .history-row");
  if (!row) return;

  if (!confirm(I18n.t("confirm.deleteJob"))) return;

  const jobId = row.dataset.jobId;
  if (jobId && /^[0-9a-f-]{36}$/i.test(jobId)) {
    try {
      const res = await fetch(`/api/jobs/${jobId}`, { method: "DELETE" });
      if (!res.ok) {
        alert(I18n.t("error.deleteFailed"));
        return;
      }
    } catch {
      alert(I18n.t("error.network"));
      return;
    }
  }

  Jobs.notifyChanged();
});
