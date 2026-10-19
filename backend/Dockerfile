# ---------- Build stage: install deps into an isolated user site-packages ----------
FROM python:3.11-slim AS builder
WORKDIR /build
COPY requirements.txt .
RUN pip install --no-cache-dir --user -r requirements.txt

# ---------- Runtime stage ----------
FROM python:3.11-slim
RUN groupadd -r appuser && useradd -r -g appuser appuser

WORKDIR /app
COPY --from=builder /root/.local /home/appuser/.local
COPY app ./app

ENV PATH=/home/appuser/.local/bin:$PATH \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

RUN chown -R appuser:appuser /app /home/appuser/.local
USER appuser

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=15s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health')" || exit 1

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
