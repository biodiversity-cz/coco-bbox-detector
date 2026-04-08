# Musí odpovídat wheelům pro torch/ultralytics (viz poetry.lock). 3.14 zatím často bez cp314 torch.
FROM python:3.13-slim-bookworm

RUN pip install --no-cache-dir poetry
RUN useradd --uid 1000  --shell /bin/bash appuser

RUN apt-get update && apt-get install -y --no-install-recommends \
    libgl1 \
    curl \
 && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY pyproject.toml poetry.lock* /app/
RUN poetry config virtualenvs.create false \
 && poetry install --no-interaction --no-ansi --no-root

ARG WEIGHTS_URL=""
# Plain .pt or .pt.gz (e.g. HeSPI sheet-component from GitHub releases)
RUN if [ -n "$WEIGHTS_URL" ]; then \
      mkdir -p /app/weights; \
      case "$WEIGHTS_URL" in \
        *.gz) \
          curl -fSL "$WEIGHTS_URL" -o /app/weights/model.pt.gz \
          && gzip -df /app/weights/model.pt.gz ;; \
        *) \
          curl -fSL "$WEIGHTS_URL" -o /app/weights/model.pt ;; \
      esac; \
    fi

COPY src ./src
RUN chown -R appuser:appuser /app

EXPOSE 5000

USER appuser
ENTRYPOINT ["python", "src/main.py"]
