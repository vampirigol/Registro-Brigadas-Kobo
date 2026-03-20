# Imagen lista para Railway: Flask + Gunicorn + Playwright (Chromium) + Tesseract + poppler
FROM python:3.12-slim-bookworm

WORKDIR /app

# OCR / PDF y utilidades del sistema
RUN apt-get update && apt-get install -y --no-install-recommends \
    tesseract-ocr \
    tesseract-ocr-spa \
    poppler-utils \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Navegador y dependencias nativas de Playwright (necesario en servidor sin GUI)
RUN playwright install --with-deps chromium

COPY . .

RUN mkdir -p uploads logs

ENV PYTHONUNBUFFERED=1
# Railway inyecta PORT; Gunicorn: 1 worker, varios hilos (SSE + peticiones API)
EXPOSE 8080
CMD ["sh", "-c", "exec gunicorn server:app --bind 0.0.0.0:${PORT:-8080} --workers 1 --threads 4 --timeout 300 --graceful-timeout 60"]
