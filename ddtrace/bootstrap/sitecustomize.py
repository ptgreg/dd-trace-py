"""
Bootstrapping code that is run when using the `ddtrace-run` Python entrypoint
Add all monkey-patching that needs to run by default here
"""

from ddtrace import patch_all; patch_all(django=True, flask=True, pylons=True) # noqa
import os

from ddtrace import tracer
if 'DATADOG_SERVICE_ENV' in os.environ:
    tracer.set_tags({"env": os.environ["DATADOG_SERVICE_ENV"]})

if 'DATADOG_SERVICE_NAME' in os.environ:
    tracer.set_tags({"_global_service": os.environ["DATADOG_SERVICE_NAME"]})
