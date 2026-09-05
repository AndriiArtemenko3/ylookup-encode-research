"""Optional OpenTelemetry instrumentation plus always-on local events.

- If OTEL_EXPORTER_OTLP_ENDPOINT is set, spans export via OTLP under service
  name `ylookup-spreadsheet-agent`. Otherwise everything is a no-op and the
  pipeline runs with zero telemetry errors and zero network calls.
- `events(path)` gives an always-on local JSONL event writer so the research
  record never depends on a collector.

PRIVACY / FAIRNESS RULES (hard):
- Never attach API keys, secrets, or environment variables.
- Never attach golden cell values, golden workbook contents, or expected answers.
- Never attach hidden/private dataset contents or whole workbook serialisations.
- Task ids and aggregate metadata are sufficient. The submission's
  traces/<id>.jsonl remain the canonical model/tool traces; OTel is internal
  research observability only.

`span_attributes()` drops any attribute whose key looks like a secret or a
golden value as a safety net; do not rely on it — just never pass them.

Usage:

    from telemetry import tracer, span, events

    with span("task.run", {"experiment.id": "E001", "task.id": task_id,
                           "task.instruction_type": itype, "model.id": model}):
        ...
"""

import datetime
import json
import os
from contextlib import contextmanager
from pathlib import Path

SERVICE_NAME = "ylookup-spreadsheet-agent"
_FORBIDDEN_KEY_PARTS = ("golden", "expected", "secret", "api_key", "apikey", "password", "authorization", "credential")  # guard-ok: denylist keeps these OUT of telemetry


def _forbidden_key(key: str) -> bool:
    lowered = key.lower()
    # "token" alone would swallow input_tokens/output_tokens, which we want
    return (any(part in lowered for part in _FORBIDDEN_KEY_PARTS)
            or lowered == "token" or lowered.endswith("_token"))

_tracer = None


def otlp_enabled() -> bool:
    return bool(os.environ.get("OTEL_EXPORTER_OTLP_ENDPOINT"))


def tracer():
    """Real OTLP tracer when configured, otherwise a no-op tracer."""
    global _tracer
    if _tracer is not None:
        return _tracer
    try:
        from opentelemetry import trace
        if otlp_enabled():
            from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
            from opentelemetry.sdk.resources import Resource
            from opentelemetry.sdk.trace import TracerProvider
            from opentelemetry.sdk.trace.export import BatchSpanProcessor
            provider = TracerProvider(resource=Resource.create({"service.name": SERVICE_NAME}))
            provider.add_span_processor(BatchSpanProcessor(OTLPSpanExporter()))
            trace.set_tracer_provider(provider)
        # Without an endpoint the default provider is a no-op ProxyTracer: safe.
        _tracer = trace.get_tracer(SERVICE_NAME)
    except Exception:  # opentelemetry missing or misconfigured: degrade to no-op
        class _NoopSpan:
            def set_attribute(self, *a, **k): pass
            def record_exception(self, *a, **k): pass
            def set_status(self, *a, **k): pass
            def __enter__(self): return self
            def __exit__(self, *a): return False

        class _NoopTracer:
            @contextmanager
            def start_as_current_span(self, name, **kwargs):
                yield _NoopSpan()

        _tracer = _NoopTracer()
    return _tracer


def span_attributes(attrs: dict | None) -> dict:
    """Drop keys that must never reach telemetry, and non-scalar values."""
    clean = {}
    for key, value in (attrs or {}).items():
        if _forbidden_key(key):
            continue
        if isinstance(value, (str, bool, int, float)):
            if isinstance(value, str) and len(value) > 2000:
                value = value[:2000]
            clean[key] = value
    return clean


@contextmanager
def span(name: str, attrs: dict | None = None):
    """Suggested names: experiment.run, task.run, workbook.inspect, model.call,
    tool.call, code.execute, workbook.write, validation, retry, evaluation.run.
    Suggested attrs: experiment.id, task.id, task.instruction_type, model.id,
    checkpoint.id, harness.version, attempt.number, tool.name, latency_ms,
    input_tokens, output_tokens, status, error.type."""
    with tracer().start_as_current_span(name) as s:
        for key, value in span_attributes(attrs).items():
            s.set_attribute(key, value)
        try:
            yield s
        except Exception as e:
            try:
                s.set_attribute("error.type", type(e).__name__)
                s.record_exception(e)
            except Exception:
                pass
            raise


class events:
    """Always-on local JSONL event log, one JSON object per line."""

    def __init__(self, path: Path | str):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def emit(self, event: str, **fields) -> None:
        record = {"ts": datetime.datetime.now(datetime.timezone.utc).isoformat(),
                  "event": event, **span_attributes(fields)}
        with self.path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(record, ensure_ascii=False) + "\n")
