# -*- coding: utf-8 -*-

from flask import render_template,g
from flask.ext.mail import Message
from app import mail, db
from .models import User
from config import MAIL_SENDER
from threading import Thread
from app import app

# Send mail into a dedicated thread in order to avoir the web app to wait
def send_async_email(app, msg):
    with app.app_context():
        mail.send(msg)

# Wrapper function for sending mails using flask-mail plugin
def send_email(subject, sender, recipients, text_body):
    msg = Message(subject, sender=sender, recipients=recipients)
    msg.body = text_body
    thr = Thread(target=send_async_email, args=[app, msg])
    thr.start()

# Function which sends notifications to users when a movie is added
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
