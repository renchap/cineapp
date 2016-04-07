# -*- coding: utf-8 -*-

from flask import render_template, flash, redirect, url_for, g, request, session
from flask.ext.login import login_user, logout_user, current_user, login_required
from app import app, db, lm
from .forms import LoginForm, AddUserForm, AddMovieForm, MarkMovieForm, SearchMovieForm, SelectMovieForm, ConfirmMovieForm, FilterForm
from .models import User, Movie, Mark
from sqlalchemy.exc import IntegrityError, InvalidRequestError
from bcrypt import hashpw, gensalt
from wtforms.ext.sqlalchemy.orm import model_form
from flask.ext.wtf import Form
from datetime import datetime
import config
import json
from .tvmdb import search_movies,get_movie,download_poster
from sqlalchemy import desc, or_, and_, Table
from sqlalchemy.sql.expression import select
import re

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

	# Make the search form available in all templates (Including base.html)
	g.search_form = SearchMovieForm()

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

@app.route('/movies/list/<int:page>')
@app.route('/movies/list')
@app.route('/movies/filter', methods=[ 'GET', 'POST' ], endpoint="filter_form")
@app.route('/movies/filter/<int:page>', endpoint="filter_mode")
def list_movies(page=1):

	# Display the search form
	filter_form = FilterForm()

	# Let's check if we are in list mode or filter mode
	url_rule=request.url_rule
	if url_rule.rule == "/movies/filter" or url_rule.rule == "/movies/filter/<int:page>":
		# Tell to the pagination system that we are in filter mode
		route_rule="filter_mode"
		session['search_type']="filter"

		print filter_form.submit_filter.data

		# We are in filter mode
		if g.search_form.submit_search.data == True:
			# We come from the form into the navbar
			if g.search_form.validate_on_submit():
				filter_string=g.search_form.search.data
				session['query']=filter_string

		elif filter_form.submit_filter.data == True:
			# We come from the filter form above the datatable
			# Build the filter request

			if filter_form.origin.data == None and filter_form.type.data == None and filter_form.seen_where.data == None:
				# All filter are empty => Let's display the list
				return redirect(url_for('list_movies'))

			session['search_type']="filter_origin_type"
			filter_dict = {'origin' : None, 'type': None, 'seen_where' : None}

			if filter_form.origin.data != None:
				filter_dict['origin'] = filter_form.origin.data.id

			if filter_form.type.data != None:
				filter_dict['type'] = filter_form.type.data.id

			if filter_form.seen_where.data != None:
				filter_dict['seen_where'] = filter_form.seen_where.data.id


			session['query']=filter_dict
		else:
			# We are in filter mode with a pagination request
			filter_string=session.get('query',None)

	else:

		# Tell to the pagination system that we are in list mode
		route_rule="list_movies"
		session['search_type']="list"

	# Let's fetch all the users, I will need them
	users = User.query.all()

	return render_template('movies_list.html', users=users,route_rule=route_rule,filter_form=filter_form)

