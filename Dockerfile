FROM python:3.13.4-slim AS builder
WORKDIR /app

RUN pip install uv && \
    rm -rf /root/.cache/pip

COPY pyproject.toml pyproject.toml
COPY uv.lock uv.lock

ENV VIRTUAL_ENV=/venv
RUN python -m venv $VIRTUAL_ENV
ENV PATH="$VIRTUAL_ENV/bin:$PATH"

RUN uv pip install .


FROM python:3.13.4-slim AS runtime
WORKDIR /app

ENV VIRTUAL_ENV=/venv
ENV PATH="$VIRTUAL_ENV/bin:$PATH"

COPY --from=builder /venv /venv

COPY main.py .
COPY jobs_main.py .
COPY src/ src/

RUN playwright install --with-deps

CMD ["python", "main.py"]
