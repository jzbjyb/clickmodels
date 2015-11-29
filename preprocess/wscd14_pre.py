# -*- coding: utf-8 -*-

import re
import os
from collections import defaultdict, namedtuple
from util import SessionLineItem, ParseException

'''
log format: https://www.kaggle.com/c/yandex-personalized-web-search-challenge/details/logs-format
'''
LineItemM = namedtuple('LineItemM', ['session', 'type', 'day', 'user'])
LineItemC = namedtuple('LineItemC', ['session', 'timepass', 'type', 'serp', 'url'])
LineItemQ = namedtuple('LineItemQ', ['session', 'timepass', 'type', 'serp', 'query', 'terms', 'url_domain'])

SerpItem = namedtuple('SerpItem', ['session', 'serp', 'query', 'urls'])

def parse_line(line):
	ls = line.split('\t')
	if len(ls) is 4 and ls[1] is 'M':
		return LineItemM(ls[0], ls[1], int(ls[2]), ls[3])
	elif len(ls) is 5 and ls[2] is 'C':
		return LineItemC(ls[0], int(ls[1]), ls[2], ls[3], ls[4])
	elif len(ls) >= 7 and (ls[2] is 'Q' or ls[2] is 'T'):
		return LineItemQ(ls[0], int(ls[1]), ls[2], ls[3], ls[4], ls[5].split(','), [(ud.split(',')[0], ud.split(',')[1]) for ud in ls[6:]])
	else:
		raise ParseException('%s is unexpected' % line)

def trans_wscd14(filename, newfilename):
	batch = 10000 # session number
	has_next = True
	end = 0
	total_line = 0
	total_session = 0
	while(has_next):
		if total_session >= 100000:
			break
		print 'total read %d lines' % total_line
		print 'total read %d sessions' % total_session
		session_data = defaultdict()
		with open(filename, 'r') as file:
			start = end
			file.seek(start)
			ln = 0
			session_num = 0
			for line in file:
				if session_num >= batch:
					has_next = False
					break
				end += len(line)
				ln += 1
				line = line.strip()
				if line is '':
					continue
				line_item = parse_line(line)
				if line_item.type is 'M':
					session_num += 1
				if line_item.type is 'Q' or line_item.type is 'T':
					key = line_item.session + '#' + line_item.serp
					if not session_data.has_key(key):
						# add new serp
						session_data[key] = SerpItem(line_item.session, line_item.serp, line_item.query, {})
						# flag click as false
						for ud in line_item.url_domain:
							session_data[key].urls[ud[0]] = False
					else:
						print 'woops! multipule serps for same session? %s' % key
				elif line_item.type is 'C':
					key = line_item.session + '#' + line_item.serp
					if session_data.has_key(key):
						# flag click as true
						if session_data[key].urls.has_key(line_item.url):
							session_data[key].urls[line_item.url] = True
						else:
							print 'woops! no url in the same serp? %s %s' %(key, line_item.url)
					else :
						print 'woops! no session serp declared before click? %s' % key
			has_next = not has_next
			total_line += ln
			total_session += session_num
		mod = 'a' if os.path.isfile(newfilename) and start is not 0 else 'w'
		with open(newfilename, mod) as file:
			for serpk in session_data:
				serpv = session_data[serpk]
				so = SessionLineItem(serpv.session + '#' + serpv.serp, serpv.query, 0, 0,  '[' + ', '.join(['"' + u + '"' for u in serpv.urls]) + ']', '[' + ', '.join(['false' for u in serpv.urls]) + ']', [1 if serpv.urls[u] else 0 for u in serpv.urls])
				file.write('\t'.join([str(it) for it in so]) + '\n')

	print 'final total session %d line %d' %(total_session, total_line)