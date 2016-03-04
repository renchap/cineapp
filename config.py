import os
basedir = os.path.abspath(os.path.dirname(__file__))

# WTForms Config
WTF_CSRF_ENABLED = True
SECRET_KEY = '<Insert_your_secret_key_here>'

# Database Settings
SQLALCHEMY_DATABASE_URI = 'mysql://<login>:<password>@<hostname>/<database>'
SQLALCHEMY_MIGRATE_REPO = os.path.join(basedir, 'db_repository')
