# -*- coding: utf-8 -*-

from flask import render_template,g
from flask.ext.mail import Message
from app import mail, db
from .models import User
from config import MAIL_SENDER

# Wrapper function for sending mails using flask-mail plugin
def send_email(subject, sender, recipients, text_body):
    msg = Message(subject, sender=sender, recipients=recipients)
    msg.body = text_body
    mail.send(msg)

def add_movie_notification(movie):
	users = User.query.all()
	you_user = False
	for cur_user in users:
		# Check if the cur_user is the logged user who added the movie
		# in order to change the mail text
		if cur_user.id==g.user.id:
			you_user=True
	
		send_email('[Cineapp] - Ajout d\'un film' , MAIL_SENDER,[ cur_user.email ] ,
		render_template('add_movie_notification.txt', dest_user=cur_user, add_user=g.user,movie=movie,you_user=you_user))
