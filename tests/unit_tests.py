# -*- coding: utf-8 -*-

import os
from cineapp import app, db
from cineapp.models import User, Type, Origin
from bcrypt import hashpw, gensalt
import unittest
import tempfile
import shutil
import StringIO

class FlaskrTestCase(unittest.TestCase):

    def setUp(self):
	# Define the test directory
        self.dir = os.path.dirname(__file__)

        self.app = app.test_client()

	# Source test configuration
	app.config.from_pyfile('configs/settings_test.cfg')

	if os.environ.get('TRAVIS') == "yes":
		app.config['SQLALCHEMY_DATABASE_URI'] = 'mysql://root@127.0.0.1/cineapp_ci'
		app.config['POSTER_PATH'] = "/home/travis/cineapp_ci/static/posters"
		app.config['AVATARS_FOLDER'] = "/home/travis/cineapp_ci/static/avatars"

	app.config['WTF_CSRF_ENABLED'] = False
	app.config['TESTING'] = True

	# Delete the directories if they exisits
	if os.path.isdir(os.path.join(app.config['POSTERS_PATH'])):
		shutil.rmtree(app.config['POSTERS_PATH'])

	if os.path.isdir(os.path.join(app.config['AVATARS_FOLDER'])):
		shutil.rmtree(app.config['AVATARS_FOLDER'])

	# Create directories
	os.makedirs(app.config['POSTERS_PATH'])
	os.makedirs(app.config['AVATARS_FOLDER'])

        db.create_all()

    def tearDown(self):
	# Remove directories
	shutil.rmtree(app.config['POSTERS_PATH'])
	shutil.rmtree(app.config['AVATARS_FOLDER'])

	db.session.commit()
	db.drop_all()

    def test_populateUsers(self):
	hashed_password=hashpw("toto1234".encode('utf-8'),gensalt())
	u = User()
	u.nickname="ptitoliv"
	u.password=hashed_password
	u.email="ptitoliv@ptitoliv.net"

	db.session.add(u)
	db.session.commit()

	# Try to fetch user
	u = User.query.get(1)
	assert u.nickname == 'ptitoliv'

    def test_index(self):
        rv = self.app.get('/login')
	assert "Welcome to CineApp" in rv.data

    def test_login_logout(self):
	hashed_password=hashpw("toto1234".encode('utf-8'),gensalt())
	u = User()
	u.nickname="ptitoliv"
	u.password=hashed_password
	u.email="ptitoliv@ptitoliv.net"

	db.session.add(u)
	db.session.commit()
	assert u.nickname == 'ptitoliv'

	# Bad user
	rv=self.app.post('/login',data=dict(username="user",password="pouet"), follow_redirects=True)
	assert "Mauvais utilisateur !" in rv.data 

	# Bad password
	rv=self.app.post('/login',data=dict(username="ptitoliv",password="pouet"), follow_redirects=True)
	assert "Mot de passe incorrect !" in rv.data 

	# Good login
	rv=self.app.post('/login',data=dict(username="ptitoliv",password="toto1234"), follow_redirects=True)
	assert "Welcome <strong>ptitoliv</strong>" in rv.data 

	rv=self.app.get('/logout', follow_redirects=True)
	assert "Welcome to CineApp" in rv.data

    def test_add_movie(self):
	hashed_password=hashpw("toto1234".encode('utf-8'),gensalt())
	u = User()
	u.nickname="ptitoliv"
	u.password=hashed_password
	u.email="ptitoliv@ptitoliv.net"

	db.session.add(u)
	db.session.commit()

	# Add types
	t = Type()
	t.id="C"
	t.type="Comédie"

	db.session.add(t)
	db.session.commit()

	# Add origin
	o = Origin()
	o.id="F"
	o.origin="Francais"

	db.session.add(o)
	db.session.commit()

	rv=self.app.post('/login',data=dict(username="ptitoliv",password="toto1234"), follow_redirects=True)
	assert "Welcome <strong>ptitoliv</strong>" in rv.data 

	# We are logged => add the movie
	rv=self.app.get('/movies/add')
	assert "Ajout d&#39;un film" in rv.data

	# Fill the movie title
	rv=self.app.post('/movies/add/select',data=dict(search="tuche",submit_search=True))
	assert "Les Tuche" in rv.data

	# Select the movie
	rv=self.app.post('/movies/add/confirm',data=dict(movie="66129",submit_select=True))
	assert "Ajouter le film" in rv.data

	# Store the movie into database
	rv=self.app.post('/movies/add/confirm',data=dict(movie_id="66129",origin="F",type="C",submit_confirm=True),follow_redirects=True)
	assert "Film ajout" in rv.data
	assert "Affiche" in rv.data

    def test_upload_avatar(self):
	hashed_password=hashpw("toto1234".encode('utf-8'),gensalt())
	u = User()
	u.nickname="ptitoliv"
	u.password=hashed_password
	u.email="ptitoliv@ptitoliv.net"

	db.session.add(u)
	db.session.commit()

	rv=self.app.post('/login',data=dict(username="ptitoliv",password="toto1234"), follow_redirects=True)
	assert "Welcome <strong>ptitoliv</strong>" in rv.data 

	print self.dir	
	with open(self.dir + '/ressources/test_avatar.png', 'rb') as img1:
        	img1StringIO = StringIO.StringIO(img1.read())

	rv=self.app.post('/my/profile',
                             content_type='multipart/form-data',
			     data=dict(email="ptitoliv+test@ptitoliv.net",upload_avatar=(img1StringIO, 'test_avatar.png')), follow_redirects=True)

	assert "Informations mises à jour" in rv.data
	assert "Avatar correctement mis à jour" in rv.data

if __name__ == '__main__':
    unittest.main()
