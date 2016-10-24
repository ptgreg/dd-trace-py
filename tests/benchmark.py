import time
import timeit

from ddtrace import Tracer

from .utils import get_test_tracer


REPEAT = 10
NUMBER = 10000


def trace_error(tracer):
    # explicit vars
    with tracer.trace("a", service="s", resource="r", span_type="t"):
        1 / 0


def benchmark_tracer_trace():
    tracer = get_test_tracer()

    # testcase
    def trace(tracer):
        # explicit vars
        with tracer.trace("a", service="s", resource="r", span_type="t") as s:
            s.set_tag("a", "b")
            s.set_tag("b", 1)
            with tracer.trace("another.thing"):
                pass
            with tracer.trace("another.thing"):
                pass

    # benchmark
    print("## tracer.trace() benchmark: {} loops ##".format(NUMBER))
    timer = timeit.Timer(lambda: trace(tracer))
    result = timer.repeat(repeat=REPEAT, number=NUMBER)
    print("- trace execution time: {:8.6f}".format(min(result)))


def benchmark_tracer_wrap():
    tracer = get_test_tracer()

    # testcase
    class Foo(object):
        @staticmethod
        @tracer.wrap()
        def s():
            return 0

        @classmethod
        @tracer.wrap()
        def c(cls):
            return 0

        @tracer.wrap()
        def m(self):
            return 0

    f = Foo()

    # benchmark
    print("## tracer.trace() wrapper benchmark: {} loops ##".format(NUMBER))
    timer = timeit.Timer(f.s)
    result = timer.repeat(repeat=REPEAT, number=NUMBER)
    print("- staticmethod execution time: {:8.6f}".format(min(result)))
    timer = timeit.Timer(f.c)
    result = timer.repeat(repeat=REPEAT, number=NUMBER)
    print("- classmethod execution time: {:8.6f}".format(min(result)))
    timer = timeit.Timer(f.m)
    result = timer.repeat(repeat=REPEAT, number=NUMBER)
    print("- method execution time: {:8.6f}".format(min(result)))


if __name__ == '__main__':
    benchmark_tracer_wrap()
    benchmark_tracer_trace()
