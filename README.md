# 🎨 Image Transform Pipeline — MVP

Веб-додаток: завантажуєш мультяшні JPG/PNG → отримуєш 2 ZIP архіви.
- **Архів 1** — векторний стиль (Image Trace + градієнт фон)
- **Архів 2** — 3D Pixar стиль

---

## Швидкий старт (Windows — vtracer потребує Python 3.12)

```powershell
# 1. Запуск (створить .venv з Python 3.12 і встановить залежності)
.\run.ps1

# 2. Конфіг (один раз)
copy .env.example .env
# відкрий .env і встав API ключі

# → http://127.0.0.1:5000
```

> **Не використовуйте `py app.py` на Python 3.14** — vtracer падає (native crash).
> Завжди запускайте через `.\run.ps1` або `.venv\Scripts\python.exe app.py`.

Linux/macOS:

```bash
python3.12 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
python app.py
```

---

## Структура проекту

```
image_transform/
│
├── app.py                  # Entry point, Flask factory
├── config.py               # Всі налаштування з .env
├── requirements.txt
│
├── backend/
│   ├── api/
│   │   └── routes.py       # 🔵 БЕК — /upload, /status, /download
│   ├── core/
│   │   ├── pipeline.py     # 🔵 БЕК — оркестратор кроків обробки
│   │   └── job_manager.py  # 🔵 БЕК — стан jobs (in-memory → Redis у фіналі)
│   ├── services/
│   │   ├── ai_service.py       # 🔵 БЕК — Replicate API (img2img unique + 3D)
│   │   ├── image_service.py    # 🟢 ФРОНТ — vtracer + Pillow фільтри
│   │   └── hivedetect_service.py # 🔵 БЕК — Hivedetect API
│   └── utils/
│       └── validators.py   # 🔵 БЕК — валідація файлів
│
├── frontend/
│   ├── templates/
│   │   └── index.html      # 🟢 ФРОНТ — UI розмітка
│   └── static/
│       ├── css/style.css   # 🟢 ФРОНТ — стилі
│       └── js/app.js       # 🟢 ФРОНТ — upload, polling, UI стани
│
└── tests/                  # тести (додавати по ходу)
```

---

## Хто що робить

| Файл | Розробник |
|------|-----------|
| `backend/api/routes.py` | 🔵 БЕК |
| `backend/core/pipeline.py` | 🔵 БЕК |
| `backend/core/job_manager.py` | 🔵 БЕК |
| `backend/services/ai_service.py` | 🔵 БЕК |
| `backend/services/hivedetect_service.py` | 🔵 БЕК |
| `backend/services/image_service.py` | 🟢 ФРОНТ |
| `frontend/` | 🟢 ФРОНТ |

---

## API

| Метод | URL | Опис |
|-------|-----|------|
| `POST` | `/api/upload` | Завантажити файли, отримати `job_id` |
| `GET` | `/api/status/<job_id>` | Статус + прогрес + Hivedetect % |
| `GET` | `/api/download/<job_id>/vector` | Скачати Архів 1 |
| `GET` | `/api/download/<job_id>/3d` | Скачати Архів 2 |

---

## TODO для Розробника 2 (image_service.py)

```python
# 1. pip install vtracer cairosvg
# 2. Реалізувати vectorize_with_gradient():
#    - vtracer.convert(input_path, svg_path, colormode='color', nr_colors=6)
#    - cairosvg.svg2png(url=svg_path, write_to=png_path)
#    - накласти радіальний градієнт фон
```
