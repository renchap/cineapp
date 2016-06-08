from flask import Flask
from flask.ext.login import login_user, logout_user, current_user, login_required, LoginManager
from flask.ext.sqlalchemy import SQLAlchemy
from flask import Flask, session
from flask.ext.session import Session
from flask.ext.mail import Mail
from flask.ext.babel import Babel
import logging, sys, os
from logging.handlers import RotatingFileHandler

app = Flask(__name__)

# Configuration file reading
if os.environ.get('TEST') == "yes":
	app.config.from_pyfile('configs/settings_test.cfg')
else:
	app.config.from_pyfile('configs/settings.cfg')

# Check if API_KEY is defined
if not app.config.has_key('API_KEY'):
	# Let's import it from environnment
	if os.environ.get('API_KEY') != None:
		app.config['API_KEY'] = os.environ.get('API_KEY')
	else:
		sys.exit(1)

# Database Initialization
db = SQLAlchemy(app)

# Login manager init
lm = LoginManager()
lm.init_app(app)
lm.login_view = 'login'

# Session Manager Init
sess = Session()
sess.init_app(app)

# Mail engine init
mail = Mail(app)

# Translation engine init
babel = Babel(app)

##################
# Logging system #
##################

# Open a file rotated every 100MB
file_handler = RotatingFileHandler(os.path.join(app.config['LOGDIR'],'cineapp.log'), 'a', 100 * 1024 * 1024, 10)
file_handler.setFormatter(logging.Formatter('%(asctime)s %(levelname)s: %(message)s [in %(pathname)s:%(lineno)d]'))
app.logger.setLevel(logging.INFO)
app.logger.addHandler(file_handler)
app.logger.info('Cineapp startup')

from cineapp import views, models
