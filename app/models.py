# -*- coding: utf-8 -*-
from app import app,db
from sqlalchemy import desc,text, DefaultClause
import flask.ext.whooshalchemy as whooshalchemy
from whoosh.analysis import CharsetFilter, StemmingAnalyzer
from whoosh import fields
from whoosh.support.charset import accent_map
from whoosh.support.charset import default_charset, charset_table_to_dict

class User(db.Model):

	__tablename__ = "users"

	id = db.Column(db.Integer, primary_key=True)
	nickname = db.Column(db.String(64), index=True, unique=True)
	password = db.Column(db.String(255))
	email = db.Column(db.String(120), index=True, unique=True)
	avatar = db.Column(db.String(255), unique=True)
	notif_enabled = db.Column(db.Boolean)
	graph_color = db.Column(db.String(6))
	added_movies = db.relationship('Movie', backref='added_by', lazy='dynamic')

	@property
	def is_authenticated(self):
		return True

	@property
	def is_active(self):
		return True

	@property
	def is_anonymous(self):
		return False

	def get_id(self):
		try:
			return unicode(self.id) # Python 2
		except NameError:
			return str(self.id) # Python 3

	def __repr__(self):
		return '<User %r>' % (self.nickname)
	

class Type(db.Model):
	
	__tablename__ = "types"
	
	id = db.Column(db.String(5),primary_key=True)
	type = db.Column(db.String(20), unique=True)
	movies = db.relationship('Movie', backref='type_object', lazy='dynamic')

class Origin(db.Model):
	
	__tablename__ = "origins"
	
	id = db.Column(db.String(5),primary_key=True)
	origin = db.Column(db.String(50), unique=True)
	movies = db.relationship('Movie', backref='origin_object', lazy='dynamic')

class Movie(db.Model):

	__tablename__ = "movies"

	# Settings for FTS (WooshAlchemy)
	__searchable__ = [ 'name', 'director' ]
	charmap = charset_table_to_dict(default_charset)
	__analyzer__ =  StemmingAnalyzer() | CharsetFilter(charmap)

	id = db.Column(db.Integer, primary_key=True)
	name = db.Column(db.String(100), unique=True, index=True)
	release_date = db.Column(db.Date, index=True)
	type = db.Column(db.String(5), db.ForeignKey('types.id'),index=True)
	url = db.Column(db.String(100), index=True)
	origin = db.Column(db.String(5), db.ForeignKey('origins.id'), index=True)
	director = db.Column(db.String(50), index=True)
	poster_path = db.Column(db.String(255))
	added_by_user = db.Column(db.Integer, db.ForeignKey('users.id'))

	def __repr__(self):
		return '<Movie %r>' % (self.name)

	def next(self):
		"""
			Return the next item into the database
		"""
		return db.session.query(Movie).filter(Movie.id > self.id).order_by(Movie.id).first()

	def prev(self):
		"""
			Return the previous item into the database
		"""
		return db.session.query(Movie).filter(Movie.id < self.id).order_by(desc(Movie.id)).first()

class Mark(db.Model):
	
	__tablename__ = "marks"

	user_id = db.Column(db.Integer, db.ForeignKey('users.id'), primary_key=True)
	movie_id = db.Column(db.Integer, db.ForeignKey('movies.id'), primary_key=True)
	seen_when = db.Column(db.Date)
	seen_where = db.Column(db.String(4))
	mark = db.Column(db.Float)
	comment = db.Column(db.String(1000))
	homework_when = db.Column(db.Date)
	# Server_default allow to put the column with DEFAULT VALUE to NULL which is mandatory if we want the foreign key to be added
	# If the value is not NULL, the default value is O so the foreign constraint is violated
	homework_who = db.Column(db.Integer,db.ForeignKey('users.id'),nullable=True,server_default=text('NULL'))
	movie = db.relationship('Movie', backref='marked_by_users')
	user = db.relationship('User', backref='marked_movies',foreign_keys='Mark.user_id')
	homework_who_user = db.relationship('User', backref='given_homework',foreign_keys='Mark.homework_who')

# Enable FTS indexation
whooshalchemy.whoosh_index(app, Movie)
