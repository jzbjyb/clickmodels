# -*- coding: utf-8 -*-

from .inference import ClickModel
from .config_sample import MAX_ITERATIONS, DEBUG, PRETTY_LOG, MAX_DOCS_PER_QUERY, SERP_SIZE, TRANSFORM_LOG, QUERY_INDEPENDENT_PAGER, DEFAULT_REL

import time
import sys
import math
from collections import defaultdict

DEFAULT_REDUNDANCY = 0.5
DEFAULT_USEINFO = True

class N_UbmModel(ClickModel):
    def __init__(self, ignoreIntents=True, ignoreLayout=True, param=None, config=None):
        ClickModel.__init__(self, ignoreIntents, ignoreLayout, config)
        self.param = {} if param is None else param

    def train(self, sessions):
        max_query_id = self.config.get('MAX_QUERY_ID')
        if max_query_id is None:
            print >>sys.stderr, 'WARNING: no MAX_QUERY_ID specified for', self
            max_query_id = 100000
        # alpha: query -> url -> "attractiveness probability"
        self.alpha = [defaultdict(lambda: self.config.get('DEFAULT_REL', DEFAULT_REL)) \
                        for q in xrange(max_query_id)]
        # gamma: rank -> "distance to last click" - 1 -> "examination probability"
        self.gamma = [[0.5 \
            for d in xrange(self.config.get('MAX_DOCS_PER_QUERY', MAX_DOCS_PER_QUERY))] \
                for r in xrange(self.config.get('MAX_DOCS_PER_QUERY', MAX_DOCS_PER_QUERY))]
        # lambdaa: query -> "query informativeness or query intents diversity probability"
        self.lambdaa = [0.0 for q in xrange(max_query_id)]
        # beta: url -> url -> "redundancy probability"
        self.beta = defaultdict(lambda: defaultdict(lambda: DEFAULT_REDUNDANCY))
        
        if not self.config.get('PRETTY_LOG', PRETTY_LOG):
            print >>sys.stderr, '-' * 80
            print >>sys.stderr, 'Start. Current time is', datetime.now()
        # iteration
        for iteration_count in xrange(self.config.get('MAX_ITERATIONS', MAX_ITERATIONS)):
            alphaFractions = [defaultdict(lambda: [1.0, 2.0]) \
						for q in xrange(max_query_id)]
            gammaFractions = [[[1.0, 2.0] \
                for d in xrange(self.config.get('MAX_DOCS_PER_QUERY', MAX_DOCS_PER_QUERY))] \
                    for r in xrange(self.config.get('MAX_DOCS_PER_QUERY', MAX_DOCS_PER_QUERY))]
            lambdaaFractions = [[1.0, 1.0, 1.0, 2.0] for q in xrange(max_query_id)]
            betaFractions = defaultdict(lambda: defaultdict(lambda: [1.0, 2.0]))
            e_s = time.time()
            # E-step
            for s in sessions:
                es_s = time.time()
                query = s.query
                prevClick = -1
                t_l = self.lambdaa[query]
                for rank, c in enumerate(s.clicks):
                    url = s.results[rank]
                    url_preClick = s.results[prevClick] if prevClick >= 0 else None
                    preDist = rank - prevClick - 1
                    t_a = self.alpha[query][url]
                    # the redundancy of pair <u_r, u_0> is 0.5
                    t_b = self.beta[url][url_preClick]
                    t_g = self.gamma[rank][preDist]

                    if c == 1:
                    	alphaFractions[query][url][0] += \
                    		t_a * (t_l * (1-t_b) + 1 - t_l) / (t_l * (1-t_b) + t_a * (1 - t_l))
                    	gammaFractions[rank][preDist][0] += \
                    		1
                    	lambdaaFractions[query][0] *= \
                    		t_g * (1-t_b)
                    	lambdaaFractions[query][1] *= \
                    		t_g * t_a
                    	betaFractions[url][url_preClick][0] += \
                    		(1-t_b) * ((1-t_l) * t_a + t_l) / ((1-t_l) * t_a + (1 - t_b) * t_l)
                    else:
                    	alphaFractions[query][url][0] += \
                    		t_a * (1 - t_g * (t_l * (1-t_b) + 1 - t_l)) / (1 - t_g * t_l * (1-t_b) - t_a * t_g * (1 - t_l))
                    	gammaFractions[rank][preDist][0] += \
                    		t_g * (1 - t_l * t_a - (1-t_l) * (1-t_b)) / (1 - t_g * (t_l * t_a + (1-t_l) * (1-t_b)))
                    	lambdaaFractions[query][0] *= \
                    		1 - t_g * (1-t_b)
                    	lambdaaFractions[query][1] *= \
                    		1 - t_g * (1-t_a)
                    	betaFractions[url][url_preClick][0] += \
                    		(1-t_b) * (1 - t_g * ((1-t_l) * t_a + t_l)) / (1 - t_g * (1-t_l) * t_a - t_g * t_l * (1-t_b))
                    
                    alphaFractions[query][url][1] += 1
                    gammaFractions[rank][preDist][1] += 1
                    betaFractions[url][url_preClick][1] += 1
                    if c != 0:
                        prevClick = rank
                lambdaaFractions[query][0] *= t_l
                lambdaaFractions[query][1] *= 1 - t_l
                lambdaaFractions[query][2] += lambdaaFractions[query][0] / (lambdaaFractions[query][0] + lambdaaFractions[query][1])
                lambdaaFractions[query][0] = lambdaaFractions[query][1] = 1
                lambdaaFractions[query][3] += 1
                es_e = time.time()
            if not self.config.get('PRETTY_LOG', PRETTY_LOG):
                sys.stderr.write('E')
            e_e = time.time()

            m_s = time.time()
            # M-step
            sum_square_displacement = 0.0
            # maximize alpha
            for q in xrange(max_query_id):
                for url, aF in alphaFractions[q].iteritems():
                    new_alpha = aF[0] / aF[1]
                    sum_square_displacement += (self.alpha[q][url] - new_alpha) ** 2
                    self.alpha[q][url] = new_alpha
            # maximize gamma
            for r in xrange(self.config.get('MAX_DOCS_PER_QUERY', MAX_DOCS_PER_QUERY)):
                for d in xrange(self.config.get('MAX_DOCS_PER_QUERY', MAX_DOCS_PER_QUERY)):
                    gF = gammaFractions[r][d]
                    new_gamma = gF[0] / gF[1]
                    sum_square_displacement += (self.gamma[r][d] - new_gamma) ** 2
                    self.gamma[r][d] = new_gamma
            # maximize lambdaa
            for q in xrange(max_query_id):
            	lF = lambdaaFractions[q]
            	new_lambdaa = lF[2] / lF[3]
            	sum_square_displacement += (self.lambdaa[q] - new_lambdaa) ** 2
            	self.lambdaa[q] = new_lambdaa
            # maximize beta
            for url, last in betaFractions.iteritems():
           		for preurl, bF in last.iteritems():
           			new_beta = (bF[1] - bF[0]) / bF[1]
           			sum_square_displacement += (self.beta[url][preurl] - new_beta) ** 2
           			# the beta is symmetric
           			self.beta[url][preurl] = self.beta[preurl][url] = new_beta
            m_e = time.time()

            if not self.config.get('PRETTY_LOG', PRETTY_LOG):
                sys.stderr.write('M\n')
            rmsd = math.sqrt(sum_square_displacement)
            if self.config.get('PRETTY_LOG', PRETTY_LOG):
                sys.stderr.write('e %f m %f ' % (e_e-e_s, m_e-m_s))
                sys.stderr.write('%d..' % (iteration_count + 1))
            else:
                print >>sys.stderr, 'Iteration: %d, ERROR: %f' % (iteration_count + 1, rmsd)
        if self.config.get('PRETTY_LOG', PRETTY_LOG):
            sys.stderr.write('\n')

    def _get_click_probs(self, s, possibleIntents):
        """
        Returns clickProbs list
        clickProbs[i][k] = P(C_1, ..., C_k | I=i)
        """
        clickProbs = dict((i, []) for i in possibleIntents)
        firstVerticalPos = -1 if not any(s.layout[:-1]) else [k for (k, l) in enumerate(s.layout) if l][0]
        prevClick = -1
        layout = [False] * len(s.layout) if self.ignoreLayout else s.layout
        for rank, c in enumerate(s.clicks):
            url = s.results[rank]
            url_preClick = s.results[prevClick] if prevClick >= 0 else None
            l = self.lambdaa[s.query]
            prob = {False: 0.0, True: 0.0}
            for i in possibleIntents:
                a = self.alpha[s.query][url]
                g = self.gamma[rank][rank - prevClick - 1]
                b = self.beta[url][url_preClick]
                prevProb = 1 if rank == 0 else clickProbs[i][-1]
                if c == 0:
                    clickProbs[i].append(prevProb * (1 - g * (l * (1-b) + (1-l) * a)))
                else:
                    clickProbs[i].append(prevProb * g * (l * (1-b) + (1-l) * a))
            if c != 0:
                prevClick = rank
        return clickProbs
