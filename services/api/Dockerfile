# services/api/Dockerfile (build context = repo root)
FROM python:3.12-slim
ENV PYTHONUNBUFFERED=1 UV_COMPILE_BYTECODE=1
RUN pip install --no-cache-dir uv
WORKDIR /srv/services/api
COPY services/api/pyproject.toml services/api/uv.lock ./
RUN uv sync --frozen --no-dev
COPY services/api/ ./
COPY data/demo_runs/ /srv/data/demo_runs/
COPY data/fixtures/ /srv/data/fixtures/
EXPOSE 8000
# --frozen --no-dev: a bare `uv run` would re-sync the dev group at container start (see DECISIONS D-035)
CMD ["uv", "run", "--frozen", "--no-dev", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", \
     "--workers", "1", "--timeout-keep-alive", "75", "--proxy-headers"]
