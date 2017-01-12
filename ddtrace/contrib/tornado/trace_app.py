
import logging

from ddtrace.context import Context

from ... import compat
from ...ext import http, errors, AppTypes


log = logging.getLogger(__name__)


class TraceApp(object):
    """
    TraceApp modifies a Tornado application so that it traces requests.
    """

    def __init__(self, app, tracer, service="tornado"):
        """
        Initialize a new tracing application.
        """
        self.app = app
        self.service = service
        self.tracer = tracer

        tracer.set_service_info(
            service=service,
            app="tornado",
            app_type=AppTypes.web,
        )

        for (_, specs) in app.handlers:
            for spec in specs:
                self.patch_handler_class(spec.handler_class)

        log.info("tracing application (service {0!r})".format(service))

    def patch_handler_class(self, cls):
        """
        Replace various methods of a handler class by wrappers which will
        create and update spans.
        """
        cls.prepare = self.wrap_handler_prepare(cls.prepare)
        cls.on_finish = self.wrap_handler_on_finish(cls.on_finish)
        cls.clear = self.wrap_handler_clear(cls.clear)
        cls.set_status = self.wrap_handler_set_status(cls.set_status)
        cls.render = self.wrap_handler_render(cls.render)
        cls.render_string = self.wrap_handler_render_string(cls.render_string)

    def wrap_handler_prepare(self, fn):
        """
        Create a wrapped prepare() handler method and return it.
        """
        tracer = self.tracer
        service = self.service

        def prepare(self):
            try:
                context = Context()
                self._datadog_request_context = context

                uri = self.request.uri
                endpoint = uri.strip("/").replace("/", "_").lower()
                resource = compat.to_unicode(endpoint)

                span = tracer.trace("tornado.request", service=service,
                                    resource=resource, span_type=http.TYPE,
                                    context=context)
                span.set_tag(http.URL, compat.to_unicode(uri))

                self._datadog_request_span = span
            except Exception:
                log.exception("cannot trace request")

            return fn(self)
        return prepare

    def wrap_handler_on_finish(self, fn):
        """
        Create a wrapped on_finish() handler method and return it.
        """
        def on_finish(self):
            # In tornado, render() calls finish() which calls on_finish().
            # Therefore if there is an active render span, we finish it right
            # here.
            span = getattr(self, "_datadog_render_span", None)
            if span:
                try:
                    span.finish()
                except Exception:
                    log.exception("cannot finish render span")

                self._datadog_render_span = None

            fn(self)

            span = getattr(self, "_datadog_request_span", None)
            if span:
                try:
                    span.finish()
                except Exception:
                    log.exception("cannot finish request span")

                self._datadog_request_span = None
                self._datadog_request_context = None
        return on_finish

    def wrap_handler_clear(self, fn):
        """
        Create a wrapped clear() handler method and return it.
        """
        def clear(self):
            span = getattr(self, "_datadog_request_span", None)
            if span:
                span.error = 0
                span.set_tag(http.STATUS_CODE, 200)

            fn(self)
        return clear

    def wrap_handler_set_status(self, fn):
        """
        Create a wrapped set_status() handler method and return it.
        """
        def set_status(self, status_code, reason=None):
            span = getattr(self, "_datadog_request_span", None)
            if span:
                span.set_tag(http.STATUS_CODE, status_code)
                span.error = status_code >= 400 and status_code < 600
                if reason is not None:
                    span.set_tag(errors.ERROR_MSG, reason)

            fn(self, status_code, reason)
        return set_status

    def wrap_handler_render(self, fn):
        """
        Create a wrapped render() handler method and return it.
        """
        tracer = self.tracer

        def render(self, template_name, **kwargs):
            context = self._datadog_request_context

            span = tracer.trace("tornado.render", span_type=http.TEMPLATE,
                                context=context)
            span.set_tag("tornado.template", template_name)
            self._datadog_render_span = span

            fn(self, template_name, **kwargs)

        return render

    def wrap_handler_render_string(self, fn):
        """
        Create a wrapped render_string() handler method and return it.
        """
        tracer = self.tracer

        def render_string(self, template_name, **kwargs):
            context = self._datadog_request_context

            with tracer.trace("tornado.render_string", span_type=http.TEMPLATE,
                              context=context) as span:
                span.set_tag("tornado.template", template_name)
                res = fn(self, template_name, **kwargs)

            return res
        return render_string
