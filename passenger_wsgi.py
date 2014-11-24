#!/usr/bin/env python

import server

def application(environ, start_response):
    return server.app.wsgi(environ, start_response)

