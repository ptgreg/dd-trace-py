"""
tests for Tracer and utilities.
"""

import time

from nose.tools import assert_raises, eq_
from unittest.case import SkipTest

from .utils import get_test_tracer


def test_tracer_vars():
    tracer = get_test_tracer()

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
    tracer = get_test_tracer()
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
    assert not tracer.writer.spans
    _make_cake()
    spans = tracer.writer.pop()
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
    spans = tracer.writer.pop()
    for s in spans:
        assert s.trace_id != make.trace_id

def test_tracer_wrap():
    tracer = get_test_tracer()

    @tracer.wrap('decorated_function', service='s', resource='r',
            span_type='t')
    def f(tag_name, tag_value):
        # make sure we can still set tags
        span = tracer.current_span()
        span.set_tag(tag_name, tag_value)
    f('a', 'b')

    spans = tracer.writer.pop()
    eq_(len(spans), 1)
    s = spans[0]
    eq_(s.name, 'decorated_function')
    eq_(s.service, 's')
    eq_(s.resource, 'r')
    eq_(s.span_type, 't')
    eq_(s.to_dict()['meta']['a'], 'b')

def test_tracer_wrap_default_name():
    tracer = get_test_tracer()

    @tracer.wrap()
    def f():
        pass
    f()

    eq_(tracer.writer.spans[0].name, 'tests.test_tracer.f')

def test_tracer_wrap_exception():
    tracer = get_test_tracer()

    @tracer.wrap()
    def f():
        raise Exception('bim')

    assert_raises(Exception, f)

    eq_(len(tracer.writer.spans), 1)
    eq_(tracer.writer.spans[0].error, 1)

def test_tracer_wrap_multiple_calls():
    # Make sure that we create a new span each time the function is called
    tracer = get_test_tracer()

    @tracer.wrap()
    def f():
        pass
    f()
    f()

    spans = tracer.writer.pop()
    eq_(len(spans), 2)
    assert spans[0].span_id != spans[1].span_id

def test_tracer_wrap_span_nesting():
    # Make sure that nested spans have the correct parents
    tracer = get_test_tracer()

    @tracer.wrap('inner')
    def inner():
        pass
    @tracer.wrap('outer')
    def outer():
        with tracer.trace('mid'):
            inner()
    outer()

    spans = tracer.writer.pop()
    eq_(len(spans), 3)

    # sift through the list so we're not dependent on span ordering within the
    # writer
    for span in spans:
        if span.name == 'outer':
            outer_span = span
        elif span.name == 'mid':
            mid_span = span
        elif span.name == 'inner':
            inner_span = span
        else:
            assert False, 'unknown span found'  # should never get here

    assert outer_span
    assert mid_span
    assert inner_span

    eq_(outer_span.parent_id, None)
    eq_(mid_span.parent_id, outer_span.span_id)
    eq_(inner_span.parent_id, mid_span.span_id)

def test_tracer_wrap_class():
    tracer = get_test_tracer()

    class Foo(object):

        @staticmethod
        @tracer.wrap()
        def s():
            return 1

        @classmethod
        @tracer.wrap()
        def c(cls):
            return 2

        @tracer.wrap()
        def i(cls):
            return 3

    f = Foo()
    eq_(f.s(), 1)
    eq_(f.c(), 2)
    eq_(f.i(), 3)

    spans = tracer.writer.pop()
    eq_(len(spans), 3)
    names = [s.name for s in spans]
    # FIXME[matt] include the class name here.
    eq_(sorted(names), sorted(["tests.test_tracer.%s" % n for n in ["s", "c", "i"]]))

def test_tracer_disabled():
    # add some dummy tracing code.
    tracer = get_test_tracer()

    tracer.enabled = True
    with tracer.trace("foo") as s:
        s.set_tag("a", "b")
    assert tracer.writer.pop()

    tracer.enabled = False
    with tracer.trace("foo") as s:
        s.set_tag("a", "b")
    assert not tracer.writer.pop()

def test_unserializable_span_with_finish():
    try:
        import numpy as np
    except ImportError:
        raise SkipTest("numpy not installed")

    # a weird case where manually calling finish with an unserializable
    # span was causing an loop of serialization.
    tracer = get_test_tracer()

    with tracer.trace("parent") as span:
        span.metrics['as'] = np.int64(1) # circumvent the data checks
        span.finish()

def test_tracer_disabled_mem_leak():
    # ensure that if the tracer is disabled, we still remove things from the
    # span buffer upon finishing.
    tracer = get_test_tracer()

    tracer.enabled = False
    s1 = tracer.trace("foo")
    s1.finish()
    p1 = tracer.current_span()
    s2 = tracer.trace("bar")
    assert not s2._parent, s2._parent
    s2.finish()
    assert not p1, p1
