import os

from ...ext import AppTypes
from .middleware import TraceMiddleware
from ddtrace import tracer

from wrapt import ObjectProxy
import flask


def patch():
    """Patch the instrumented Flask object
    """
    if getattr(flask, '_datadog_patch', False):
        return

    setattr(flask, '_datadog_patch', True)
    setattr(flask, 'Flask', TracedFlask)


class TracedFlask(flask.Flask):

    def __init__(self, *args, **kwargs):
        super(TracedFlask, self).__init__(*args, **kwargs)
        service = os.environ.get("DATADOG_SERVICE_NAME") or "flask"

        TraceMiddleware(self, tracer, service=service)
