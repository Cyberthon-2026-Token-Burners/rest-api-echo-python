FROM python:3.12-slim AS builder

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .

RUN pip install --no-cache-dir --target=/app/dependencies -r requirements.txt

FROM python:3.12-slim AS runner

WORKDIR /app

COPY --from=builder /app/dependencies /app/dependencies
ENV PYTHONPATH=/app/dependencies:$PYTHONPATH

COPY app/ app/

EXPOSE 8080
ENV PORT=8080

RUN groupadd -r appgroup && useradd -r -g appgroup -u 1000 appuser
RUN chown -R appuser:appgroup /app
USER appuser

CMD ["sh", "-c", "python -m uvicorn app.main:app --host 0.0.0.0 --port ${PORT}"]