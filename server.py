#!/usr/bin/env python

import bottle

@bottle.route('/')
def index():
    return "it still works!" 

app = bottle.default_app()

def application(environ, start_response):
    return app.wsgi(environ, start_response) 

if __name__ == "__main__":
    bottle.debug(True)
    bottle.run(app, host='0.0.0.0', port='8088', reloader=True)

