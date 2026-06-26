FROM python:3.12-slim AS builder

WORKDIR /workspace

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir --prefix=/install -r requirements.txt

FROM python:3.12-slim AS runner

WORKDIR /app

COPY --from=builder /install /usr/local

RUN groupadd -g 1000 appgroup && \
    useradd -r -u 1000 -g appgroup -m -s /sbin/nologin appuser

COPY app/ /app/app/
RUN chown -R appuser:appgroup /app

USER appuser

EXPOSE 8080

ENV PORT=8080
ENV PYTHONUNBUFFERED=1

CMD ["sh", "-c", "exec uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8080}"]