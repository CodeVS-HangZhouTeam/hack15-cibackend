#!/usr/bin/env python3

import tornado.ioloop
import tornado.log
import tornado.web


class PullRequestHandler(tornado.web.RequestHandler):
    def post(self):
        self.set_status(204)
        print(self.request.body.decode('utf-8', 'replace'))


application = tornado.web.Application([
    (r"/pr", PullRequestHandler),
])

if __name__ == '__main__':
    tornado.log.enable_pretty_logging()
    application.listen(8080)
    tornado.ioloop.IOLoop.current().start()
