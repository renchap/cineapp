from flask import Flask
from flask.ext.login import login_user, logout_user, current_user, login_required, LoginManager
from flask.ext.sqlalchemy import SQLAlchemy
from flask import Flask, session
from flask.ext.session import Session

app = Flask(__name__)

# Configuration file reading
app.config.from_object('config')

# Database Initialization
db = SQLAlchemy(app)

# Login manager init
lm = LoginManager()
lm.init_app(app)
lm.login_view = 'login'

# Session Manager Init
sess = Session()
sess.init_app(app)

from app import views, models
