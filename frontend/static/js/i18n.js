window.I18n = (() => {
  const STORAGE_KEY = "itp_lang";
  const SUPPORTED = ["en", "ru", "ka"];
  const STEP_KEYS = ["reference", "review", "turnaround", "complete"];

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
      "settings.sub": "Edit FLUX prompts for reference and turnaround generation. API keys stay in .env.",
      "settings.promptsTitle": "AI Prompts",
      "settings.productReference": "Step 1 — Product reference",
      "settings.productReferenceHint": "Object prompt: text-only (FLUX Dev) or with style refs (Kontext).",
      "settings.styleGuided": "Style guide prefix (with style refs)",
      "settings.styleGuidedHint": "Prepended when you upload style references at job start.",
      "settings.turnaround": "Step 2 — Turnaround sheet (Qwen multi-angle)",
      "settings.turnaroundHint": "Default: Qwen camera rotations (~$0.025/view). Settings prompt is for kontext/lora only.",
      "settings.legacyTitle": "Legacy prompts",
      "settings.kontext3d": "3D Pixar (FLUX Kontext)",
      "settings.kontext3dHint": "Legacy 3D mode only.",
      "settings.legacyUnique": "Legacy uniquify (SD img2img)",
      "settings.legacyUniqueHint": "Only when UNIQUE_MODE=sd-img2img.",
      "settings.legacyPixar": "Legacy 3D (SD img2img)",
      "settings.legacyPixarHint": "Only when THREED_MODEL=sd-img2img.",
      "settings.negative": "Negative prompt (legacy img2img)",
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
      "hero.sub": "Product reference and turnaround sheets via FLUX.",
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
      "upload.generateTitle": "Generate Dataset",
      "upload.generateCount": "Products to generate",
      "upload.generateHint": "Random unique catalog objects; turnaround starts automatically after each reference.",
      "upload.styleRefsTitle": "Style references (optional)",
      "upload.styleRefsHint": "1–10 example images — same render style, different object each time.",
      "upload.styleRefsDrop": "Drag & drop style examples or click to browse",
      "upload.clearStyleRefs": "Clear style refs",
      "upload.generateStart": "Generate Products",
      "upload.orUpload": "or upload existing references",
      "upload.titleLg": "Drag & drop reference images here",
      "upload.hintLg": "JPG or PNG · Skip step 1, turnaround only · Max 10 files",
      "upload.startTurnaround": "Start Turnaround Only",
      "upload.browse": "Browse Files",
      "upload.clear": "Clear all",
      "upload.cardTitle": "Upload References",
      "upload.pageSub": "Generate product references and turnaround sheets in parallel.",
      "info.outputArchive": "Output Archive",
      "info.referenceDesc": "Catalog product reference (1:1)",
      "info.turnaroundDesc": "Five-view turnaround sheet (16:9)",
      "info.pipelineSteps": "Pipeline Steps",
      "info.step1": "Generate references (FLUX Dev / Kontext)",
      "info.modelsValue": "dev / kontext",
      "info.stepReview": "Review & download",
      "info.step2": "Turnaround (Qwen multi-angle)",
      "info.step3": "Hive Detect Check",
      "info.step4": "ZIP & Download",
      "info.maxFiles": "Max per job",
      "info.models": "Models",
      "progress.title": "Processing Job",
      "progress.currentStep": "Current step:",
      "progress.images": "{progress} / {total} images",
      "progress.etaCalculating": "ETA calculating…",
      "progress.eta": "ETA {mins}m {secs}s",
      "progress.reviewReady": "References ready — review and continue",
      "progress.complete": "Complete",
      "progress.failed": "Failed",
      "progress.processingFailed": "Processing failed.",
      "step.reference": "Reference",
      "step.review": "Review",
      "step.turnaround": "Turnaround",
      "step.complete": "Complete",
      "status.processing": "Processing",
      "status.awaiting_continue": "Review",
      "status.completed": "Completed",
      "status.error": "Error",
      "job.label": "Job {id}",
      "job.files": "{count} files",
      "job.hiveAi": "{score}% AI",
      "hive.reference": "Reference",
      "hive.vector": "Vector",
      "hive.threed": "3D",
      "hive.turnaround": "Turnaround",
      "hive.pending": "Waiting for Hive check…",
      "hive.checkFailed": "Check failed",
      "hive.qualityReport": "Quality Report",
      "hive.colFile": "File",
      "hive.colReference": "Reference",
      "hive.colVector": "Vector",
      "hive.col3d": "3D",
      "hive.colTurnaround": "Turnaround",
      "hive.colAvg": "Avg",
      "files.counter": "{count} / {max} files",
      "date.today": "Today, {time}",
      "date.yesterday": "Yesterday, {time}",
      "action.downloadArchive": "Download Archive",
      "action.continueTurnaround": "Continue to Turnaround",
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
      "generate.counter": "{count} image(s)",
      "styleRefs.counter": "{count} / {max} style refs",
      "error.generateFailed": "Generation failed.",
      "error.continueFailed": "Could not start turnaround phase.",
      "error.maxStyleRefs": "Maximum 10 style reference images.",
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
      "settings.productReference": "Шаг 1 — Референс объекта",
      "settings.productReferenceHint": "Промпт объекта: только текст (FLUX Dev) или со style refs (Kontext).",
      "settings.styleGuided": "Префикс стиля (со style refs)",
      "settings.styleGuidedHint": "Добавляется в начало, если загружены style references при старте задачи.",
      "settings.turnaround": "Шаг 2 — Turnaround (локальный GPU)",
      "settings.turnaroundHint": "Default: Qwen camera rotations (~$0.025/view). Settings prompt is for kontext/lora only.",
      "settings.kontext3d": "3D Pixar (FLUX Kontext)",
      "settings.kontext3dHint": "Только при PIPELINE_MODE=legacy-3d.",
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
      "upload.generateTitle": "Генерация датасета",
      "upload.generateCount": "Сколько объектов",
      "upload.generateHint": "Случайные объекты из каталога; turnaround стартует сразу после каждого референса.",
      "upload.styleRefsTitle": "Style references (опционально)",
      "upload.styleRefsHint": "1–10 примеров — тот же стиль рендера, каждый раз другой объект.",
      "upload.styleRefsDrop": "Перетащите примеры стиля или выберите файлы",
      "upload.clearStyleRefs": "Очистить style refs",
      "upload.generateStart": "Начать генерацию",
      "upload.orUpload": "или загрузить готовые референсы",
      "upload.titleLg": "Перетащите изображения сюда",
      "upload.hintLg": "JPG или PNG · Максимум 10 файлов",
      "upload.start": "Начать обработку",
      "upload.browse": "Выбрать файлы",
      "upload.clear": "Очистить",
      "upload.cardTitle": "Загрузка изображений",
      "upload.pageSub": "Референсы и turnaround генерируются параллельно.",
      "info.outputArchive": "Архив результата",
      "info.referenceDesc": "Каталожный референс объекта (1:1)",
      "info.turnaroundDesc": "Turnaround на 5 видов (16:9)",
      "info.pipelineSteps": "Этапы пайплайна",
      "info.step1": "Референсы (FLUX Dev / Kontext)",
      "info.modelsValue": "dev или kontext",
      "info.stepReview": "Проверка и скачивание",
      "info.step2": "Turnaround (Kontext Dev + LoRA)",
      "info.step3": "Проверка Hive",
      "info.step4": "ZIP и скачивание",
      "info.maxFiles": "Макс. за задачу",
      "info.models": "Модели",
      "progress.title": "Обработка задачи",
      "progress.currentStep": "Текущий этап:",
      "progress.images": "{progress} / {total} изображений",
      "progress.etaCalculating": "Расчёт ETA…",
      "progress.eta": "ETA {mins}м {secs}с",
      "progress.reviewReady": "Референсы готовы — проверьте и продолжите",
      "progress.complete": "Готово",
      "progress.failed": "Ошибка",
      "progress.processingFailed": "Обработка не удалась.",
      "step.reference": "Референс",
      "step.review": "Проверка",
      "step.turnaround": "Turnaround",
      "step.hive": "Hive Check",
      "step.complete": "Готово",
      "status.processing": "Обработка",
      "status.awaiting_continue": "Проверка",
      "status.completed": "Завершено",
      "status.error": "Ошибка",
      "job.label": "Задача {id}",
      "job.files": "{count} файлов",
      "job.hiveAi": "{score}% AI",
      "hive.vector": "Vector",
      "hive.threed": "3D",
      "hive.turnaround": "Turnaround",
      "hive.pending": "Ожидание Hive check…",
      "hive.checkFailed": "Проверка не удалась",
      "hive.qualityReport": "Отчёт качества",
      "hive.colFile": "Файл",
      "hive.colVector": "Vector",
      "hive.col3d": "3D",
      "hive.colTurnaround": "Turnaround",
      "hive.colAvg": "Сред.",
      "files.counter": "{count} / {max} файлов",
      "date.today": "Сегодня, {time}",
      "date.yesterday": "Вчера, {time}",
      "action.downloadArchive": "Скачать архив",
      "action.continueTurnaround": "Продолжить turnaround",
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
      "generate.counter": "{count} изображ.",
      "styleRefs.counter": "{count} / {max} style refs",
      "error.generateFailed": "Генерация не удалась.",
      "error.continueFailed": "Не удалось запустить turnaround.",
      "error.maxStyleRefs": "Максимум 10 style reference изображений.",
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
      "settings.productReference": "ნაბიჯი 1 — პროდუქტის რეფერენსი",
      "settings.productReferenceHint": "ობიექტის პრომპტი: მხოლოდ ტექსტი (FLUX Dev) ან style refs-ით (Kontext).",
      "settings.styleGuided": "სტილის პრეფიქსი (style refs-ით)",
      "settings.styleGuidedHint": "ემატება დასაწყისში, თუ დავალების დაწყებისას ატვირთავთ style references.",
      "settings.turnaround": "ნაბიჯი 2 — Turnaround (ლოკალური GPU)",
      "settings.turnaroundHint": "Default: Qwen camera rotations (~$0.025/view). Settings prompt is for kontext/lora only.",
      "settings.kontext3d": "3D Pixar (FLUX Kontext)",
      "settings.kontext3dHint": "მხოლოდ PIPELINE_MODE=legacy-3d-ზე.",
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
      "upload.generateTitle": "დატასეტის გენერაცია",
      "upload.generateCount": "რამდენი ობიექტი",
      "upload.generateHint": "კატალოგიდან შემთხვევითი ობიექტები; turnaround იწყება თითოეული რეფერენსის შემდეგ.",
      "upload.styleRefsTitle": "Style references (არასავალდებულო)",
      "upload.styleRefsHint": "1–10 მაგალითი — იგივე სტილი, ყოველ ჯერზე სხვა ობიექტი.",
      "upload.styleRefsDrop": "გადმოიტანეთ სტილის მაგალითები ან აირჩიეთ ფაილები",
      "upload.clearStyleRefs": "style refs-ის გასუფთავება",
      "upload.generateStart": "გენერაციის დაწყება",
      "upload.orUpload": "ან ატვირთეთ მზა რეფერენსები",
      "upload.titleLg": "გადმოიტანეთ სურათები აქ",
      "upload.hintLg": "JPG ან PNG · მაქს. 10 ფაილი",
      "upload.start": "დამუშავების დაწყება",
      "upload.browse": "ფაილების არჩევა",
      "upload.clear": "გასუფთავება",
      "upload.cardTitle": "სურათების ატვირთვა",
      "upload.pageSub": "რეფერენსები და turnaround პარალელურად გენერირდება.",
      "info.outputArchive": "შედეგის არქივი",
      "info.referenceDesc": "კატალოგის რეფერენსი (1:1)",
      "info.turnaroundDesc": "5-ვიუ turnaround (16:9)",
      "info.pipelineSteps": "პაიპლაინის ეტაპები",
      "info.step1": "რეფერენსები (FLUX Dev / Kontext)",
      "info.modelsValue": "dev ან kontext",
      "info.stepReview": "შემოწმება და ჩამოტვირთვა",
      "info.step2": "Turnaround (Kontext Dev + LoRA)",
      "info.step3": "Hive Detect შემოწმება",
      "info.step4": "ZIP და ჩამოტვირთვა",
      "info.maxFiles": "მაქს. ერთ დავალებაზე",
      "info.models": "მოდელები",
      "progress.title": "დავალების დამუშავება",
      "progress.currentStep": "მიმდინარე ეტაპი:",
      "progress.images": "{progress} / {total} სურათი",
      "progress.etaCalculating": "ETA გამოითვლება…",
      "progress.eta": "ETA {mins}წ {secs}წ",
      "progress.reviewReady": "რეფერენსები მზადაა — გადახედეთ და გააგრძელეთ",
      "progress.complete": "დასრულდა",
      "progress.failed": "შეცდომა",
      "progress.processingFailed": "დამუშავება ვერ მოხერხდა.",
      "step.reference": "რეფერენსი",
      "step.review": "შემოწმება",
      "step.turnaround": "Turnaround",
      "step.hive": "Hive Check",
      "step.complete": "დასრულება",
      "status.processing": "მუშავდება",
      "status.awaiting_continue": "შემოწმება",
      "status.completed": "დასრულებული",
      "status.error": "შეცდომა",
      "job.label": "დავალება {id}",
      "job.files": "{count} ფაილი",
      "job.hiveAi": "{score}% AI",
      "hive.vector": "Vector",
      "hive.threed": "3D",
      "hive.turnaround": "Turnaround",
      "hive.pending": "Hive check-ის მოლოდინი…",
      "hive.checkFailed": "შემოწმება ვერ მოხერხდა",
      "hive.qualityReport": "ხარისხის ანგარიში",
      "hive.colFile": "ფაილი",
      "hive.colVector": "Vector",
      "hive.col3d": "3D",
      "hive.colTurnaround": "Turnaround",
      "hive.colAvg": "საშ.",
      "files.counter": "{count} / {max} ფაილი",
      "date.today": "დღეს, {time}",
      "date.yesterday": "გუშინ, {time}",
      "action.downloadArchive": "არქივის ჩამოტვირთვა",
      "action.continueTurnaround": "Turnaround-ის გაგრძელება",
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
      "generate.counter": "{count} სურათი",
      "styleRefs.counter": "{count} / {max} style refs",
      "error.generateFailed": "გენერაცია ვერ მოხერხდა.",
      "error.continueFailed": "turnaround-ის გაშვება ვერ მოხერხდა.",
      "error.maxStyleRefs": "მაქსიმუმ 10 style reference სურათი.",
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

  function generateCounter(count) {
    return t("generate.counter", { count });
  }

  function styleRefCounter(count, max = 10) {
    return t("styleRefs.counter", { count, max });
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
    if (status === "awaiting_continue") return t("status.awaiting_continue");
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
    generateCounter,
    styleRefCounter,
    jobLabel,
    progressImages,
    statusLabel,
    apply,
    setLang,
    get lang() { return lang; },
    STEP_KEYS,
  };
})();
