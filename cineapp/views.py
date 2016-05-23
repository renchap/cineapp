# -*- coding: utf-8 -*-

import urllib, hashlib, re, os, locale, json
from datetime import datetime
from flask import render_template, flash, redirect, url_for, g, request, session
from flask.ext.login import login_user, logout_user, current_user, login_required
from flask.ext.wtf import Form
from wtforms.ext.sqlalchemy.orm import model_form
from wtforms.ext.sqlalchemy.fields import QuerySelectField
from cineapp import app, db, lm
from cineapp.forms import LoginForm, AddUserForm, AddMovieForm, MarkMovieForm, SearchMovieForm, SelectMovieForm, ConfirmMovieForm, FilterForm, UserForm, PasswordForm, HomeworkForm
from cineapp.models import User, Movie, Mark, Origin, Type
from cineapp.tvmdb import search_movies,get_movie,download_poster
from cineapp.emails import add_movie_notification, mark_movie_notification, add_homework_notification
from cineapp.utils import frange
from sqlalchemy.exc import IntegrityError, InvalidRequestError
from sqlalchemy.orm.exc import FlushError
from sqlalchemy import desc, or_, and_, Table
from sqlalchemy.sql.expression import select, case, literal
from bcrypt import hashpw, gensalt

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
        	return redirect(url_for('show_dashboard'))

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
@app.route('/movies/filter', methods=[ 'GET', 'POST' ], endpoint="filter_form")
@app.route('/movies/filter/<int:page>', endpoint="filter_mode")
def list_movies(page=1):

	# Display the search form
	filter_form = FilterForm()

	# Fetch the query string or dict => We'll need it later
	session_query=session.get('query')
	
	# If clear_table session variable is set to false, that means we come from add_homework
	if session.pop('clear_table',None) == False:
		clear_table=False
	else:
		clear_table=True

	# Let's check if we are in list mode or filter mode
	url_rule=request.url_rule
	if url_rule.rule == "/movies/filter" or url_rule.rule == "/movies/filter/<int:page>":
		# Tell to the pagination system that we are in filter mode
		route_rule="filter_mode"
		session['search_type']="filter"

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

			# Put the forms parameter into a session object in order to be handled by the datatable
			session['search_type']="filter_origin_type"
			filter_dict = {'origin' : None, 'type': None, 'seen_where' : None}

			if filter_form.origin.data != None:
				filter_dict['origin'] = filter_form.origin.data.id

			if filter_form.type.data != None:
				filter_dict['type'] = filter_form.type.data.id

			if filter_form.seen_where.data != None:
				filter_dict['seen_where'] = filter_form.seen_where.data.id

			session['query']=filter_dict

		elif isinstance(session_query,dict):
			# We come from an homework link and we want to fill the form
			session['search_type']="filter_origin_type"
			
			# Rebuild the form setting default values stores into the session object
			# We need to check if the variable is not or none in order to avoid an exception
			if session_query['origin'] == None:
				origin = None
			else:
				origin=Origin.query.get(session_query['origin'])

			if session_query['type'] == None:
				type = None
			else:
				type=Type.query.get(session_query['type'])

			if session_query['seen_where'] == None:
				seen_where=None
			else:
				seen_where=User.query.get(session_query['seen_where'])

			# Recreate the form with the set default values
			filter_form=FilterForm(origin=origin,type=type,seen_where=seen_where)
		else:
			# We are in filter mode with a pagination request
			filter_string=session.get('query',None)

	else:

		# Tell to the pagination system that we are in list mode
		route_rule="list_movies"
		session['search_type']="list"

	# Let's fetch all the users, I will need them
	users = User.query.all()

	return render_template('movies_list.html', users=users,route_rule=route_rule,filter_form=filter_form,clear_table=clear_table)

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

		# Let's build the filtered requested following what has been posted in the filter form
		filter_fields=session.get('query')
		movies_query = Movie.query.outerjoin(Mark).filter_by(user_id=filter_user)

		# Check that we have a real list in order to avoid an exception	
		if filter_fields is list:
			if filter_fields['origin'] != None:
				movies_query = movies_query.filter(Movie.origin==filter_fields['origin'])

			if filter_fields['type'] != None:
				movies_query = movies_query.filter(Movie.type==filter_fields['type'])

			if filter_fields['seen_where'] != None:

				# We want to sort movies for a specific user keeping the seen_where filter enabled
				# So we want to see movies seen in theater (or not) by a user sorting these movies by marks of another user
				# Since we sort by marks, we don't want to see movies without a mark for that user
				# So we need that to build that specific subquery.

				# First let's fetch the movies seen by a user in theaters
				movies_seen_in_theater = Mark.query.filter(Mark.user_id==filter_fields['seen_where']).filter(Mark.seen_where=='C').all()
				array_movies_seen_in_theater = []

				# Then build a list of these movies
				for cur_movie_seen_in_theater in movies_seen_in_theater:
					array_movies_seen_in_theater.append(cur_movie_seen_in_theater.movie_id)
				
				# Finally let's build the filter that will be used later building the query
				movies_query = movies_query.filter(Mark.movie_id.in_(array_movies_seen_in_theater))

		# Sort my desc marks
		if order_dir == "desc":
			if session.get('search_type') == 'list': 
				movies = Movie.query.outerjoin(Mark).filter_by(user_id=filter_user).filter(Mark.mark != None).order_by(desc(Mark.mark)).slice(int(start),int(start) + int(length))
				count_movies=Movie.query.outerjoin(Mark).filter_by(user_id=filter_user).count()

			elif session.get('search_type') == 'filter_origin_type':
				movies = movies_query.filter(Mark.mark != None).order_by(desc(Mark.mark)).slice(int(start),int(start) + int(length))
				count_movies=movies_query.filter(Mark.mark != None).count()
					
			elif session.get('search_type') == 'filter':
				movies = Movie.query.outerjoin(Mark).whoosh_search(session.get('query')).filter_by(user_id=filter_user).filter(Mark.mark != None).order_by(desc(Mark.mark)).slice(int(start),int(start) + int(length))
				count_movies=Movie.query.outerjoin(Mark).whoosh_search(session.get('query')).filter_by(user_id=filter_user).filter(Mark.mark != None).count()

		# Sort by asc marks
		else:
			if session.get('search_type') == 'list': 
				movies = Movie.query.outerjoin(Mark).filter_by(user_id=filter_user).filter(Mark.mark != None).order_by(Mark.mark).slice(int(start),int(start) + int(length))
				count_movies=Movie.query.outerjoin(Mark).filter_by(user_id=filter_user).count()
			elif session.get('search_type') == 'filter_origin_type':
				movies = movies_query.filter(Mark.mark != None).order_by(Mark.mark).slice(int(start),int(start) + int(length))
				count_movies=movies_query.filter(Mark.mark != None).count()
			elif session.get('search_type') == 'filter':
				movies = Movie.query.outerjoin(Mark).whoosh_search(session.get('query')).filter_by(user_id=filter_user).filter(Mark.mark != None).order_by(Mark.mark).slice(int(start),int(start) + int(length))
				count_movies=Movie.query.outerjoin(Mark).whoosh_search(session.get('query')).filter_by(user_id=filter_user).count()
	else:

		# If we are are => No sort. Just filter or list display.
		if session.get('search_type') == 'list': 
			movies = Movie.query.order_by(order_column + " " + order_dir).slice(int(start),int(start) + int(length))
			count_movies=Movie.query.count()

		# Let's use the filter form
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

		# Here, this is for the string search (Movie or director)
		elif session.get('search_type') == 'filter':
			movies = Movie.query.whoosh_search(session.get('query')).order_by(order_column + " " + order_dir).slice(int(start),int(start) + int(length))
			count_movies=Movie.query.whoosh_search(session.get('query')).count()

	# Let's fetch all the users, I will need them
	users = User.query.all()

	# Init the dictionnary
	dict_movie = { "draw": draw , "recordsTotal": count_movies, "recordsFiltered" : count_movies, "data": []}
	for cur_movie in movies:
		# Fetch the note for the logged user
		my_mark=None
		my_when="-"
		my_where=""
		my_comment=""

		# Calculate the average mark for each movie
		average_mark_query=db.session.query(db.func.avg(Mark.mark).label("average")).filter(Mark.movie_id==cur_movie.id).one()
		
		try:
			# Round the average mark for a better display
			average_mark=round(float(average_mark_query.average),2)
		except:
			# There is no average because no mark recorded
			average_mark="-"

		for cur_mark in cur_movie.marked_by_users:
			if cur_mark.user_id == g.user.id:
				my_mark=cur_mark.mark
				my_comment = cur_mark.comment

				# Convert the date object only if seen_when field is not null (Homework UC)
				if cur_mark.seen_when != None:
					my_when=str(cur_mark.seen_when.strftime("%Y"))

				my_where=cur_mark.seen_where

		# Fill a dictionnary with marks for all the others users
		dict_mark = {}
		dict_where = {}
		dict_when = {}
		dict_homework = {}
		dict_comments = {}
		for cur_user in users:
			dict_mark[cur_user.id]=None
			dict_comments[cur_user.id]=None
			dict_where[cur_user.id]="-"
			dict_when[cur_user.id]="-"
			dict_homework[cur_user.id]={ "when" : None, "who:" : None, "link" : url_for("add_homework",movie_id=cur_movie.id,user_id=cur_user.id)}
			for cur_mark in cur_movie.marked_by_users:
				if cur_mark.user.id == cur_user.id:
					dict_mark[cur_user.id]=cur_mark.mark		
					dict_where[cur_user.id]=cur_mark.seen_where
					dict_comments[cur_user.id]=cur_mark.comment
					dict_homework[cur_user.id]["when"]=str(cur_mark.homework_when)

					if cur_mark.homework_who_user != None:
						dict_homework[cur_user.id]["who"]=cur_mark.homework_who_user.nickname

					# Convert the date object only if seen_when field is not null (Homework UC)
					if cur_mark.seen_when != None:
						dict_when[cur_user.id]=str(cur_mark.seen_when.strftime("%Y"))

		# Create the json object for the datatable
		dict_movie["data"].append({"DT_RowData": { "link": url_for("show_movie",movie_id=cur_movie.id), "mark_link": url_for("mark_movie",movie_id_form=cur_movie.id),"homework_link": dict_homework},
		"id": cur_movie.id,"name": cur_movie.name, 
		"director": cur_movie.director,
		"average" : average_mark,
		"my_mark": my_mark, 
		"my_when": my_when,
		"my_where": my_where, 
		"my_comment": my_comment,
		"other_marks": dict_mark, 
		"other_where": dict_where,
		"other_when": dict_when,
		"other_comments": dict_comments,
		"other_homework_when" : dict_homework })

	# Send the json object to the browser
	return json.dumps(dict_movie) 

