# -*- coding: utf-8 -*-

from flask.ext.wtf import Form
from wtforms import StringField, PasswordField
from wtforms.ext.sqlalchemy.fields import QuerySelectField
from wtforms.validators import DataRequired, EqualTo, Email, URL, ValidationError
from app.models import Origin, Type

def get_origins():
	return Origin.query.all()

def get_types():
	return Type.query.all()

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
	comment = StringField('Commentaire du Film', [DataRequired()])
	seen_where = StringField('Ou j\'ai vu le film', [DataRequired()])

	def validate_mark(form,field):
		try:
			int(field.data)
		except ValueError:
			raise ValidationError('Pas un chiffre')
		if int(field.data) < 0 or int(field.data) > 20:
			raise ValidationError('Note Incorrecte')
