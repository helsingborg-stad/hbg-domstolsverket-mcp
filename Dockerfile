FROM python:3.11-slim

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    UV_COMPILE_BYTECODE=1

RUN useradd --uid 10001 --no-create-home appuser

COPY pyproject.toml uv.lock /app/

RUN pip install --no-cache-dir uv \
    && uv sync --frozen --no-dev

COPY main.py README.md /app/

ENV VIRTUAL_ENV="/app/.venv" \
    PATH="/app/.venv/bin:$PATH" \
    HOME=/tmp

USER 10001

EXPOSE 8000

CMD ["python", "main.py"]
