FROM python:3.12-slim AS builder
WORKDIR /app
ARG PIP_INDEX_URL=https://packagefeedproxy.microsoft.io/pypi/simple/
ENV PIP_INDEX_URL=${PIP_INDEX_URL} UV_INDEX_URL=${PIP_INDEX_URL}
RUN pip install --no-cache-dir uv
COPY pyproject.toml ./
RUN uv venv /opt/venv && uv pip install --python /opt/venv/bin/python -r pyproject.toml

FROM python:3.12-slim
RUN addgroup --system app && adduser --system --ingroup app app
COPY --from=builder /opt/venv /opt/venv
WORKDIR /app
COPY --chown=app:app app ./app
ENV PATH="/opt/venv/bin:$PATH" PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
USER app
EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--no-access-log"]
