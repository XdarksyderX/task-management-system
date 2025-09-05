FROM python:3.13-slim AS builder
ENV PIP_DISABLE_PIP_VERSION_CHECK=on PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
RUN apt-get update && apt-get install -y --no-install-recommends build-essential \
 && rm -rf /var/lib/apt/lists/*
WORKDIR /app
COPY requirements.txt .
RUN pip wheel --no-cache-dir -w /wheels -r requirements.txt

FROM python:3.13-slim
ENV PIP_DISABLE_PIP_VERSION_CHECK=on PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
RUN groupadd -r app && useradd -r -g app app && mkdir -p /app /reports
WORKDIR /app
COPY --from=builder /wheels /wheels
COPY requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir --no-index --find-links=/wheels -r /app/requirements.txt
COPY entrypoint.sh /app/entrypoint.sh
COPY . /app
RUN chown -R app:app /app /reports && chmod +x /app/entrypoint.sh
USER app
EXPOSE 8000
CMD ["/app/entrypoint.sh","backend"]
