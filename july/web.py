from tornado import web, escape
from july.template import JulyTemplateLoader

__all__ = ["JulyHandler", "ApiHandler", "run_server"]


class JulyHandler(web.RequestHandler):
    """July Handler

    Subclass JulyHandler to make an app, it provides a way to organize a July
    App, and will support more features in the future.

    If you don't want the in app template feature, set app_template=False::

        class HomeHandler(JulyHandler):
            app_template = False

            def get(self):
                self.write('hello world')
    """
    app_template = True

    def _get_app(self):
        if hasattr(self, '_july_app'):
            return self._july_app
        if '__july_apps__' in self.settings:
            app = self.settings['__july_apps__'].get(self.__module__, None)
            self._july_app = app

        self._july_app = None
        return self._july_app

    def create_template_loader(self, template_path):
        app = self._get_app()
        if app and self.app_template:
            kwargs = {}
            if 'autoescape' in self.settings:
                kwargs['autoescape'] = self.settings['autoescape']

            return JulyTemplateLoader(template_path, app, **kwargs)
        return super(JulyHandler, self).create_template_loader(template_path)

    def render_string(self, template_name, **kwargs):
        #: add application filters
        if '__july_filters__' in self.settings:
            kwargs.update(self.settings['__july_filters__'])

        #: add application global variables
        if '__july_global__' in self.settings:
            assert "g" not in kwargs, "g is a reserved keyword."
            kwargs["g"] = self.settings['__july_global__']

        #: add app filters
        app = self._get_app()
        if app and '__july_filters__' in app.settings:
            kwargs.update(app.settings['__july_filters__'])

        return super(JulyHandler, self).render_string(template_name, **kwargs)


class ApiHandler(web.RequestHandler):
    xsrf_protect = False

    def check_xsrf_cookie(self):
        if not self.xsrf_protect:
            return
        return super(ApiHandler, self).check_xsrf_cookie()

    def is_ajax(self):
        return "XMLHttpRequest" == self.request.headers.get("X-Requested-With")

    def write(self, chunk):
        self.set_header("Content-Type", "application/json; charset=UTF-8")
        if isinstance(chunk, (dict, list)):
            chunk = escape.json_encode(chunk)
            callback = self.get_argument('callback', None)
            if callback:
                chunk = "%s(%s)" % (callback, escape.to_unicode(chunk))
                self.set_header("Content-Type",
                                "application/javascript; charset=UTF-8")
        super(ApiHandler, self).write(chunk)


def run_server(app):
    import logging
    import tornado.locale
    from tornado import httpserver, ioloop
    from tornado.options import options, parse_command_line
    parse_command_line()
    server = httpserver.HTTPServer(app(), xheaders=True)
    server.listen(int(options.port), options.address)

    if options.locale_path:
        tornado.locale.load_translations(options.locale_path)
        tornado.locale.set_default_locale(options.default_locale)

    logging.info('Start server at %s:%s' % (options.address, options.port))
    ioloop.IOLoop.instance().start()
