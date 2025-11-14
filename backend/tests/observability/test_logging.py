import builtins
import importlib

import pytest
from opentelemetry import trace


@pytest.mark.asyncio
async def test_fallback_json_when_orjson_missing(monkeypatch):
    import app.observability.logging as logging_mod

    original_import = builtins.__import__

    def fake_import(name, *args, **kwargs):
        if name == "orjson":
            raise ImportError("orjson not available")
        return original_import(name, *args, **kwargs)

    # Force reload with ImportError for orjson
    monkeypatch.setattr(builtins, "__import__", fake_import)
    reloaded = importlib.reload(logging_mod)
    try:
        # _json_dumps should use stdlib json with default=str and not crash
        result = reloaded._json_dumps({"x": object()})
        assert isinstance(result, str)
        assert '"x"' in result and result.startswith("{")
    finally:
        # Restore normal import path and reload module back to normal
        monkeypatch.setattr(builtins, "__import__", original_import)
        importlib.reload(logging_mod)


@pytest.mark.asyncio
async def test_add_trace_ids_injects_when_span_valid(monkeypatch):
    import app.observability.logging as logging_mod

    event = {}

    # Provide a fake current span with a valid context regardless of SDK state
    class _Ctx:
        is_valid = True
        trace_id = 0x1234
        span_id = 0x5678

    class _Span:
        def get_span_context(self):
            return _Ctx()

    monkeypatch.setattr(trace, "get_current_span", lambda: _Span(), raising=True)
    out = logging_mod._add_trace_ids(None, None, event)
    assert "trace_id" in out and "span_id" in out
    # hex lengths: 32 for trace_id, 16 for span_id
    assert len(out["trace_id"]) == 32
    assert len(out["span_id"]) == 16
