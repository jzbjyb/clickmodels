# -*- coding: utf-8 -*-

import re
from collections import defaultdict, namedtuple
from util import SessionLineItem

MAX_SPAN_IN_SECOND = 300 # 3 min, that is only if two logs within 3 min of a <uid, query> do the two log belong to same session 
MAX_DOC_PER_QUERY = 20
TIEM_SAPN = [24, 60, 60]
REGEX = {
	'TIME': re.compile('^\d{2}:\d{2}:\d{2}$'),
}
'''
used to store all the query and corresponding urls in a small time span
structure: time key --(dict map)--> query str --(list index)--> url
'''
QUERY_AGG_BY_TIME = defaultdict(lambda: defaultdict(lambda: [None] * MAX_DOC_PER_QUERY))


'''
used to store all the uid(cookie) and corresponding querys
structure: uid --(dict map)--> query --(list index)--> session list
'''
SESSION_AGG = defaultdict(lambda: defaultdict(lambda: []))

'''
used to store one line in SougouQ 2008 query log
note that the 'rank' and 'clickseq' is one-based index
'''
LineItem = namedtuple('LineItem', ['time', 'uid', 'query', 'rank', 'clickseq', 'url'])


def search(query_agg, query, timekey):
	for sk in [timekey] + range(timekey - 10, timekey) + range(timekey + 1, timekey + 11):
		if query_agg.has_key(sk) and query_agg[sk].has_key(query):
			return query_agg[sk][query]
	return None

def agg(query_agg, span):
	for tk in query_agg:
		query_map1 = query_agg[tk]
		for tks in xrange(tk + 1, tk + span):
			if not query_agg.has_key(tks):
				continue
			query_map2 = query_agg[tks]
			for q in query_map2:
				if not query_map1.has_key(q):
					continue
				# synchronize url list
				for i in xrange(MAX_DOC_PER_QUERY):
					if query_map1[q][i] is None and query_map2[q][i] is not None:
						query_map1[q][i] = query_map2[q][i]
					elif query_map1[q][i] is not None and query_map2[q][i] is None:
						query_map2[q][i] = query_map1[q][i]

def parse_time(time_str):
	if time_str is None or time_str is '':
		return None
	if REGEX['TIME'].match(time_str) is None:
		return None
	ts = time_str.split(':')
	timestemp = 0
	tspan = TIEM_SAPN[-len(ts):]
	for t in xrange(len(ts)):
		timestemp = timestemp * tspan[t] + int(ts[t])
	return timestemp

def getkey_by_time(timestemp, slot = 60):
	# each slot span 1 minutes
	return timestemp / slot

def parse_line(line):
	ls = line.split('\t')
	if len(ls) != 5:
		return None
	time = parse_time(ls[0])
	if time is None:
		return None
	return LineItem(time, ls[1], ls[2][1:-1], int(ls[3].split(' ')[0]), int(ls[3].split(' ')[1]), ls[4])

def trans_sougou(filename, newfilename):
	start_time, end_time = [None] * 2
	# read all log
	with open(filename, 'r') as file:
		for line in file:
			line = line.decode('gbk').encode('utf-8').strip()
			if line is '':
				continue
			li = parse_line(line)
			if li is None:
				print line
				continue
			if li.rank <= MAX_DOC_PER_QUERY:
				QUERY_AGG_BY_TIME[getkey_by_time(li.time)][li.query][li.rank-1] = li.url
				if len(SESSION_AGG[li.uid][li.query]) > 0 and li.time - SESSION_AGG[li.uid][li.query][-1][2] <= MAX_SPAN_IN_SECOND :
					# same session
					SESSION_AGG[li.uid][li.query][-1][0][li.rank-1] = li.url
					SESSION_AGG[li.uid][li.query][-1][1][li.rank-1] = True
					SESSION_AGG[li.uid][li.query][-1][2] = li.time
				else:
					# new session
					SESSION_AGG[li.uid][li.query].append([[None] * MAX_DOC_PER_QUERY, [False] * MAX_DOC_PER_QUERY, li.time])
					SESSION_AGG[li.uid][li.query][-1][0][li.rank-1] = li.url
					SESSION_AGG[li.uid][li.query][-1][1][li.rank-1] = True
	# agg all log 
	agg(QUERY_AGG_BY_TIME, 10)
	# complement session with unclicked urls
	with open(newfilename, 'w') as file:
		for uid in SESSION_AGG:
			for query in SESSION_AGG[uid]:
				for session in SESSION_AGG[uid][query]:
					urls = search(QUERY_AGG_BY_TIME, query, getkey_by_time(session[2]))
					for i in xrange(MAX_DOC_PER_QUERY):
						if session[1][i] is False:
							session[0][i] = urls[i]
					# gen tuple in output format
					os = SessionLineItem(uid + '#' + query + '#' + str(session[2]), \
										query, 0, session[0], [False] * MAX_DOC_PER_QUERY, session[1])
					file.write(' '.join([str(it) for it in os]) + '\n')