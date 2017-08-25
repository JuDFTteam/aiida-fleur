#!/usr/bin/env python
# -*- coding: utf-8 -*-

def gcd(x, y):
    """
    greatest common divisor
    """
    while y != 0:
        (x, y) = (y, x % y)
    return x

def decide_ncore(nkpoints, ncore):
    """
    For kpoint para the number of cores used must be devidebale
    """
    ncore_new = gcd(nkpoints, ncore)
    ncore_list = list(range(ncore_new, ncore+1))
    #print ncore_list
    for noc in ncore_list:
        remain = nkpoints % noc
        #print remain
        if not(remain):
            ncore_new = noc
    return ncore_new
