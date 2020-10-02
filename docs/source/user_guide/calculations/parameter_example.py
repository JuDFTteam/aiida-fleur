# -*- coding: utf-8 -*-
Cd = Dict(dict={
    'atom':{'element' : 'Cd', 'rmt' : 2.5, 'jri' : 981, 'lmax' : 12,
            'lnonsph' : 6, 'lo' : '4d',
            'econfig' : '[Ar] 4s2 3d10 4p6 | 4d10 5s2'},
    'comp': {'kmax': 4.7, 'gmaxxc' : 12.0, 'gmax' : 14.0},
    'kpt': {'div1' : 17, 'div2': 17, 'div3' : 17, 'tkb' : 0.0005}})

# Magnetism and spin orbit coupling
Cr = Dict(dict={
    'atom1':{'element' : 'Cr', 'id': '24.0', 'rmt' : 2.1, 'jri' : 981,
             'lmax' : 12, 'lnonsph' : 6, 'lo' : '3s 3p', 'bmu':1.5},
    'atom2':{'element' : 'Cr', 'id': '24.1', 'rmt' : 2.1, 'jri' : 981,
             'lmax' : 12, 'lnonsph' : 6, 'lo' : '3s 3p', 'bmu':1.4},
    'comp': {'kmax': 5.2, 'gmaxxc' : 12.5, 'gmax' : 15.0},
    'kpt': {'div1' : 24, 'div2': 24, 'div3' : 24, 'tkb' : 0.0005},
    'soc' : {'theta' : 0.0, 'phi' : 0.0}})
