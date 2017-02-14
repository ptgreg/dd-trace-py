import os

from .middleware import PylonsTraceMiddleware
from ddtrace import tracer

import pylons.wsgiapp

def patch():
    """Patch the instrumented Flask object
    """
    if getattr(pylons.wsgiapp, '_datadog_patch', False):
        return

    setattr(pylons.wsgiapp, '_datadog_patch', True)
    setattr(pylons.wsgiapp, 'PylonsApp', TracedPylonsApp)


class TracedPylonsApp(pylons.wsgiapp.PylonsApp):

    def __init__(self, *args, **kwargs):
        super(TracedPylonsApp, self).__init__(*args, **kwargs)
        service = os.environ.get("DATADOG_SERVICE_NAME") or "pylons"

        PylonsTraceMiddleware(self, tracer, service=service)
