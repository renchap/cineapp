# -*- coding: utf-8 -*-

def frange(start, end, step):
	tmp = start
	while(tmp <= end):
		yield tmp
		tmp += step