@app.route('/movies/show/<int:movie_id>')
@login_required
def show_movie(movie_id):
	# Select movie
	movie = Movie.query.get_or_404(movie_id)

	# Initialize the dict which will contain the data to be displayed
	mark_users=[]

	# Get user list
	users=User.query.all()

	# Browse all users
	for cur_user in users:
		print "On traite" + cur_user.nickname

		# Let's check if the movie has already been marked by the user
		marked_movie=Mark.query.get((cur_user.id,movie_id))

		if marked_movie != None:
			if marked_movie.homework_who != None:
				mark_users.append({ "user": cur_user, "mark": "homework_in_progress", "comment": "N/A" })
			else:
				mark_users.append({ "user": cur_user, "mark": marked_movie.mark, "comment": marked_movie.comment })
		else:
			mark_users.append({ "user" : cur_user, "mark": None, "comment": "N/A" })

	# Let's check if the movie has already been marked by the user
	marked_movie=Mark.query.get((g.user.id,movie_id))

	if marked_movie is None or marked_movie.mark == None:
		return render_template('movie_show.html', movie=movie, mark_users=mark_users, movie_next=movie.next(),movie_prev=movie.prev(),marked_flag=False)
	else:
		return render_template('movie_show.html', movie=movie, mark_users=mark_users, movie_next=movie.next(),movie_prev=movie.prev(),marked_flag=True)

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

		if marked_movie == None:
			marked_movie=Mark(user_id=g.user.id,
				movie_id=movie.id,
				seen_when=datetime.utcnow(),
				seen_where=form.seen_where.data,
				mark=form.mark.data,
				comment=form.comment.data,
				updated_when=datetime.now()
			)	
		else:
			marked_movie.mark=form.mark.data
			marked_movie.comment=form.comment.data
			updated_when=datetime.now()
			
		try:
			db.session.add(marked_movie)
			db.session.commit()
			flash('Note ajoutée','success')

			# Send notification
			mark_movie_notification(marked_movie)
			return redirect(url_for('show_movie',movie_id=movie_id_form))
			
		except IntegrityError:
			db.session.rollback()
			flash('Impossible d\'ajouter la note','danger')
			return render_template('movie_show.html', movie=movie, mark=True, marked_flag=False, form=form)

		except FlushError:
			db.session.rollback()
			flash('Impossible d\'ajouter la note','danger')
			return render_template('movie_show.html', movie=movie, mark=True, marked_flag=False, form=form)

	if marked_movie is None or marked_movie.mark == None:
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
		movie_to_create.added_when=datetime.now()

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
				flash('Impossible de télécharger le poster','warning')

			# Movie has been added => Send notifications
			add_movie_notification(movie_to_create)
			
			# Movie added ==> Go to the mark form !
			return redirect(url_for('mark_movie',movie_id_form=new_movie_id))

		except IntegrityError as e:
			flash('Film déjà existant','danger')
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
			flash('Utilisateur ajouté')
		except IntegrityError:
			flash('Utilisateur déjà existant')
	return render_template('add_user_form.html', form=form)

