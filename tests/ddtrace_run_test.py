#!/usr/bin/env python
from ddtrace import tracer
import os

if __name__ == '__main__':
    if 'DATADOG_SERVICE_ENV' in os.environ:
        assert tracer.tags["env"] == os.environ['DATADOG_SERVICE_ENV']
