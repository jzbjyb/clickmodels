#!/usr/bin/env python
#coding: utf-8

from preprocess.sougou_pre import trans_sougou
from preprocess.wscd14_pre import trans_wscd14

import sys

if __name__ == '__main__':
	func = {
		'sougou08': trans_sougou,
		'wscd14': trans_wscd14
	}
	func[sys.argv[1]](sys.argv[2], sys.argv[3])