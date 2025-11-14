import types

import pytest

from app.observability import otel as ot


class DummyBatchSpanProcessor:
    def __init__(self, exporter):
        self.exporter = exporter


class DummyConsoleExporter:
    pass


class DummyOTLPExporter:
    def __init__(self, endpoint=None):
        self.endpoint = endpoint


class DummyTracerProvider:
    def __init__(self, resource=None):
        self.resource = resource
        self.processors = []

    def add_span_processor(self, processor):
        self.processors.append(processor)


@pytest.mark.asyncio
async def test_setup_otel_uses_console_exporter_when_no_endpoint(monkeypatch):
    # Ensure endpoint not set; set custom service name
    monkeypatch.delenv("OTEL_EXPORTER_OTLP_ENDPOINT", raising=False)
    monkeypatch.setenv("OTEL_SERVICE_NAME", "test-service")

    # Capture provider set
    captured = {}

    def fake_set_provider(provider):
        captured["provider"] = provider

    # Monkeypatch instrumentation hooks to no-ops while capturing calls
    called = {"fastapi": False, "requests": False, "psycopg": False}
    monkeypatch.setattr(
        ot,
        "FastAPIInstrumentor",
        types.SimpleNamespace(
            instrument_app=lambda _app: called.__setitem__("fastapi", True)
        ),
        raising=True,
    )
    monkeypatch.setattr(
        ot,
        "RequestsInstrumentor",
        lambda: types.SimpleNamespace(
            instrument=lambda: called.__setitem__("requests", True)
        ),
        raising=True,
    )
    monkeypatch.setattr(
        ot,
        "PsycopgInstrumentor",
        lambda: types.SimpleNamespace(
            instrument=lambda: called.__setitem__("psycopg", True)
        ),
        raising=True,
    )

    # Replace exporter/processor/provider
    monkeypatch.setattr(ot, "ConsoleSpanExporter", DummyConsoleExporter, raising=True)
    monkeypatch.setattr(ot, "OTLPSpanExporter", DummyOTLPExporter, raising=True)
    monkeypatch.setattr(ot, "BatchSpanProcessor", DummyBatchSpanProcessor, raising=True)
    monkeypatch.setattr(ot, "TracerProvider", DummyTracerProvider, raising=True)
    monkeypatch.setattr(
        ot.trace, "set_tracer_provider", fake_set_provider, raising=True
    )

    # Run
    app = object()
    ot.setup_otel(app)

    provider = captured["provider"]
    # Validate BatchSpanProcessor and exporter type
    assert isinstance(provider, DummyTracerProvider)
    assert len(provider.processors) == 1
    batch = provider.processors[0]
    assert isinstance(batch, DummyBatchSpanProcessor)
    assert isinstance(batch.exporter, DummyConsoleExporter)
    # Instrumentation invoked
    assert all(called.values())
    # Resource contains service.name set (cannot introspect Resource easily here)
    assert provider.resource is not None


@pytest.mark.asyncio
async def test_setup_otel_uses_otlp_exporter_when_endpoint(monkeypatch):
    monkeypatch.setenv("OTEL_EXPORTER_OTLP_ENDPOINT", "http://collector:4318/v1/traces")
    monkeypatch.setenv("OTEL_SERVICE_NAME", "test-service-otlp")

    captured = {}

    def fake_set_provider(provider):
        captured["provider"] = provider

    called = {"fastapi": False, "requests": False, "psycopg": False}
    monkeypatch.setattr(
        ot,
        "FastAPIInstrumentor",
        types.SimpleNamespace(
            instrument_app=lambda _app: called.__setitem__("fastapi", True)
        ),
        raising=True,
    )
    monkeypatch.setattr(
        ot,
        "RequestsInstrumentor",
        lambda: types.SimpleNamespace(
            instrument=lambda: called.__setitem__("requests", True)
        ),
        raising=True,
    )
    monkeypatch.setattr(
        ot,
        "PsycopgInstrumentor",
        lambda: types.SimpleNamespace(
            instrument=lambda: called.__setitem__("psycopg", True)
        ),
        raising=True,
    )

    monkeypatch.setattr(ot, "ConsoleSpanExporter", DummyConsoleExporter, raising=True)
    monkeypatch.setattr(ot, "OTLPSpanExporter", DummyOTLPExporter, raising=True)
    monkeypatch.setattr(ot, "BatchSpanProcessor", DummyBatchSpanProcessor, raising=True)
    monkeypatch.setattr(ot, "TracerProvider", DummyTracerProvider, raising=True)
    monkeypatch.setattr(
        ot.trace, "set_tracer_provider", fake_set_provider, raising=True
    )

    app = object()
    ot.setup_otel(app)

    provider = captured["provider"]
    assert isinstance(provider, DummyTracerProvider)
    assert len(provider.processors) == 1
    batch = provider.processors[0]
    assert isinstance(batch.exporter, DummyOTLPExporter)
    assert batch.exporter.endpoint == "http://collector:4318/v1/traces"
    assert all(called.values())