@app.route('/movies/json', methods=['GET','POST'])
@login_required
def update_datatable():

	# Local variables for handling the datatable
	args = json.loads(request.values.get("args"))
	columns = args.get("columns")
	start = args.get('start')
	length = args.get('length')
	draw = args.get('draw')
	order_by=args.get('order')
	order_column=columns[order_by[0]['column']]['data']
	order_dir=order_by[0]['dir']

	# Guess which is the sort column
	m=re.match('other_marks.(.*)',order_column)

	if m != None:
		filter_user=m.group(1)
	elif order_column == "my_mark":
		filter_user = g.user.id
	else:
		filter_user = None
	
	if filter_user != None:
		# We need a special query for sorting records by logged user mark

		# Let's build the filtered requested following what has been posted in the filter form
		filter_fields=session.get('query')
		movies_query = Movie.query.outerjoin(Mark).filter_by(user_id=filter_user)

		if filter_fields['origin'] != None:
			movies_query = movies_query.filter(Movie.origin==filter_fields['origin'])

		if filter_fields['type'] != None:
			movies_query = movies_query.filter(Movie.type==filter_fields['type'])

		if filter_fields['seen_where'] != None:
			movies_seen_in_theater = Mark.query.filter(Mark.user_id==filter_fields['seen_where']).filter(Mark.seen_where=='C').all()
			array_movies_seen_in_theater = []

			for cur_movie_seen_in_theater in movies_seen_in_theater:
				array_movies_seen_in_theater.append(cur_movie_seen_in_theater.movie_id)

			movies_query = movies_query.filter(Mark.movie_id.in_(array_movies_seen_in_theater))

		if order_dir == "desc":
			if session.get('search_type') == 'list': 
				movies = Movie.query.outerjoin(Mark).filter_by(user_id=filter_user).order_by(desc(Mark.mark)).slice(int(start),int(start) + int(length))
				count_movies=Movie.query.outerjoin(Mark).filter_by(user_id=filter_user).count()
			elif session.get('search_type') == 'filter_origin_type':
				movies = movies_query.order_by(desc(Mark.mark)).slice(int(start),int(start) + int(length))
				count_movies=movies_query.count()
					
			elif session.get('search_type') == 'filter':
				movies = Movie.query.outerjoin(Mark).whoosh_search(session.get('query')).filter_by(user_id=filter_user).order_by(desc(Mark.mark)).slice(int(start),int(start) + int(length))
				count_movies=Movie.query.outerjoin(Mark).whoosh_search(session.get('query')).filter_by(user_id=filter_user).count()
		else:
			if session.get('search_type') == 'list': 
				movies = Movie.query.outerjoin(Mark).filter_by(user_id=filter_user).order_by(Mark.mark).slice(int(start),int(start) + int(length))
				count_movies=Movie.query.outerjoin(Mark).filter_by(user_id=filter_user).count()
			elif session.get('search_type') == 'filter_origin_type':
				movies = movies_query.order_by(Mark.mark).slice(int(start),int(start) + int(length))
				count_movies=movies_query.count()
			elif session.get('search_type') == 'filter':
				movies = Movie.query.outerjoin(Mark).whoosh_search(session.get('query')).filter_by(user_id=filter_user).order_by(Mark.mark).slice(int(start),int(start) + int(length))
				count_movies=Movie.query.outerjoin(Mark).whoosh_search(session.get('query')).filter_by(user_id=filter_user).count()
	else:

		if session.get('search_type') == 'list': 
			movies = Movie.query.order_by(order_column + " " + order_dir).slice(int(start),int(start) + int(length))
			count_movies=Movie.query.count()

		elif session.get('search_type') == 'filter_origin_type':
			# Let's build the filtered requested following what has been posted in the filter form
			filter_fields=session.get('query')
			movies_query = Movie.query

			if filter_fields['origin'] != None:
				movies_query = movies_query.filter(Movie.origin==filter_fields['origin'])

			if filter_fields['type'] != None:
				movies_query = movies_query.filter(Movie.type==filter_fields['type'])

			if filter_fields['seen_where'] !=None:
				movies_query = movies_query.join(Mark).filter_by(user_id=filter_fields['seen_where']).filter(Mark.seen_where=='C')

			# Build the request
			movies = movies_query.order_by(order_column + " " + order_dir).slice(int(start),int(start) + int(length))
			count_movies=movies_query.count()

		elif session.get('search_type') == 'filter':
			movies = Movie.query.whoosh_search(session.get('query')).order_by(order_column + " " + order_dir).slice(int(start),int(start) + int(length))
			count_movies=Movie.query.whoosh_search(session.get('query')).count()

	# Let's fetch all the users, I will need them
	users = User.query.all()

	# Init the dictionnary
	dict_movie = { "draw": draw , "recordsTotal": count_movies, "recordsFiltered" : count_movies, "data": []}
	for cur_movie in movies:
		# Fetch the note for the logged user
		my_mark=-1
		my_when="-"
		my_where=""
		for cur_mark in cur_movie.marked_by_users:
			if cur_mark.user_id == g.user.id:
				my_mark=cur_mark.mark
				my_when=str(cur_mark.seen_when.strftime("%Y"))
				my_where=cur_mark.seen_where

		# Fill a dictionnary with marks for all the others users
		dict_mark = {}
		dict_where = {}
		dict_when = {}
		for cur_user in users:
			dict_mark[cur_user.id]="-"
			dict_where[cur_user.id]="-"
			dict_when[cur_user.id]="-"
			for cur_mark in cur_movie.marked_by_users:
				if cur_mark.user.id == cur_user.id:
					dict_mark[cur_user.id]=cur_mark.mark		
					dict_where[cur_user.id]=cur_mark.seen_where
					dict_when[cur_user.id]=str(cur_mark.seen_when.strftime("%Y"))

		# Create the json object for the datatable
		dict_movie["data"].append({"DT_RowData": { "link": url_for("show_movie",movie_id=cur_movie.id), "mark_link": url_for("mark_movie",movie_id_form=cur_movie.id)}, "id": cur_movie.id,"name": cur_movie.name, "director": cur_movie.director, "my_mark": my_mark, "my_when": my_when, "my_where": my_where, "other_marks": dict_mark, "other_where": dict_where, "other_when": dict_when })

	# Send the json object to the browser
	return json.dumps(dict_movie) 

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
