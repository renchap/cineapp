# -*- coding: utf-8 -*-

from flask import render_template, flash, redirect, url_for, g, request, session
from flask.ext.login import login_user, logout_user, current_user, login_required
from app import app, db, lm
from .forms import LoginForm, AddUserForm, AddMovieForm, MarkMovieForm, SearchMovieForm, SelectMovieForm, ConfirmMovieForm
from .models import User, Movie, Mark
from sqlalchemy.exc import IntegrityError, InvalidRequestError
from bcrypt import hashpw, gensalt
from wtforms.ext.sqlalchemy.orm import model_form
from flask.ext.wtf import Form
from datetime import datetime
import config
from .tvmdb import search_movies,get_movie,download_poster

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
	# First, generate all the forms that we going to use in the view
	search_form=SearchMovieForm() 
	select_form=SelectMovieForm()
	confirm_form=ConfirmMovieForm()

	# Search form is validated => Let's fetch the movirs from tvdb.org
	if search_form.submit_search.data  and search_form.validate_on_submit():
		select_form=SelectMovieForm(search_movies(search_form.search.data))

		# Put it in a session in order to to the validation
		session['query_movie'] = search_form.search.data
		
		# Display the selection form
		if len(select_form.movie.choices) == 0:
			flash("Aucun film correspondant","danger")
			return render_template('add_movie_wizard.html', search_form=search_form)
		else:
			return render_template('select_movie_wizard.html', select_form=select_form)

	
	# Validate selection form
	if select_form.submit_select.data:

		# Fetch the query from the previous form in order to fill correctly the radio choices
		movie_query = session.get('query_movie', None)
		if movie_query != None:
			select_form=SelectMovieForm(search_movies(movie_query))

		if select_form.validate_on_submit():
		
			# Fetch the query from the previous form in order to fill correctly the radio choices
			movie_query = session.get('query_movie', None)
			if movie_query != None:
				select_form=SelectMovieForm(search_movies(movie_query))

			# Last step : Set type and origin and add the movie
			movie_to_create=get_movie(select_form.movie.data)
			confirm_form.movie_id.data=select_form.movie.data

			# Go to the final confirmation form
			return render_template('confirm_movie_wizard.html', movie=movie_to_create, form=confirm_form)
	
	# Confirmation form => add into the database
	if confirm_form.submit_confirm.data and confirm_form.validate_on_submit():

		# Form is okay => We can add the movie
		movie_to_create=get_movie(confirm_form.movie_id.data)
		movie_to_create.added_by_user=g.user.id
		movie_to_create.type=confirm_form.type.data.id
		movie_to_create.origin=confirm_form.origin.data.id

		# Add the movie in the database
		try:
			db.session.add(movie_to_create)
			db.session.flush()
			new_movie_id=movie_to_create.id
			db.session.commit()
			flash('Film ajouté','success')

			# Donwload the poster and update the database
			if download_poster(movie_to_create):
				flash('Affiche téléchargée','success')
			else:
				flash('Impossible de rettéléchar le poster','warning')
			
			# Movie added ==> Go to the mark form !
			return redirect(url_for('mark_movie',movie_id_form=new_movie_id))

		except IntegrityError as e:
			flash('Film already exists','danger')
			db.session.rollback()
			return redirect(url_for('add_movie'))

	# If we are here, that means we want to display the first form
	return render_template('add_movie_wizard.html', search_form=search_form)

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
