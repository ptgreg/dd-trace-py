import mock

from ddtrace.tracer import Tracer
from ddtrace.writer import AgentWriter
from ddtrace.transport import HTTPTransport


class FakeTime(object):
    """"Allow to mock time.time for tests

    `time.time` returns a defined `current_time` instead.
    Any `time.time` call also increase the `current_time` of `delta` seconds.
    """

    def __init__(self):
        # Sane defaults
        self._current_time = 1e9
        self._delta = 0.001

    def __call__(self):
        self._current_time = self._current_time + self._delta
        return self._current_time

    def set_epoch(self, epoch):
        self._current_time = epoch

    def set_delta(self, delta):
        self._delta = delta

    def sleep(self, second):
        self._current_time += second


def patch_time():
    """Patch time.time with FakeTime"""
    return mock.patch('time.time', new_callable=FakeTime)


class DummyWriter(AgentWriter):
    """ DummyWriter is a small fake writer used for tests. not thread-safe. """

    def __init__(self):
        super(DummyWriter, self).__init__()
        # dummy components
        self._transport = DummyTransport('localhost', '7777')
        # easy access to registered components
        self.spans = []
        self.services = {}

    def write_trace(self, trace):
        super(DummyWriter, self).write_trace(trace)
        self.spans += trace

    def write_services(self, services):
        super(DummyWriter, self).write_services(services)
        self.services = services

    def pop(self):
        # dummy method
        s = self.spans
        self.spans = []
        return s

    def pop_services(self):
        # dummy method
        s = self.services
        self.services = {}
        return s


class DummyTransport(HTTPTransport):
    """
    Fake HTTPTransport so that the send() method doesn't make any calls.
    """
    def send(self, *args, **kwargs):
        pass


def get_test_tracer():
    """
    Create a new test Tracer() that you can use to retrieve easily
    application spans. This tracer uses a DummyWriter() and will
    not make any real calls. Despite that, mocked components behave
    exactly as the original implementations (i.e. encoding is done
    properly), so if there is an error you will notice this.

    This test tracer should not be used for integration tests.
    """
    # create a new tracer and stop background executions
    tracer = Tracer()
    tracer.writer.stop()
    # replace the writer with a DummyWriter
    tracer.writer = DummyWriter()
    return tracer
