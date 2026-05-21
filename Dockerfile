FROM python:3.12-slim AS build

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app

COPY pyproject.toml README.md ./
COPY src ./src

RUN pip install --upgrade pip && \
    pip install --prefix=/install .

FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    O2_JUDGE_HOST=0.0.0.0 \
    O2_JUDGE_PORT=8000

WORKDIR /app

COPY --from=build /install /usr/local
COPY --from=build /app/src ./src

RUN useradd --create-home --uid 10001 judge
USER judge

EXPOSE 8000

CMD ["python", "-m", "judge_server"]
