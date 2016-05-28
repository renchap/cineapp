# -*- coding: utf-8 -*-

from flask import render_template,g
from flask.ext.mail import Message
from cineapp import mail, db
from cineapp.models import User
from threading import Thread
from cineapp import app

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
	users = User.query.filter_by(notif_enabled=1).all()
	for cur_user in users:
		# Check if the cur_user is the logged user who added the movie
		# in order to change the mail text
		if cur_user.id==g.user.id:
			you_user=True
		else:
			you_user = False
	
		send_email('[Cineapp] - Ajout d\'un film' , app.config['MAIL_SENDER'],[ cur_user.email ] ,
		render_template('add_movie_notification.txt', dest_user=cur_user, add_user=g.user,movie=movie,you_user=you_user))

# Function which sends notifications to users when a movie is added
def mark_movie_notification(mark,notif_type):
	users = User.query.filter_by(notif_enabled=1).all()
	for cur_user in users:
		# Check if the cur_user is the logged user who added the movie
		# in order to change the mail text
		if cur_user.id==g.user.id:
			you_user=True
		else:
			you_user=False

		if notif_type == "add":	
			send_email('[Cineapp] - Note d\'un film' , app.config['MAIL_SENDER'],[ cur_user.email ] ,
			render_template('mark_movie_notification.txt', dest_user=cur_user, add_user=g.user,mark=mark,you_user=you_user,notif_type=notif_type))
		elif notif_type == "update":
			send_email('[Cineapp] - Note mise à jour' , app.config['MAIL_SENDER'],[ cur_user.email ] ,
			render_template('mark_movie_notification.txt', dest_user=cur_user, add_user=g.user,mark=mark,you_user=you_user,notif_type=notif_type))

# Function which sends notification to user who received an homework
def add_homework_notification(mark):
	# For the homework, just send a mail to the user who has to handle the homework.

	# Check if notifications are enabled for the destination user
	if mark.user.notif_enabled == True:
		try:
			send_email('[Cineapp] - Attribution d\'un devoir', app.config['MAIL_SENDER'],[ mark.user.email ],
			render_template('add_homework_notification.txt', dest_user=mark.user, homework_who=mark.homework_who_user, movie=mark.movie))
			return 0
		except:
			return 1
	else:
		return 2
