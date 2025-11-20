FROM python:3.13.4-slim-bookworm AS builder
WORKDIR /app
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential gcc \
    && rm -rf /var/lib/apt/lists/*
COPY requirements.txt .
RUN pip install --upgrade pip && pip install --prefix=/install -r requirements.txt

FROM python:3.13.4-slim-bookworm AS runtime
WORKDIR /app
COPY --from=builder /install /usr/local
COPY . .
CMD ["python", "main.py", "-env", "prod"]