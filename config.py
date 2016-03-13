import os
basedir = os.path.abspath(os.path.dirname(__file__))

# WTForms Config
WTF_CSRF_ENABLED = True
SECRET_KEY = '\xcaVt\xb7u\x91n/\xec\xf8\xc8,\xd4*\xe83\xe4\xe7A_\xf8}0\xaf'

# Database Settings
SQLALCHEMY_DATABASE_URI = 'mysql://root:tgbnhytgb888sql@127.0.1.1/cine_app'
SQLALCHEMY_MIGRATE_REPO = os.path.join(basedir, 'db_repository')

API_KEY = "f2e6fc93c9cf93e0a32e3546930a6f8a"
API_URL = "http://api.themoviedb.org/3"

# Session Settings
SESSION_TYPE = "filesystem"

# Application Settings
POSTERS_PATH = "/home/ptitoliv/cine_app/app/static/posters"
