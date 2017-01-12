"""
To trace requests in a Tornado application, add:

    from ddtrace import tracer
    from ddtrace.contrib.tornado import TraceApp

Then trace the application:

    TraceApp(app, tracer, service="my-tornado-app")

For example, here is a hello world application:

    import tornado.ioloop
    import tornado.web
    import tornado.httpserver

    from ddtrace import tracer
    from ddtrace.contrib.tornado import TraceApp


    class Application(tornado.web.Application):
        def __init__(self):
            handlers = [(r"/", HandlerRoot)]
            settings = dict()
            super().__init__(handlers, **settings)

    class HandlerRoot(tornado.web.RequestHandler):
        def get(self):
            self.write("Hello world!\n")

    app = Application()
    TraceApp(app, tracer, service="hello-world")

    server = tornado.httpserver.HTTPServer(app)
    server.listen(8888)

    tornado.ioloop.IOLoop.current().start()
"""

from .trace_app import TraceApp

__all__ = ['TraceApp']
