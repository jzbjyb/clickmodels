# -*- coding: utf-8 -*-

from collections import namedtuple

'''
used to store one line in the format suit for clickmodels
note that the 'urls', 'presents', 'clicks' are lists with the same length
'''
SessionLineItem = namedtuple('SessionLineItem', ['id', 'query', 'region', 'P_intent', 'urls', 'presents', 'clicks'])

class ParseException(Exception):
	pass