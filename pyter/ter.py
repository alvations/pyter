# -*- coding:utf-8 -*-
from __future__ import division
# TODO: __future__ syntax will work forever?
""" Copyright (c) 2011 Hiroyuki Tanaka. All rights reserved."""

import itertools as itrt
import difflib

__all__ = []

__all__ += ['diff_align']
def diff_align(ref, hyp, wordmatch=True):
    """ aligning via difflib's SequenceMatcher
    this method is utility.
    """
    s = difflib.SequenceMatcher()
    if wordmatch:
        ref = ref.split()
        hyp = hyp.split()
    s.set_seqs(ref, hyp)
    ## re formulate to string index
    if wordmatch:
        aligns = [(sum(len(x) + 1 for x in ref[:y]),
                   sum(len(x) + 1 for x in hyp[:z]),
                   sum(len(x) + 1 for x in ref[y:y + w]) - 1)
                   for y, z, w in s.get_matching_blocks()]
        return aligns[:-1]
    else:
        return list(map(tuple, s.get_matching_blocks()))[:-1]


__all__ += ['pretty_print']
def pretty_print(ref, hyp, aligns):
    newref = ''
    newhyp = ''
    l = [(0, 0, 0)] + aligns
    for s, e in zip(l[:-1], l[1:]):
        rlen = _tospace(ref[s[0]:e[0]])
        hlen = _tospace(hyp[s[1]:e[1]])
        if s[2] > 0:
            newref += ref[s[0]:s[0] + s[2]] + ' ' + ref[s[0] + s[2]:e[0]] + ' '
            newhyp += hyp[s[1]:s[1] + s[2]] + ' ' + hyp[s[1] + s[2]:e[1]] + ' '
        else:
            newref += ref[s[0]:e[0]] + ' '
            newhyp += hyp[s[1]:e[1]] + ' '
        if rlen > hlen:
            newhyp += ' ' * (rlen - hlen)
        elif hlen > rlen:
            newref += ' ' * (hlen - rlen)
    return newref[:-1], newhyp[:-1]


def _tospace(s):
    r = 0
    for c in s:
        r += 2 if ord(c) > 255 else 1
    return r

__all__ += ['align']
def align(ref, hyp, wordmatch=True):
    """ aligning via Translation Error Rate matching algorithm.
    TODO: Input must be unicode when Python2.x. No Warning or Error occured.
    >>> align('A B C D E F', 'E F A C D B')
    [(0, 4, 1), (2, 10, 1), (4, 6, 3), (8, 0, 3)]
    """
    ref = _str2list(ref, wordmatch)
    hyp = _str2list(hyp, wordmatch)
    if len(ref) > len(hyp):
        hyp += [''] * (len(ref) - len(hyp))
    dist = lambda x, y: edit_distance(x, list(filter(None, y)))
    ## prepare align
    h = hyp
    marks = {}
    replaced_map = list(range(len(hyp)))  ## trace replacing
    while True:
        ## find the alignment
        scores = []
        for csr, sp, ep in _iter_matches(ref, h):
            nhyp = h[:sp] + h[ep:]
            nhyp = nhyp[:csr] + h[sp:ep] + nhyp[csr:]
            scores.append((dist(ref, nhyp), nhyp, csr, sp, ep))
        if not scores:
            break
        scores.sort()
        scores = [x for x in scores if  x[0] == scores[0][0]]
        scores.sort(key=lambda x: x[4] - x[3], reverse=True)
        prescore = dist(ref, h)
        if scores[0][0] >= prescore:
            break
        # post scoreing
        h = scores[0][1]
        csr, sp, ep = scores[0][2:]
        hyp_mark = replaced_map[sp:ep]
        nrmap = replaced_map[:sp] + replaced_map[ep:]
        nrmap = nrmap[:csr] + replaced_map[sp:ep] + nrmap[csr:]
        replaced_map = nrmap
        marks[csr] = hyp_mark
    ## do align
    aligns = [(x, y[0], len(y)) for x, y in marks.items()]
    hyp_indexes = set(range(len(hyp)))
    for _, l in marks.items():
        hyp_indexes -= set(l)
    hyp_indexes = sorted(list(hyp_indexes))
    sp = 0
    while sp < len(ref):
        if sp in marks:
            sp += len(marks[sp])
            continue
        # 最初にhyp_indexesにヒットするindexは
        h_sp = None
        for idx in (i for i, x in enumerate(hyp) if x == ref[sp]):
            if idx in hyp_indexes:
                h_sp = idx
                break
        if h_sp is None:
            sp += 1
            continue
        for h_ep in range(h_sp + 1, len(hyp) + 1):
            if h_ep == len(hyp) or sp + h_ep - h_sp >= len(ref) or hyp[h_ep] != ref[sp + h_ep - h_sp]:
                aligns.append((sp, h_sp, h_ep - h_sp))
                sp += h_ep - h_sp
                break
        else:
            assert(False)  # must not come here
    aligns.sort()
    ## re formulate to string index
    if wordmatch:
        aligns = [(sum(len(x) + 1 for x in ref[:y]),
                   sum(len(x) + 1 for x in hyp[:z]),
                   sum(len(x) + 1 for x in ref[y:y + w]) - 1)
                   for y, z, w in aligns]
    return aligns

