"""
tests for Tracer and utilities.
"""

import time
import random

from nose.tools import eq_

from ddtrace.tracer import Tracer


def test_tracer_vars():
    tracer = Tracer(writer=None)

    # explicit vars
    s = tracer.trace("a", service="s", resource="r", span_type="t")
    eq_(s.service, "s")
    eq_(s.resource, "r")
    eq_(s.span_type, "t")
    s.finish()

    # defaults
    s = tracer.trace("a")
    eq_(s.service, None)
    eq_(s.resource, "a") # inherits
    eq_(s.span_type, None)

def test_tracer():
    # add some dummy tracing code.
    writer = DummyWriter()
    tracer = Tracer(writer=writer)
    sleep = 0.05

    def _mix():
        with tracer.trace("cake.mix"):
            time.sleep(sleep)

    def _bake():
        with tracer.trace("cake.bake"):
            time.sleep(sleep)

    def _make_cake():
        with tracer.trace("cake.make") as span:
            span.service = "baker"
            span.resource = "cake"
            _mix()
            _bake()

    # let's run it and make sure all is well.
    assert not writer.spans
    _make_cake()
    spans = writer.pop()
    assert spans, "%s" % spans
    eq_(len(spans), 3)
    spans_by_name = {s.name:s for s in spans}
    eq_(len(spans_by_name), 3)

    make = spans_by_name["cake.make"]
    assert make.span_id
    assert make.parent_id is None
    assert make.trace_id

    for other in ["cake.mix", "cake.bake"]:
        s = spans_by_name[other]
        eq_(s.parent_id, make.span_id)
        eq_(s.trace_id, make.trace_id)
        eq_(s.service, make.service) # ensure it inherits the service
        eq_(s.resource, s.name)      # ensure when we don't set a resource, it's there.


    # do it again and make sure it has new trace ids
    _make_cake()
    spans = writer.pop()
    for s in spans:
        assert s.trace_id != make.trace_id

def test_tracer_disabled():
    # add some dummy tracing code.
    writer = DummyWriter()
    tracer = Tracer(writer=writer)

    tracer.enabled = True
    with tracer.trace("foo") as s:
        s.set_tag("a", "b")
    assert writer.pop()

    tracer.enabled = False
    with tracer.trace("foo") as s:
        s.set_tag("a", "b")
    assert not writer.pop()

def test_tracer_disabled_mem_leak():
    # ensure that if the tracer is disabled, we still remove things from the
    # span buffer upon finishing.
    writer = DummyWriter()
    tracer = Tracer(writer=writer)
    tracer.enabled = False
    s1 = tracer.trace("foo")
    s1.finish()
    p1 = tracer.current_span()
    s2 = tracer.trace("bar")
    assert not s2._parent, s2._parent
    s2.finish()
    assert not p1, p1

def test_sampling():
    writer = DummyWriter()
    tracer = Tracer(writer=writer, sample_rate=0.5)

    # Set the seed so that the choice of sampled traces is deterministic, then write tests accordingly
    random.seed(4012)

    # First trace, sampled
    with tracer.trace("foo") as s:
        assert s.sampled
        assert s.weight == 2
    assert writer.pop()

    # Second trace, not sampled
    with tracer.trace("figh") as s:
        assert not s.sampled
        s2 = tracer.trace("what")
        assert not s2.sampled
        s2.finish()
        with tracer.trace("ever") as s3:
            assert not s3.sampled
            s4 = tracer.trace("!")
            assert not s4.sampled
            s4.finish()
    spans = writer.pop()
    assert not spans, spans

    # Third trace, not sampled
    with tracer.trace("ters") as s:
        assert s.sampled
    assert writer.pop()


class DummyWriter(object):
    """ DummyWriter is a small fake writer used for tests. not thread-safe. """

    def __init__(self):
        self.spans = []
        self.services = {}

    def write(self, spans, services=None):
        self.spans += spans
        if services:
            self.services.update(services)

    # dummy methods

    def pop(self):
        s = self.spans
        self.spans = []
        return s

    def pop_services(self):
        s = self.services
        self.services = {}
        return s
