import logging
import os
import sys

import structlog
from opentelemetry import trace
from structlog.contextvars import bind_contextvars, clear_contextvars

# Try orjson; fall back to stdlib json
try:
    import orjson as _jsonlib

    def _json_dumps(d):
        return _jsonlib.dumps(d).decode()
except Exception:
    import json as _jsonlib

    def _json_dumps(d):
        return _jsonlib.dumps(d, default=str)


def _add_trace_ids(_, __, event):
    span = trace.get_current_span()
    ctx = span.get_span_context()
    if ctx and ctx.is_valid:
        event["trace_id"] = f"{ctx.trace_id:032x}"
        event["span_id"] = f"{ctx.span_id:016x}"
    return event


def _json_renderer(_, __, event):
    return _json_dumps(event)


def configure_logging():
    level = os.getenv("LOG_LEVEL", "INFO").upper()
    logging.basicConfig(
        level=level, handlers=[logging.StreamHandler(sys.stdout)], format="%(message)s"
    )
    for name in ("uvicorn", "uvicorn.error", "uvicorn.access"):
        logging.getLogger(name).handlers = []
        logging.getLogger(name).propagate = True
        logging.getLogger(name).setLevel(level)

    structlog.configure(
        processors=[
            structlog.processors.TimeStamper(fmt="iso", utc=True),
            structlog.processors.add_log_level,
            _add_trace_ids,
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            _json_renderer,
        ],
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.make_filtering_bound_logger(getattr(logging, level, logging.INFO)),
        cache_logger_on_first_use=True,
    )


get_logger = structlog.get_logger
bind_ctx = bind_contextvars
clear_ctx = clear_contextvars
