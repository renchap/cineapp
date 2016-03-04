# -*- coding: utf-8 -*-

from flask import render_template, flash, redirect, url_for, g, request
from flask.ext.login import login_user, logout_user, current_user, login_required
from app import app, db, lm
from .forms import LoginForm, AddUserForm, AddMovieForm, MarkMovieForm
from .models import User, Movie, Mark
from sqlalchemy.exc import IntegrityError, InvalidRequestError
from bcrypt import hashpw, gensalt
from wtforms.ext.sqlalchemy.orm import model_form
from flask.ext.wtf import Form
from datetime import datetime

@app.route('/')
@app.route('/index')
def index():
	return redirect(url_for('login'))

@app.before_request
def before_request():
	# Store the current authenticated user into a global object
	# current_user set by flask
	# g set by flask
	g.user = current_user

@app.route('/login', methods=['GET','POST'])
def login():

	# Let's check if we are authenticated => If yes redirect to the index page
	if g.user is not None and g.user.is_authenticated:
        	return redirect(url_for('list_my_movies'))

	# If we are here, we are not login. Build the form and try the login.
	form = LoginForm()
	if form.validate_on_submit():
		# Let's validate the user
		user=User.query.filter_by(nickname=form.username.data).first()
		if user is None:
			flash("Mauvais utilisateur !",'danger')
			return redirect(url_for('login'))
		else:
			if hashpw(form.password.data.encode('utf-8'), user.password.encode('utf-8')) != user.password:
				flash("Mot de passe incorrect !",'danger')
				return redirect(url_for('login'))
			# User authenticated => Let's login it
			login_user(user)
			return redirect(request.args.get('next') or url_for('index'))
		return redirect(url_for('index'))
	
	return render_template('login.html', title='Sign In', form=form)

@app.route('/logout')
def logout():
	logout_user()
	return redirect(url_for('index'))

@app.route('/movies/list')
@app.route('/movies/list/<int:page>')
def list_movies(page=1):
	movies = Movie.query.paginate(page,20,False)

	# Let's fetch all the users, I will need them
	users = User.query.all()
	return render_template('movies_list.html', movies=movies, users=users)

@app.route('/movies/show/<int:movie_id>')
@login_required
def show_movie(movie_id):
	# Select movie
	movie = Movie.query.get_or_404(movie_id)

	# Let's check if the movie has already been marked
	marked_movie=Mark.query.get((g.user.id,movie_id))

	if marked_movie is None:
		return render_template('movie_show.html', movie=movie, movie_next=movie.next(),movie_prev=movie.prev(),marked_flag=False)
	else:
		return render_template('movie_show.html', movie=movie, movie_next=movie.next(),movie_prev=movie.prev(),marked_flag=True)

@app.route('/movies/mark/<int:movie_id_form>', methods=['GET','POST'])
@login_required
def mark_movie(movie_id_form):
	# Select movie
	form=MarkMovieForm()
	movie = Movie.query.get_or_404(movie_id_form)

	# Let's check if the movie has already been marked
	marked_movie=Mark.query.get((g.user.id,movie_id_form))

	# Mark the movie and display the correct page
	if form.validate_on_submit():
		mark=Mark(user_id=g.user.id,
			movie_id=movie.id,
			seen_when=datetime.utcnow(),
			seen_where=form.seen_where.data,
			mark=form.mark.data,
			comment=form.comment.data
		)	

		try:
			db.session.add(mark)
			db.session.commit()
			flash('Note ajoutée','success')
			return redirect(url_for('show_movie',movie_id=movie_id_form))
			
		except IntegrityError:
			db.session.rollback()
			flash('Impossible d\'ajouter la note')
			return render_template('movie_show.html', movie=movie, mark=True, marked_flag=False, form=form)

	if marked_movie is None:
		return render_template('movie_show.html', movie=movie, mark=True, marked_flag=False, form=form)
	else:
		return render_template('movie_show.html', movie=movie, mark=True, marked_flag=True)

@app.route('/movies/add', methods=['GET','POST'])
@login_required
def add_movie():
	# Generate the form directly from Model
	form = AddMovieForm()
	
	# Let's add the movie into the database
	# For origin and type since we use a QuerySelectField, we get an object !
	# So we need to get the attribute
	if form.validate_on_submit():
		movie=Movie(name=form.name.data,
			year=form.year.data,
			url=form.url.data,
			director=form.director.data,
			origin=form.origin.data.id,
			type=form.type.data.id,
			added_by_user=g.user.id
		)

		try:
			db.session.add(movie)
			db.session.flush()
			new_movie_id=movie.id
			db.session.commit()
			flash('Film ajouté','success')
			return redirect(url_for('mark_movie',movie_id_form=new_movie_id))
		except IntegrityError:
			db.session.rollback()
			flash('Impossible d\'ajouter le film','danger')
		
	return render_template('add_movie.html', form=form)

@app.route('/my/marks')
@app.route('/my/marks/<int:page>')
@login_required
def list_my_movies(page=1):
	marked_movies=Mark.query.filter_by(user_id=g.user.id).paginate(page,15,False)
	return render_template('marks.html', marked_movies=marked_movies)

@lm.user_loader
def load_user(id):
	return User.query.get(int(id))

@app.route('/users/add', methods=['GET','POST'])
@login_required
def add_user():
	form=AddUserForm()
	if form.validate_on_submit():
		# Form is okay => add the user
		# But salt the password before
		hashed_password=hashpw(form.password.data.encode('utf-8'),gensalt())
	
		# Now add the user into the database	
		user=User(nickname=form.username.data,password=hashed_password,email=form.email.data)
		try:
			db.session.add(user)
			db.session.commit()
			flash('Utilisateur added')
		except IntegrityError:
			flash('Utilisateur déjà existant')
	return render_template('add_user_form.html', form=form)