@app.route('/my/profile', methods=['GET', 'POST'])
@login_required
def edit_user_profile():

	# Init the form
	form=UserForm(obj=g.user)
	
	if form.validate_on_submit():
		# Update the User object
		g.user.email = form.email.data
		g.user.notif_enabled = form.notif_enabled.data

		try:
			db.session.add(g.user)
			db.session.commit()
			flash('Informations mises à jour','success')
		except:
			flash('Impossible de mettre à jour l\'utilisateur', 'danger')

	# Fetch the object for the current logged_in user
	return render_template('edit_profile.html',form=form,state="user")

@app.route('/my/password', methods=['GET', 'POST'])
@login_required
def change_user_password():

	# Init the form
	form=PasswordForm(obj=g.user)

	# Check the form and validation the password check is ok
	if form.validate_on_submit():
		# Let's fetch the password from the form
		g.user.password = hashpw(form.password.data.encode('utf-8'),gensalt())
		try:
			db.session.add(g.user)
			db.session.commit()
			flash('Mot de passe mis à jour','success')
		except:
			flash('Impossible de mettre à jour le mot de passe', 'danger')
	
	# Fetch the object for the current logged_in user
	return render_template('edit_profile.html',form=form,state="password")

@app.route('/homework/add/<int:movie_id>/<int:user_id>')
@login_required
def add_homework(movie_id,user_id):
	
	# Create the mark object
	mark=Mark(user_id=user_id,movie_id=movie_id,homework_who=g.user.id,homework_when=datetime.now())

	# We want to add an homework => Set a session variable in order to tell to the list_movies table not cleaning the table
	session['clear_table']=False

	# Add the object to the database
	try:
		db.session.add(mark)
		db.session.commit()
		flash('Devoir ajouté','success')
	
	except Exception,e: 
		flash('Impossible de creer le devoir','danger')
		return redirect(url_for('list_movies'))

	# Send email notification
	mail_status = add_homework_notification(mark)
	if mail_status == 0:
		flash('Notification envoyée','success')
	elif mail_status == 1:
		flash('Erreur lors de l\'envoi de la notifiction','danger')
	elif mail_status == 2:
		flash('Aucune notification à envoyer','warning')

	return redirect(url_for('show_movie',movie_id=movie_id))

