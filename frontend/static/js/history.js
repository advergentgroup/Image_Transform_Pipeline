const searchInput  = document.getElementById("searchInput");
const filterPills  = document.getElementById("filterPills");
const historyList    = document.getElementById("historyList");
const historyEmpty   = document.getElementById("historyEmpty");
const historyEmptyText = document.getElementById("historyEmptyText");
const historyLoading = document.getElementById("historyLoading");

let activeFilter = "all";
let allJobs = [];

if (filterPills) {
  filterPills.addEventListener("click", e => {
    const pill = e.target.closest(".filter-pill");
    if (!pill) return;
    filterPills.querySelectorAll(".filter-pill").forEach(p => p.classList.remove("active"));
    pill.classList.add("active");
    activeFilter = pill.dataset.filter;
    applyFilters();
  });
}

if (searchInput) {
  searchInput.addEventListener("input", applyFilters);
}

document.addEventListener("jobs:changed", loadJobs);
document.addEventListener("i18n:changed", () => {
  loadJobs();
});

loadJobs();
Jobs.syncSidebarFromApi();
setInterval(loadJobs, 4000);
setInterval(() => Jobs.syncSidebarFromApi(), 4000);

async function loadJobs() {
  if (!historyList) return;

  historyLoading?.classList.remove("hidden");
  historyEmpty?.classList.add("hidden");
  historyList.innerHTML = "";

  try {
    allJobs = await Jobs.fetchJobs();
    historyList.innerHTML = allJobs.map((job, i) => Jobs.renderHistoryRow(job, i)).join("");
    applyFilters();
  } catch {
    allJobs = [];
    historyList.innerHTML = "";
    if (historyEmptyText) historyEmptyText.textContent = I18n.t("history.loadError");
    historyEmpty?.classList.remove("hidden");
  } finally {
    historyLoading?.classList.add("hidden");
  }
}

function applyFilters() {
  if (!historyList || !historyEmpty) return;

  const query = (searchInput?.value || "").trim().toLowerCase();
  const rows = historyList.querySelectorAll(".history-row");
  let visible = 0;

  if (allJobs.length === 0 && rows.length === 0) {
    if (historyEmptyText) historyEmptyText.textContent = I18n.t("history.empty");
    historyEmpty.classList.remove("hidden");
    return;
  }

  rows.forEach(row => {
    const jobId = (row.dataset.jobId || "").toLowerCase();
    const status = row.dataset.status || "";
    const short = jobId.slice(0, 4);

    const matchFilter = activeFilter === "all" || status === activeFilter;
    const matchSearch = !query || jobId.includes(query) || short.includes(query.replace("#", ""));

    const show = matchFilter && matchSearch;
    row.classList.toggle("hidden", !show);
    if (show) visible++;
  });

  if (visible === 0) {
    if (historyEmptyText) {
      historyEmptyText.textContent = query || activeFilter !== "all"
        ? I18n.t("history.emptySearch")
        : I18n.t("history.empty");
    }
    historyEmpty.classList.remove("hidden");
  } else {
    historyEmpty.classList.add("hidden");
  }
}
