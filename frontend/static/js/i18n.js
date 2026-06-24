window.I18n = (() => {
  const STORAGE_KEY = "itp_lang";
  const SUPPORTED = ["en", "ru", "ka"];
  const STEP_KEYS = ["uniquifying", "vectorizing", "transform3d", "hive", "complete"];

  const messages = {
    en: {
      "app.name": "ImageTransform",
      "page.dashboard": "Dashboard",
      "page.newJob": "New Job",
      "page.history": "History",
      "nav.dashboard": "Dashboard",
      "nav.newJob": "New Job",
      "nav.history": "History",
      "nav.settings": "Settings",
      "topbar.newJob": "New Job",
      "topbar.pause": "Pause",
      "page.settings": "Settings",
      "settings.sub": "Edit AI prompts used before Replicate runs. API keys stay in .env.",
      "settings.promptsTitle": "AI Prompts",
      "settings.kontext3d": "3D Pixar (FLUX Kontext)",
      "settings.kontext3dHint": "Used for Archive 2 — 3D transform step.",
      "settings.legacyUnique": "Legacy uniquify (SD img2img)",
      "settings.legacyUniqueHint": "Only when UNIQUE_MODE=sd-img2img.",
      "settings.legacyPixar": "Legacy 3D (SD img2img)",
      "settings.legacyPixarHint": "Only when THREED_MODEL=sd-img2img.",
      "settings.negative": "Negative prompt (legacy img2img)",
      "settings.fluxReduxNote": "flux-redux uniquify uses image input only — no text prompt.",
      "settings.save": "Save prompts",
      "settings.reset": "Reset to defaults",
      "settings.resetConfirm": "Reset all prompts to defaults?",
      "settings.saved": "Prompts saved.",
      "settings.resetDone": "Prompts reset.",
      "settings.saveError": "Could not save settings.",
      "settings.loadError": "Could not load settings.",
      "sidebar.processing": "Processing",
      "lang.en": "English",
      "lang.ru": "Russian",
      "lang.ka": "Georgian",
      "lang.switch": "Change language",
      "hero.title": 'Transform your <span class="hero-accent">illustrations</span>',
      "hero.sub": "Into vector and 3D Pixar-style assets.",
      "stat.imagesProcessed": "Images Processed",
      "stat.successfulJobs": "Successful Jobs",
      "stat.failedJobs": "Failed Jobs",
      "stat.avgHive": "Avg Hive Score",
      "activeJob.title": "Active Job",
      "activeJob.empty": "No job is running right now.",
      "activeJob.start": "Start New Job",
      "recentJobs.title": "Recent Jobs",
      "recentJobs.viewAll": "View All",
      "recentJobs.loading": "Loading…",
      "recentJobs.empty": "No jobs yet.",
      "upload.title": "Start a new transformation",
      "upload.hint": "Drag & drop up to 10 JPG/PNG images, or browse below",
      "upload.titleLg": "Drag & drop your images here",
      "upload.hintLg": "JPG or PNG · Maximum 10 files per job",
      "upload.start": "Start Processing",
      "upload.browse": "Browse Files",
      "upload.clear": "Clear all",
      "upload.cardTitle": "Upload Images",
      "upload.pageSub": "Upload illustrations and start a new transformation pipeline.",
      "info.outputArchive": "Output Archive",
      "info.vectorDesc": "Image trace + gradient background",
      "info.threedDesc": "3D Pixar style renders",
      "info.pipelineSteps": "Pipeline Steps",
      "info.step1": "AI Uniquifying",
      "info.step2": "Vectorize + Gradient",
      "info.step3": "3D Pixar Transform",
      "info.step4": "Hive Detect Check",
      "info.step5": "ZIP & Download",
      "info.maxFiles": "Max files",
      "info.formats": "Formats",
      "info.maxUpload": "Max upload",
      "progress.title": "Processing Job",
      "progress.currentStep": "Current step:",
      "progress.images": "{progress} / {total} images",
      "progress.etaCalculating": "ETA calculating…",
      "progress.eta": "ETA {mins}m {secs}s",
      "progress.complete": "Complete",
      "progress.failed": "Failed",
      "progress.processingFailed": "Processing failed.",
      "step.uniquifying": "Uniquifying",
      "step.vectorizing": "Vectorizing",
      "step.transform3d": "3D Transform",
      "step.hive": "Hive Check",
      "step.complete": "Complete",
      "status.processing": "Processing",
      "status.completed": "Completed",
      "status.error": "Error",
      "job.label": "Job {id}",
      "job.files": "{count} files",
      "job.hiveAi": "{score}% AI",
      "hive.vector": "Vector",
      "hive.threed": "3D",
      "hive.pending": "Waiting for Hive check…",
      "hive.checkFailed": "Check failed",
      "hive.qualityReport": "Quality Report",
      "hive.colFile": "File",
      "hive.colVector": "Vector",
      "hive.col3d": "3D",
      "hive.colAvg": "Avg",
      "files.counter": "{count} / {max} files",
      "date.today": "Today, {time}",
      "date.yesterday": "Yesterday, {time}",
      "action.downloadArchive": "Download Archive",
      "action.processMore": "Process more",
      "action.viewHistory": "View History",
      "action.tryAgain": "Try Again",
      "action.backDashboard": "Back to Dashboard",
      "history.title": "Job History",
      "history.sub": "Browse and download results from all past transformations.",
      "history.search": "Search by job ID…",
      "history.filter.all": "All",
      "history.filter.completed": "Completed",
      "history.filter.processing": "Processing",
      "history.filter.error": "Error",
      "history.col.job": "Job",
      "history.col.date": "Date",
      "history.col.files": "Files",
      "history.col.score": "Avg Hive",
      "history.col.status": "Status",
      "history.col.actions": "Actions",
      "history.loading": "Loading jobs…",
      "history.empty": "No jobs yet. Start your first transformation.",
      "history.emptySearch": "No jobs match your search.",
      "history.loadError": "Could not load jobs. Check that the server is running.",
      "history.prev": "Previous",
      "history.next": "Next",
      "history.page": "Page {page} of {total}",
      "error.invalidFormat": "Please upload JPG or PNG files.",
      "error.maxFiles": "Maximum 10 files per upload.",
      "error.uploadFailed": "Upload failed.",
      "error.network": "Network error. Please try again.",
      "confirm.deleteJob": "Delete this job?",
      "error.deleteFailed": "Could not delete job.",
      "aria.retryJob": "Retry job",
      "aria.delete": "Delete",
      "aria.downloadArchive": "Download archive",
    },
    ru: {
      "app.name": "ImageTransform",
      "page.dashboard": "Панель",
      "page.newJob": "Новая задача",
      "page.history": "История",
      "nav.dashboard": "Панель",
      "nav.newJob": "Новая задача",
      "nav.history": "История",
      "nav.settings": "Настройки",
      "topbar.newJob": "Новая задача",
      "topbar.pause": "Пауза",
      "page.settings": "Настройки",
      "settings.sub": "Редактирование AI-промптов перед Replicate. API-ключи остаются в .env.",
      "settings.promptsTitle": "AI промпты",
      "settings.kontext3d": "3D Pixar (FLUX Kontext)",
      "settings.kontext3dHint": "Архив 2 — шаг 3D трансформации.",
      "settings.legacyUnique": "Legacy uniquify (SD img2img)",
      "settings.legacyUniqueHint": "Только при UNIQUE_MODE=sd-img2img.",
      "settings.legacyPixar": "Legacy 3D (SD img2img)",
      "settings.legacyPixarHint": "Только при THREED_MODEL=sd-img2img.",
      "settings.negative": "Negative prompt (legacy img2img)",
      "settings.fluxReduxNote": "flux-redux uniquify — только изображение, без текстового промпта.",
      "settings.save": "Сохранить промпты",
      "settings.reset": "Сбросить по умолчанию",
      "settings.resetConfirm": "Сбросить все промпты к значениям по умолчанию?",
      "settings.saved": "Промпты сохранены.",
      "settings.resetDone": "Промпты сброшены.",
      "settings.saveError": "Не удалось сохранить.",
      "settings.loadError": "Не удалось загрузить настройки.",
      "sidebar.processing": "Обработка",
      "lang.en": "English",
      "lang.ru": "Русский",
      "lang.ka": "ქართული",
      "lang.switch": "Сменить язык",
      "hero.title": 'Преобразуйте свои <span class="hero-accent">иллюстрации</span>',
      "hero.sub": "В векторные и 3D Pixar-ассеты.",
      "stat.imagesProcessed": "Обработано изображений",
      "stat.successfulJobs": "Успешные задачи",
      "stat.failedJobs": "Ошибки",
      "stat.avgHive": "Средний Hive Score",
      "activeJob.title": "Активная задача",
      "activeJob.empty": "Сейчас нет активных задач.",
      "activeJob.start": "Новая задача",
      "recentJobs.title": "Недавние задачи",
      "recentJobs.viewAll": "Все",
      "recentJobs.loading": "Загрузка…",
      "recentJobs.empty": "Задач пока нет.",
      "upload.title": "Начать преобразование",
      "upload.hint": "Перетащите до 10 JPG/PNG или выберите файлы ниже",
      "upload.titleLg": "Перетащите изображения сюда",
      "upload.hintLg": "JPG или PNG · Максимум 10 файлов",
      "upload.start": "Начать обработку",
      "upload.browse": "Выбрать файлы",
      "upload.clear": "Очистить",
      "upload.cardTitle": "Загрузка изображений",
      "upload.pageSub": "Загрузите иллюстрации и запустите пайплайн.",
      "info.outputArchive": "Архив результата",
      "info.vectorDesc": "Трейс + градиентный фон",
      "info.threedDesc": "3D Pixar-рендеры",
      "info.pipelineSteps": "Этапы пайплайна",
      "info.step1": "AI уникализация",
      "info.step2": "Векторизация + градиент",
      "info.step3": "3D Pixar",
      "info.step4": "Проверка Hive",
      "info.step5": "ZIP и скачивание",
      "info.maxFiles": "Макс. файлов",
      "info.formats": "Форматы",
      "info.maxUpload": "Макс. загрузка",
      "progress.title": "Обработка задачи",
      "progress.currentStep": "Текущий этап:",
      "progress.images": "{progress} / {total} изображений",
      "progress.etaCalculating": "Расчёт ETA…",
      "progress.eta": "ETA {mins}м {secs}с",
      "progress.complete": "Готово",
      "progress.failed": "Ошибка",
      "progress.processingFailed": "Обработка не удалась.",
      "step.uniquifying": "Уникализация",
      "step.vectorizing": "Векторизация",
      "step.transform3d": "3D трансформ",
      "step.hive": "Hive Check",
      "step.complete": "Готово",
      "status.processing": "Обработка",
      "status.completed": "Завершено",
      "status.error": "Ошибка",
      "job.label": "Задача {id}",
      "job.files": "{count} файлов",
      "job.hiveAi": "{score}% AI",
      "hive.vector": "Vector",
      "hive.threed": "3D",
      "hive.pending": "Ожидание Hive check…",
      "hive.checkFailed": "Проверка не удалась",
      "hive.qualityReport": "Отчёт качества",
      "hive.colFile": "Файл",
      "hive.colVector": "Vector",
      "hive.col3d": "3D",
      "hive.colAvg": "Сред.",
      "files.counter": "{count} / {max} файлов",
      "date.today": "Сегодня, {time}",
      "date.yesterday": "Вчера, {time}",
      "action.downloadArchive": "Скачать архив",
      "action.processMore": "Ещё",
      "action.viewHistory": "История",
      "action.tryAgain": "Повторить",
      "action.backDashboard": "На панель",
      "history.title": "История задач",
      "history.sub": "Просмотр и скачивание результатов.",
      "history.search": "Поиск по ID задачи…",
      "history.filter.all": "Все",
      "history.filter.completed": "Завершено",
      "history.filter.processing": "Обработка",
      "history.filter.error": "Ошибка",
      "history.col.job": "Задача",
      "history.col.date": "Дата",
      "history.col.files": "Файлы",
      "history.col.score": "Avg Hive",
      "history.col.status": "Статус",
      "history.col.actions": "Действия",
      "history.loading": "Загрузка…",
      "history.empty": "Задач пока нет. Начните первую.",
      "history.emptySearch": "Ничего не найдено.",
      "history.loadError": "Не удалось загрузить задачи. Проверьте сервер.",
      "history.prev": "Назад",
      "history.next": "Далее",
      "history.page": "Страница {page} из {total}",
      "error.invalidFormat": "Загрузите JPG или PNG.",
      "error.maxFiles": "Максимум 10 файлов.",
      "error.uploadFailed": "Ошибка загрузки.",
      "error.network": "Ошибка сети. Попробуйте снова.",
      "confirm.deleteJob": "Удалить эту задачу?",
      "error.deleteFailed": "Не удалось удалить задачу.",
      "aria.retryJob": "Повторить задачу",
      "aria.delete": "Удалить",
      "aria.downloadArchive": "Скачать архив",
    },
    ka: {
      "app.name": "ImageTransform",
      "page.dashboard": "დაფა",
      "page.newJob": "ახალი დავალება",
      "page.history": "ისტორია",
      "nav.dashboard": "დაფა",
      "nav.newJob": "ახალი დავალება",
      "nav.history": "ისტორია",
      "nav.settings": "პარამეტრები",
      "topbar.newJob": "ახალი დავალება",
      "topbar.pause": "პაუზა",
      "page.settings": "პარამეტრები",
      "settings.sub": "AI პრომპტების რედაქტირება Replicate-მდე. API გასაღებები .env-ში.",
      "settings.promptsTitle": "AI პრომპტები",
      "settings.kontext3d": "3D Pixar (FLUX Kontext)",
      "settings.kontext3dHint": "არქივი 2 — 3D ტრანსფორმის ეტაპი.",
      "settings.legacyUnique": "Legacy uniquify (SD img2img)",
      "settings.legacyUniqueHint": "მხოლოდ UNIQUE_MODE=sd-img2img-ზე.",
      "settings.legacyPixar": "Legacy 3D (SD img2img)",
      "settings.legacyPixarHint": "მხოლოდ THREED_MODEL=sd-img2img-ზე.",
      "settings.negative": "Negative prompt (legacy img2img)",
      "settings.fluxReduxNote": "flux-redux uniquify — მხოლოდ სურათი, ტექსტის გარეშე.",
      "settings.save": "პრომპტების შენახვა",
      "settings.reset": "ნაგულისხმევზე",
      "settings.resetConfirm": "ყველა პრომპტი ნაგულისხმევზე?",
      "settings.saved": "შენახულია.",
      "settings.resetDone": "გადატვირთულია.",
      "settings.saveError": "შენახვა ვერ მოხერხდა.",
      "settings.loadError": "ჩატვირთვა ვერ მოხერხდა.",
      "sidebar.processing": "დამუშავება",
      "lang.en": "English",
      "lang.ru": "Русский",
      "lang.ka": "ქართული",
      "lang.switch": "ენის შეცვლა",
      "hero.title": 'გარდაქმენით თქვენი <span class="hero-accent">ილუსტრაციები</span>',
      "hero.sub": "ვექტორულ და 3D Pixar-სტილის ასეტებად.",
      "stat.imagesProcessed": "დამუშავებული სურათები",
      "stat.successfulJobs": "წარმატებული დავალებები",
      "stat.failedJobs": "შეცდომები",
      "stat.avgHive": "საშუალო Hive Score",
      "activeJob.title": "აქტიური დავალება",
      "activeJob.empty": "ამ მომენტში აქტიური დავალება არ არის.",
      "activeJob.start": "ახალი დავალება",
      "recentJobs.title": "ბოლო დავალებები",
      "recentJobs.viewAll": "ყველა",
      "recentJobs.loading": "იტვირთება…",
      "recentJobs.empty": "დავალებები ჯერ არ არის.",
      "upload.title": "ახალი ტრანსფორმაცია",
      "upload.hint": "გადმოიტანეთ 10 JPG/PNG-მდე ან აირჩიეთ ფაილები",
      "upload.titleLg": "გადმოიტანეთ სურათები აქ",
      "upload.hintLg": "JPG ან PNG · მაქს. 10 ფაილი",
      "upload.start": "დამუშავების დაწყება",
      "upload.browse": "ფაილების არჩევა",
      "upload.clear": "გასუფთავება",
      "upload.cardTitle": "სურათების ატვირთვა",
      "upload.pageSub": "ატვირთეთ ილუსტრაციები და დაიწყეთ პაიპლაინი.",
      "info.outputArchive": "შედეგის არქივი",
      "info.vectorDesc": "Image trace + გრადიენტული ფონი",
      "info.threedDesc": "3D Pixar სტილის რენდერები",
      "info.pipelineSteps": "პაიპლაინის ეტაპები",
      "info.step1": "AI უნიკალიზაცია",
      "info.step2": "ვექტორიზაცია + გრადიენტი",
      "info.step3": "3D Pixar",
      "info.step4": "Hive Detect შემოწმება",
      "info.step5": "ZIP და ჩამოტვირთვა",
      "info.maxFiles": "მაქს. ფაილები",
      "info.formats": "ფორმატები",
      "info.maxUpload": "მაქს. ატვირთვა",
      "progress.title": "დავალების დამუშავება",
      "progress.currentStep": "მიმდინარე ეტაპი:",
      "progress.images": "{progress} / {total} სურათი",
      "progress.etaCalculating": "ETA გამოითვლება…",
      "progress.eta": "ETA {mins}წ {secs}წ",
      "progress.complete": "დასრულდა",
      "progress.failed": "შეცდომა",
      "progress.processingFailed": "დამუშავება ვერ მოხერხდა.",
      "step.uniquifying": "უნიკალიზაცია",
      "step.vectorizing": "ვექტორიზაცია",
      "step.transform3d": "3D ტრანსფორმი",
      "step.hive": "Hive Check",
      "step.complete": "დასრულება",
      "status.processing": "მუშავდება",
      "status.completed": "დასრულებული",
      "status.error": "შეცდომა",
      "job.label": "დავალება {id}",
      "job.files": "{count} ფაილი",
      "job.hiveAi": "{score}% AI",
      "hive.vector": "Vector",
      "hive.threed": "3D",
      "hive.pending": "Hive check-ის მოლოდინი…",
      "hive.checkFailed": "შემოწმება ვერ მოხერხდა",
      "hive.qualityReport": "ხარისხის ანგარიში",
      "hive.colFile": "ფაილი",
      "hive.colVector": "Vector",
      "hive.col3d": "3D",
      "hive.colAvg": "საშ.",
      "files.counter": "{count} / {max} ფაილი",
      "date.today": "დღეს, {time}",
      "date.yesterday": "გუშინ, {time}",
      "action.downloadArchive": "არქივის ჩამოტვირთვა",
      "action.processMore": "კიდევ",
      "action.viewHistory": "ისტორია",
      "action.tryAgain": "თავიდან",
      "action.backDashboard": "დაფაზე",
      "history.title": "დავალებების ისტორია",
      "history.sub": "ნახეთ და ჩამოტვირთეთ შედეგები.",
      "history.search": "ძებნა ID-ით…",
      "history.filter.all": "ყველა",
      "history.filter.completed": "დასრულებული",
      "history.filter.processing": "მუშავდება",
      "history.filter.error": "შეცდომა",
      "history.col.job": "დავალება",
      "history.col.date": "თარიღი",
      "history.col.files": "ფაილები",
      "history.col.score": "Avg Hive",
      "history.col.status": "სტატუსი",
      "history.col.actions": "მოქმედებები",
      "history.loading": "იტვირთება…",
      "history.empty": "დავალებები ჯერ არ არის. დაიწყეთ პირველი.",
      "history.emptySearch": "შედეგები ვერ მოიძებნა.",
      "history.loadError": "დავალებების ჩატვირთვა ვერ მოხერხდა.",
      "history.prev": "წინა",
      "history.next": "შემდეგი",
      "history.page": "გვ. {page} / {total}",
      "error.invalidFormat": "ატვირთეთ JPG ან PNG.",
      "error.maxFiles": "მაქსიმუმ 10 ფაილი.",
      "error.uploadFailed": "ატვირთვა ვერ მოხერხდა.",
      "error.network": "ქსელის შეცდომა. სცადეთ თავიდან.",
      "confirm.deleteJob": "წავშალოთ ეს დავალება?",
      "error.deleteFailed": "დავალების წაშლა ვერ მოხერხდა.",
      "aria.retryJob": "თავიდან ცდა",
      "aria.delete": "წაშლა",
      "aria.downloadArchive": "არქივის ჩამოტვირთვა",
    },
  };

  let lang = "en";

  function t(key, params = {}) {
    let str = messages[lang]?.[key] ?? messages.en[key] ?? key;
    Object.entries(params).forEach(([k, v]) => {
      str = str.replace(new RegExp(`\\{${k}\\}`, "g"), String(v));
    });
    return str;
  }

  function step(index) {
    const key = STEP_KEYS[index];
    return key ? t(`step.${key}`) : "";
  }

  function steps() {
    return STEP_KEYS.map((_, i) => step(i));
  }

  function locale() {
    if (lang === "ru") return "ru-RU";
    if (lang === "ka") return "ka-GE";
    return "en-US";
  }

  function fileCounter(count, max = 10) {
    return t("files.counter", { count, max });
  }

  function jobLabel(shortId) {
    return t("job.label", { id: shortId });
  }

  function progressImages(progress, total) {
    return t("progress.images", { progress, total });
  }

  function statusLabel(status) {
    if (status === "done") return t("status.completed");
    if (status === "error") return t("status.error");
    return t("status.processing");
  }

  function syncStepperLabels(root = document) {
    root.querySelectorAll(".stepper .step-label[data-i18n-step]").forEach(el => {
      el.textContent = t(`step.${el.dataset.i18nStep}`);
    });
  }

  function updateLangSwitcher() {
    const code = document.getElementById("langCode");
    const menu = document.getElementById("langMenu");
    if (code) code.textContent = lang.toUpperCase();

    document.querySelectorAll(".lang-option").forEach(btn => {
      btn.classList.toggle("active", btn.dataset.lang === lang);
    });

    if (menu) {
      menu.querySelectorAll(".lang-option").forEach(btn => {
        btn.setAttribute("aria-checked", btn.dataset.lang === lang ? "true" : "false");
      });
    }
  }

  function applyPageTitle() {
    const el = document.querySelector("[data-page-title]");
    if (el) {
      document.title = `${t(el.dataset.pageTitle)} — ${t("app.name")}`;
    }
  }

  function apply(root = document) {
    root.querySelectorAll("[data-i18n]").forEach(el => {
      el.textContent = t(el.dataset.i18n);
    });
    root.querySelectorAll("[data-i18n-html]").forEach(el => {
      el.innerHTML = t(el.dataset.i18nHtml);
    });
    root.querySelectorAll("[data-i18n-placeholder]").forEach(el => {
      el.placeholder = t(el.dataset.i18nPlaceholder);
    });
    root.querySelectorAll("[data-i18n-aria]").forEach(el => {
      el.setAttribute("aria-label", t(el.dataset.i18nAria));
    });
    syncStepperLabels(root);
    applyPageTitle();
    document.documentElement.lang = lang;
    updateLangSwitcher();
  }

  function setLang(next) {
    if (!SUPPORTED.includes(next)) return;
    lang = next;
    localStorage.setItem(STORAGE_KEY, lang);
    apply();
    document.dispatchEvent(new CustomEvent("i18n:changed"));
  }

  function initLangSwitcher() {
    const btn = document.getElementById("langBtn");
    const menu = document.getElementById("langMenu");
    if (!btn || !menu) return;

    btn.addEventListener("click", e => {
      e.stopPropagation();
      menu.classList.toggle("hidden");
      btn.setAttribute("aria-expanded", menu.classList.contains("hidden") ? "false" : "true");
    });

    menu.querySelectorAll(".lang-option").forEach(option => {
      option.addEventListener("click", () => {
        setLang(option.dataset.lang);
        menu.classList.add("hidden");
        btn.setAttribute("aria-expanded", "false");
      });
    });

    document.addEventListener("click", e => {
      if (!e.target.closest("#langSwitcher")) {
        menu.classList.add("hidden");
        btn.setAttribute("aria-expanded", "false");
      }
    });
  }

  function init() {
    const saved = localStorage.getItem(STORAGE_KEY);
    lang = SUPPORTED.includes(saved) ? saved : "en";
    initLangSwitcher();
    apply();
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init);
  } else {
    init();
  }

  return {
    t,
    step,
    steps,
    locale,
    fileCounter,
    jobLabel,
    progressImages,
    statusLabel,
    apply,
    setLang,
    get lang() { return lang; },
    STEP_KEYS,
  };
})();