@app.route('/homework/list',methods=['GET','POST'])
@login_required
def list_homeworks():

	# If we have a get request, we don't come fomr a form
	# ==> Let's clean session variables
	if request.method == "GET":	
		session.pop('my_homework_filter','None')
		session.pop('given_homework_filter','None')

	# Create the two forms for user filtering
	if session.get('my_homework_filter', None) != None:
		my_homework_filter_form=HomeworkForm(label_name=u'Donné à:',prefix=u"my",user_filter=User.query.get(session.get('my_homework_filter',None)))
	else:
		my_homework_filter_form=HomeworkForm(label_name=u'Donné à:',prefix=u"my")

	if session.get('given_homework_filter', None) != None:
		given_homework_filter_form=HomeworkForm(label_name=u"Donné par:",prefix=u"given",user_filter=User.query.get(session.get('given_homework_filter')))
	else:
		given_homework_filter_form=HomeworkForm(label_name=u"Donné par:",prefix=u"given")

	# Query generation considering from where we do come from
	# We sort the results first by null results in order to show
	# movies we have to rate and them movies which have been rated
	# For this query, we use a case statement
	# http://stackoverflow.com/questions/1347894/order-by-null-first-then-order-by-other-variable

	# Fetch homeworks given by a user
	if my_homework_filter_form.validate_on_submit():

		if my_homework_filter_form.user_filter.data != None:
			# Save the filter into a session variable => Will be used if we do a search in the other form
			session['my_homework_filter']=my_homework_filter_form.user_filter.data.id
			
			my_homeworks = Mark.query.join(Mark.movie).filter(and_(Mark.user_id == g.user.id, Mark.homework_who != None, Mark.homework_who == my_homework_filter_form.user_filter.data.id)).order_by(desc(case([(Mark.mark == None, 0)],1)),Movie.name)
		else:
			my_homeworks = Mark.query.join(Mark.movie).filter(and_(Mark.user_id == g.user.id, Mark.homework_who != None)).order_by(desc(case([(Mark.mark == None, 0)],1)),Movie.name)

	elif session.get('my_homework_filter', None) != None:
		my_homeworks = Mark.query.join(Mark.movie).filter(and_(Mark.user_id == g.user.id, Mark.homework_who != None, Mark.homework_who == session.get('my_homework_filter'))).order_by(desc(case([(Mark.mark == None, 0)],1)),Movie.name)
	else:
		my_homeworks = Mark.query.join(Mark.movie).filter(and_(Mark.user_id == g.user.id, Mark.homework_who != None)).order_by(desc(case([(Mark.mark == None, 0)],1)),Movie.name)

	
	# Fetch homeworks given to other users	
	if given_homework_filter_form.validate_on_submit():

		if given_homework_filter_form.user_filter.data != None:
			
			# Save the filter into a session variable => Will be used if we do a search in the other form
			session['given_homework_filter']=given_homework_filter_form.user_filter.data.id

			given_homeworks = Mark.query.join(Mark.movie).filter(and_(Mark.homework_who == g.user.id, Mark.homework_who != None, Mark.user_id == given_homework_filter_form.user_filter.data.id)).order_by(desc(case([(Mark.mark == None, 0)],1)),Movie.name)
		else:
			given_homeworks = Mark.query.join(Mark.movie).filter(and_(Mark.homework_who != None)).order_by(desc(case([(Mark.mark == None, 0)],1)),Movie.name)

	elif session.get('given_homework_filter', None) != None:
		given_homeworks = Mark.query.join(Mark.movie).filter(and_(Mark.homework_who == g.user.id, Mark.user_id == session.get('given_homework_filter'))).order_by(desc(case([(Mark.mark == None, 0)],1)),Movie.name)
	else:
		given_homeworks = Mark.query.join(Mark.movie).filter(Mark.homework_who == g.user.id).order_by(desc(case([(Mark.mark == None, 0)],1)),Movie.name)

	return render_template('list_homeworks.html',my_homeworks=my_homeworks,given_homeworks=given_homeworks,my_homework_filter_form=my_homework_filter_form,given_homework_filter_form=given_homework_filter_form)