__all__ += ['ter']
def ter(ref, hyp, wordmatch=True):
    """Calcurate Translation Error Rate
    if wordmatch is True, input sentences are regarded as space separeted word sequence.
    else, input sentences are matched with each characters.
    TODO: Input must be unicode when Python2.x. No Warning or Error occured.
    >>> ref = 'SAUDI ARABIA denied THIS WEEK information published in the AMERICAN new york times'
    >>> hyp = 'THIS WEEK THE SAUDIS denied information published in the new york times'
    >>> '%.3f' % ter(ref, hyp)
    '0.308'
    """
    ref = _str2list(ref, wordmatch)
    hyp = _str2list(hyp, wordmatch)
    ed = FastEditDistance(ref)
    return _ter(ref, hyp, ed)
    # return _ter(ref, hyp, lambda x: edit_distance(ref, x))


__all__ += ['ter_glue']
def ter_glue(ref, hyp, wordmatch=True):
    """ When len(ref) > len(hyp), ter cannnot shift the words of ref[len(hyp):].
    ter_glue allow to add the "glue" in to the hyp, and remove this limitation.
    TODO: Input must be unicode when Python2.x. No Warning or Error occured.
    >>> ref = 'SAUDI ARABIA denied THIS WEEK information published in the AMERICAN new york times'
    >>> hyp = 'THIS WEEK THE SAUDIS denied information published in the new york times'
    >>> ter_glue(ref, hyp) == ter(ref, hyp)
    True
    """
    ref = _str2list(ref, wordmatch)
    hyp = _str2list(hyp, wordmatch)
    if len(ref) > len(hyp):
        hyp += [''] * (len(ref) - len(hyp))
    mtd = lambda x: edit_distance(ref, list(filter(None, x)))
    return _ter(ref, hyp, mtd)


def _str2list(s, wordmatch=True):
    """ Split the string into list """
    return s.split(' ') if wordmatch else list(s)


def _ter(ref, hyp, mtd):
    """ Translation Erorr Rate core function """
    err = 0
    while True:
        (delta, hyp) = _shift(ref, hyp, mtd)
        if not delta < 0:
            break
        err += 1
    return (err + mtd(hyp)) / len(ref)


def _shift(ref, hyp, mtd):
    """ Shift the phrase pair most reduce the edit_distance
    Return True shift occurred, else False.
    """
    pre_score = mtd(hyp)
    scores = []
    for csr, sp, ep in _iter_matches(ref, hyp):
        nhyp = hyp[:sp] + hyp[ep:]
        nhyp = nhyp[:csr] + hyp[sp:ep] + nhyp[csr:]
        scores.append((mtd(nhyp), nhyp))
    if not scores:
        return (0, hyp)
    scores.sort()
    return (scores[0][0] - pre_score, scores[0][1]) if scores[0][0] < pre_score else (0, hyp)


