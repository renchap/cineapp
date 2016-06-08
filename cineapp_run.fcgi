#!/usr/local/bin/python
import os

activate_this = ''
execfile(activate_this, dict(__file__=activate_this))

from flup.server.fcgi import WSGIServer
from cineapp import app

if __name__ == '__main__':
    WSGIServer(app).run()