@app.route('/graph/mark', endpoint="graph_by_mark")
@app.route('/graph/type', endpoint="graph_by_type")
@app.route('/graph/origin', endpoint="graph_by_origin")
@app.route('/graph/year', endpoint="graph_by_year")
@app.route('/graph/year_theater', endpoint="graph_by_year_theater")
@login_required
def show_graphs():

	# Generate the correct data considering the route
	graph_to_generate=os.path.basename(request.url_rule.rule)

	# Variable initialization
	labels=[]
	data={}

	# Fetch all users
	users = User.query.all();

	if graph_to_generate == "mark":
		
		# Distributed marks graph
		graph_title="Repartition par annee"
		graph_type="line"

		# Fill the labels_array with all marks possible
		for cur_mark in frange(0,20,0.5):
			labels.append(cur_mark)

		# Fill the dictionnary with distributed_marks by user
		for cur_user in users:
			data[cur_user.nickname] = { "color" : cur_user.graph_color, "data" : [] }
			for cur_mark in frange(0,20,0.5):
				data[cur_user.nickname]["data"].append(Mark.query.filter(Mark.mark==cur_mark,Mark.user_id==cur_user.id).count())

	elif graph_to_generate == "type":

		# Distributed types graph
		graph_title="Repartition par type"
		graph_type="radar"

		# Fill the types_array with all the types stored into the database
		types = Type.query.all();
		for cur_type in types:
			labels.append(cur_type.type)

		# Fill the dictionnary with distributed_types by user
		for cur_user in users:
			data[cur_user.nickname] = { "color" : cur_user.graph_color, "data" : [] }
			for cur_type in types:
				data[cur_user.nickname]["data"].append(Mark.query.join(Mark.movie).filter(Mark.mark!=None,Mark.user_id==cur_user.id,Movie.type==cur_type.id).count())
	
	elif graph_to_generate == "origin":

		# Distributed marks graph
		graph_title="Repartition par origine"
		graph_type="bar"

		# Fill the origin_array with all the types stored into the database
		origins = Origin.query.all();
		for cur_origin in origins:
			labels.append(cur_origin.origin)

		# Fill the dictionnary with distributed_origins by user
		for cur_user in users:
			data[cur_user.nickname] = { "color" : cur_user.graph_color, "data" : [] }
			for cur_origin in origins:
				data[cur_user.nickname]["data"].append(Mark.query.join(Mark.movie).filter(Mark.mark!=None,Mark.user_id==cur_user.id,Movie.origin==cur_origin.id).count())

	elif graph_to_generate == "year":

		# Distributed movies graph by year
		graph_title="Repartition par annee"
		graph_type="line"

		# Search the min and max year in order to generate a optimized graph
		min_year=int(db.session.query(db.func.min(Mark.seen_when).label("min_year")).one().min_year.strftime("%Y"))
		max_year=int(db.session.query(db.func.max(Mark.seen_when).label("max_year")).one().max_year.strftime("%Y"))

		for cur_year in range(min_year,max_year+1,1):
			labels.append(cur_year)

		# Fill the dictionnary with distributed_years by user
		for cur_user in users:
			data[cur_user.nickname] = { "color" : cur_user.graph_color, "data" : []}
			for cur_year in range(min_year,max_year+1,1):
				data[cur_user.nickname]["data"].append(Mark.query.filter(Mark.mark!=None,Mark.user_id==cur_user.id,db.func.year(Mark.seen_when)==cur_year).count())

	elif graph_to_generate == "year_theater":

		# Distributed movies graph by year
		graph_title="Films vus au cine"
		graph_type="line"

		# Search the min and max year in order to generate a optimized graph
		min_year=int(db.session.query(db.func.min(Mark.seen_when).label("min_year")).one().min_year.strftime("%Y"))
		max_year=int(db.session.query(db.func.max(Mark.seen_when).label("max_year")).one().max_year.strftime("%Y"))

		for cur_year in range(min_year,max_year+1,1):
			labels.append(cur_year)

		# Fill the dictionnary with distributed_years by user
		for cur_user in users:
			data[cur_user.nickname] = { "color" : cur_user.graph_color, "data" : []}
			for cur_year in range(min_year,max_year+1,1):
				data[cur_user.nickname]["data"].append(Mark.query.filter(Mark.mark!=None,Mark.user_id==cur_user.id,Mark.seen_where=="C",db.func.year(Mark.seen_when)==cur_year).count())

	return render_template('show_graphs.html',graph_title=graph_title,graph_type=graph_type,labels=labels,data=data)

