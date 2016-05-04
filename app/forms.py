# -*- coding: utf-8 -*-

from flask.ext.wtf import Form
from flask.ext.wtf.html5 import SearchField
from wtforms import StringField, PasswordField, RadioField, SubmitField, HiddenField, SelectField, TextAreaField, BooleanField
from wtforms.ext.sqlalchemy.fields import QuerySelectField
from wtforms.validators import DataRequired, EqualTo, Email, URL, ValidationError
from app.models import Origin, Type,User

def get_origins():
	return Origin.query.all()

def get_types():
	return Type.query.all()

def get_users():
	return User.query.all()

class LoginForm(Form):
	username = StringField('username', validators=[DataRequired()])
	password = PasswordField('password', validators=[DataRequired()])

class AddUserForm(Form):
	username = StringField('Nom Utilisateur', [DataRequired()])
	email = StringField('Adresse Email', [DataRequired(), Email(message="Adresse E-Mail Incorrecte")])
	password = PasswordField('Mot de passe',[DataRequired(), EqualTo('confirm',message='Les mots de passe ne correspondent pas')])
	confirm = PasswordField('Confirmation mot de passe')

class AddMovieForm(Form):
	name = StringField('Nom du Film', [DataRequired()])
	director = StringField('Realisateur', [DataRequired()])
	year = StringField('Annee de sortie', [DataRequired()])
	url = StringField('Fiche Allocine')
	origin = QuerySelectField(query_factory=get_origins, get_label='origin')
	type = QuerySelectField(query_factory=get_types,get_label='type')

class MarkMovieForm(Form):
	mark = StringField('Note du Film', [DataRequired()])
	comment = TextAreaField('Commentaire du Film', [DataRequired()])
	seen_where = RadioField('Ou j\'ai vu le film', choices=[('C', u'Cinema'), ('M', 'Maison')], default='M')

	def validate_mark(form,field):
		try:
			float(field.data)
		except ValueError:
			raise ValidationError('Pas un chiffre')
		if float(field.data) < 0 or float(field.data) > 20:
			raise ValidationError('Note Incorrecte')

class SearchMovieForm(Form):
	search = StringField('Nom du film', [DataRequired()])
	submit_search = SubmitField('Chercher')

class SelectMovieForm(Form):
	movie = RadioField('Film', choices=[], coerce=int)
	submit_select = SubmitField('Selectioner')

	# Specific constructer in order to pass a movie list
	def __init__(self,movies_list=[]):
		
		# Call the parent constructor
		super(SelectMovieForm, self).__init__()
		
		# Local variable
		choice_list=[]
		for cur_movie in movies_list:
			choice_list.append((cur_movie['id'], cur_movie['title']))

		self.movie.choices = choice_list

class ConfirmMovieForm(Form):
	origin = QuerySelectField(query_factory=get_origins, get_label='origin')
	type = QuerySelectField(query_factory=get_types,get_label='type')
	movie_id = HiddenField()
	submit_confirm = SubmitField("Ajouter le film")

class FilterForm(Form):
	origin = QuerySelectField('Origine',query_factory=get_origins, get_label='origin',allow_blank=True,blank_text=u'--Pas de filtre--')
	type = QuerySelectField('Type',query_factory=get_types,get_label='type',allow_blank=True,blank_text=u'--Pas de filtre--')
	seen_where = QuerySelectField('Vu au cine par',query_factory=get_users,get_label='nickname',allow_blank=True,blank_text=u'--Pas de filtre--')
	submit_filter = SubmitField("Filtrer")

class UserForm(Form):
	email = StringField('Adresse Email', [DataRequired('Champ Requis'), Email(message="Adresse E-Mail Incorrecte")])
	notif_enabled = BooleanField()
	submit_user = SubmitField("Sauver")

class PasswordForm(Form):
	password = PasswordField('Mot de passe',[DataRequired('Champ Requis'), EqualTo('confirm',message='Les mots de passe ne correspondent pas')])
	confirm = PasswordField('Confirmation mot de passe',[DataRequired('Champ Requis')])
	submit_user = SubmitField("Changer le mot de passe")

class HomeworkForm(Form):
	user_filter = QuerySelectField('Vu au cine par',query_factory=get_users,get_label='nickname',allow_blank=True,blank_text=u'--Pas de filtre--')
	submit_homework = SubmitField('Filtrer')

	# Specific constructor in order to initialize properly the user_filter label
	def __init__(self,label_name=None,*args,**kwargs):
		
		# Call the parent constructor
		super(HomeworkForm, self).__init__(*args,**kwargs)

		self.user_filter.label.text=label_name
