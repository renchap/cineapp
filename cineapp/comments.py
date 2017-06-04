# -*- coding: utf-8 -*-

from cineapp import app, db, lm
from flask import render_template, flash, redirect, url_for, g, request, session, jsonify
from flask.ext.login import login_required
from cineapp.models import User, MarkComment
from datetime import datetime

@app.route('/json/add_mark_comment', methods=['POST'])
@login_required
def add_mark_comment():

	# Fetch the important informations we need to fill the chat message object
	comment = request.form["comment"]
	dest_user = request.form["dest_user"]
	movie_id = request.form["movie_id"]

	# Create the chat_message object
	mark_comment=MarkComment()
	mark_comment.user_id = g.user.id
	mark_comment.mark_user_id = dest_user
	mark_comment.mark_movie_id = movie_id
	mark_comment.posted_when = datetime.now()
	mark_comment.message = comment

	# Add the object into the database
	try:
		db.session.add(mark_comment)
		db.session.commit()
			
		# TODO : DO BETEER REALLY !!!!
		mark_comment.posted_when = mark_comment.posted_when.strftime('%Y-%m-%d %H:%M:%S')
			
	except IntegrityError:
		db.session.rollback()

	# Build the dict we're going to send to the frontend
	data_dict = { "user": g.user.serialize(), "mark_comment": mark_comment.serialize(), "mark_comment_number": MarkComment.query.filter(MarkComment.mark_user_id==dest_user,MarkComment.mark_movie_id==movie_id).count()}

	# Let's send the JSON Response to the frontend
	return jsonify(data_dict)