@app.route('/dashboard')
@login_required
def show_dashboard():

	# Object_items
	object_list=[]
	general_stats={}
	stats_dict={}
	labels=[]
	data={"theaters": [], "others": []}
	
	# Movie Query
	movies_query=db.session.query(Movie.id,literal("user_id").label("user_id"),Movie.added_when.label("entry_date"),literal("movies").label("entry_type"))

	# Marks Query
	marks_query=db.session.query(Mark.movie_id,Mark.user_id.label("user_id"),Mark.updated_when.label("entry_date"),literal("marks").label("entry_type"))

	# Build the union request
	activity_list = movies_query.union(marks_query).order_by(desc("entry_date")).slice(0,20)

	for cur_item in activity_list:
		if cur_item.entry_type == "movies":
			object_list.append(Movie.query.get(cur_item.id))
		elif cur_item.entry_type == "marks":
			object_list.append(Mark.query.get((cur_item.user_id,cur_item.id)))

	# Build a dictionnary with the average and movies count (global / only in theaters and only at home) for all users
	# We do a dictionnary instead of a global GROUP BY in order to have all users including the one without any mark
	# and also allow an easy access to a specific user which is nice for the dashboard display
	users=User.query.all()

	for cur_user in users:
		try:
			# Fetch the user object and the current average
			avg_query=db.session.query(db.func.avg(Mark.mark).label("average")).filter(Mark.mark!=None,Mark.user_id==cur_user.id).one()
			stats_dict[cur_user.id]={ "user": cur_user, "avg": round(float(avg_query.average),2), "movies_total" : 0, "movies_theaters" : 0, "movies_home": 0 }

		except TypeError:
			# If we are here, that means the user doesn't have an average (Maybe because no mark recorded)
			stats_dict[cur_user.id]={ "user": cur_user, "avg": "N/A",  "movies_total" : 0, "movies_theaters" : 0, "movies_home": 0 }

		# Let's count the movies for each user
		stats_dict[cur_user.id]["movies_total"] = Mark.query.filter(Mark.mark!=None,Mark.user_id==cur_user.id).count()
		stats_dict[cur_user.id]["movies_theaters"] = Mark.query.filter(Mark.mark!=None,Mark.user_id==cur_user.id,Mark.seen_where=="C").count() 
		stats_dict[cur_user.id]["movies_home"] = Mark.query.filter(Mark.mark!=None,Mark.user_id==cur_user.id,Mark.seen_where=="M").count() 

	# Fetch general databases statistics
	general_stats["movies"] = Movie.query.count()

	# Generate datas for the bar graph
	cur_year=datetime.now().strftime("%Y")
	
	# Set month in French
	locale.setlocale(locale.LC_ALL, "fr_FR.UTF-8")
	for cur_month in range(1,13,1):
		labels.append(datetime.strptime(str(cur_month), "%m").strftime("%B").decode('utf-8'))
		data["theaters"].append(Mark.query.filter(Mark.mark!=None,Mark.user_id==g.user.id,Mark.user_id==g.user.id,Mark.seen_where=="C",db.func.month(Mark.seen_when)==cur_month,db.func.year(Mark.seen_when)==cur_year).count())
		data["others"].append(Mark.query.filter(Mark.mark!=None,Mark.user_id==g.user.id,Mark.user_id==g.user.id,Mark.seen_where=="M",db.func.month(Mark.seen_when)==cur_month,db.func.year(Mark.seen_when)==cur_year).count())

	# Go back to default locale
	locale.setlocale(locale.LC_ALL,locale.getdefaultlocale())
	
	return render_template('show_dashboard.html', object_list=object_list, general_stats=general_stats,labels=labels,data=data,cur_year=cur_year,stats_dict=stats_dict)

@app.route('/dt')
def dt_test():
	return render_template('dt_test.html')
