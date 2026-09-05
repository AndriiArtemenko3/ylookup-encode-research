# Ylookup research-track submission container: h6 cascade harness.
#
# Contract (research/SUBMISSION.md): judges mount a dataset dir read-only at
# /data (dataset.json + spreadsheet/<id>/ with init workbook and prompt.txt,
# same layout as the public set) and an empty dir at /out. The container runs
# unattended and writes predictions.jsonl, outputs/, traces/, run.log to /out.
#
#   docker build -t superspreadsheets .
#   docker run --rm -e TINKER_API_KEY -e TINKER_PROJECT_ID \
#       -v <dataset dir>:/data:ro -v <empty dir>:/out superspreadsheets
#
# Model id is fixed below; temperature is 0 in code. LibreOffice is required
# by the harness itself (golden-free health checks recalculate our own
# outputs before accepting them) — not only by the evaluator.

FROM python:3.11-slim-bookworm

RUN apt-get update \
    && apt-get install -y --no-install-recommends libreoffice-calc \
    && rm -rf /var/lib/apt/lists/*

COPY --from=ghcr.io/astral-sh/uv:0.11.31 /uv /usr/local/bin/uv

WORKDIR /app/research
COPY research/pyproject.toml research/uv.lock ./
RUN uv sync --frozen --extra tinker --no-dev

COPY research/sb.py research/evaluate.py research/telemetry.py ./
COPY research/baseline ./baseline
COPY research/inference ./inference
COPY research/splits ./splits

ENV PYTHONUNBUFFERED=1
# Overridable without rebuilding; model is part of the frozen configuration.
ENV MODEL_ID=Qwen/Qwen3.8-27B
ENV CONCURRENCY=8
ENV MAX_TOKENS=24576

CMD ["/bin/sh", "-c", "uv run inference/cascade_predict.py \
    --dataset-dir /data --out-dir /out \
    --base-model \"$MODEL_ID\" --concurrency \"$CONCURRENCY\" --max-tokens \"$MAX_TOKENS\""]
