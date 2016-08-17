# -*- coding: utf-8 -*-
from cineapp import app

@app.template_filter()
def minutes_to_human_duration(minutes_duration):
	"""
		Convert a duration in minutes into a duration in a cool format human readable
	"""
	try:
		hours,minutes = divmod(minutes_duration,60)
		return "%sh %smin" %(hours,minutes)
	except TypeError:
		return None

@app.template_filter()
def date_format(date,format_date):
	"""
		Convert a date object into a custom format
	"""
	return date.strftime(format_date)
