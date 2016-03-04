from flask import Flask
from flask.ext.login import login_user, logout_user, current_user, login_required, LoginManager
from flask.ext.sqlalchemy import SQLAlchemy

app = Flask(__name__)

# Configuration file reading
app.config.from_object('config')

# Database Initialization
db = SQLAlchemy(app)
# Login manager init
lm = LoginManager()
lm.init_app(app)
lm.login_view = 'login'

from app import views, models

