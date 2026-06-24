FROM python:3.13-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    libffi-dev \
    && rm -rf /var/lib/apt/lists/*

ENV PIP_DEFAULT_TIMEOUT=120 \
    PIP_RETRIES=10

COPY requirements.txt .
RUN pip install --no-cache-dir --timeout 120 --retries 10 -r requirements.txt

COPY . .

RUN mkdir -p tmp/uploads tmp/outputs

ENV PORT=8080
EXPOSE 8080

CMD ["gunicorn", "--bind", "0.0.0.0:8080", "--workers", "1", "--threads", "8", "--timeout", "300", "app:app"]