def _iter_matches(ref, hyp):
    """ yield the tuple of (ref_start_point, hyp_start_point, hyp_end_point)
    for all possible shiftings.
    """
    # refの位置に置き換えるのだから、短い方のsequenceに合わせる
    maxlen = min(len(ref), len(hyp))
    for csr in range(maxlen):
        # already aligned
        if ref[csr] == hyp[csr]:
            continue
        # search start point
        for sp in range(maxlen):
            if csr != sp and ref[csr] == hyp[sp]:
                # found start point of matched phrase
                for ep in range(sp + 1, maxlen + 1):
                    if ep == maxlen or csr + ep - sp == len(ref) or ref[csr + ep - sp] != hyp[ep]:
                        yield (csr, sp, ep)
                        break
                else:
                    # must break
                    assert(False)


__all__ += ['edit_distance']
def edit_distance(s, t):
    """It's same as the Levenshtein distance"""
    l = _gen_matrix(len(s) + 1, len(t) + 1, None)
    l[0] = [x for x, _ in enumerate(l[0])]
    for x, y in enumerate(l):
        y[0] = x
    for i, j in itrt.product(range(1, len(s) + 1), range(1, len(t) + 1)):
        l[i][j] = min(l[i - 1][j] + 1,
                      l[i][j - 1] + 1,
                      l[i - 1][j - 1] + (0 if s[i - 1] == t[j - 1] else 1))
    return l[-1][-1]


def _gen_matrix(col_size, row_size, default=None):
    return [[default for _ in range(row_size)] for __ in range(col_size)]


import bisect

__all__ += ['FastEditDistance']
class FastEditDistance(object):
    """<Experimental> Cached edit distance to calculate similar two strings.
    ref and hyp must be list or string, not generetor.
    Cache stored input hypothesis with each elements.
    """
    def __init__(self, ref):
        self.ref = ref
        self.cache_keys = []
        self.cache_value = []
        self.trivial_list = [list(range(len(ref) + 1))]

    def __call__(self, hyp):
        condition, resthyp = self._find_cache(hyp)
        new_cache, score = self._edit_distance(resthyp, condition)
        self._add_cache(new_cache, hyp)
        return score

    def _find_cache(self, hyp):
        """find longest common prefix, and return prefix of hit cache
        """
        idx = bisect.bisect_left(self.cache_keys, hyp)
        cplen_pre = 0 if idx == 0 else self._common_prefix_index(self.cache_keys[idx - 1], hyp)
        cplen_pos = 0 if idx == len(self.cache_keys) else self._common_prefix_index(self.cache_keys[idx], hyp)
        if cplen_pre > cplen_pos:
            return self.cache_value[idx - 1][:cplen_pre + 1], hyp[cplen_pre:]
        elif cplen_pre < cplen_pos:
            return self.cache_value[idx][:cplen_pos + 1], hyp[cplen_pos:]
        elif cplen_pre > 0:
            return self.cache_value[idx - 1][:cplen_pre + 1], hyp[cplen_pre:]
        return  self.trivial_list, hyp

    def _add_cache(self, ncache, s):
        """insert cache with sorted order, using binary search
        """
        idx = bisect.bisect_left(self.cache_keys, s)
        if idx < len(self.cache_keys) - 1 and self.cache_keys[idx + 1] == s:
            return              # don't have to add
        self.cache_keys.insert(idx, s)
        self.cache_value.insert(idx, ncache)

    def _common_prefix_index(self, s, t):
        """ Return end of common prefix index.
        """
        r = 0
        for i in range(min(len(s), len(t))):
            if s[i] != t[i]:
                break
            r += 1
        return r

    def _edit_distance(self, hyp, cond):
        """ calculate edit distance.
        """
        offset = len(cond)
        l = cond + [[None for _ in range(len(self.ref) + 1)] for __ in range(len(hyp))]
        for i, j in itrt.product(range(offset, offset + len(hyp)), range(len(self.ref) + 1)):
            if j == 0:
                l[i][j] = l[i - 1][j] + 1
            else:
                l[i][j] = min(l[i - 1][j] + 1,
                              l[i][j - 1] + 1,
                              l[i - 1][j - 1] + (0 if hyp[i - offset] == self.ref[j - 1] else 1))
        return l, l[-1][-1]
