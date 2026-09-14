"""The (structure, calc_parameters) pairs aiida-fleur actually uses, as plain data."""
BOHR_A = 0.5291772108

def si():
    p = 5.43
    return (dict(cell=[[0, p/2, p/2], [p/2, 0, p/2], [p/2, p/2, 0]],
                 sites=[{'position': (0.,0.,0.), 'kind_name': 'Si'},
                        {'position': (p/4, p/4, p/4), 'kind_name': 'Si'}],
                 kinds=[{'symbols': ('Si',), 'weights': (1.,), 'mass': 28.0855, 'name': 'Si'}],
                 pbc=(True, True, True)))

def w():
    a = 3.013812049196 * 0.52917721092
    return dict(cell=[[-a, a, a], [a, -a, a], [a, a, -a]],
                sites=[{'position': (0.,0.,0.), 'kind_name': 'W'}],
                kinds=[{'symbols': ('W',), 'weights': (1.,), 'mass': 183.84, 'name': 'W'}],
                pbc=(True, True, True))

def fept_film():
    a = 7.497 * BOHR_A
    return dict(cell=[[0.7071068*a, 0., 0.], [0., a, 0.], [0., 0., 0.7071068*a]],
                sites=[{'position': (0., 0., -1.99285*BOHR_A), 'kind_name': 'Fe'},
                       {'position': (0.5*0.7071068*a, 0.5*a, 0.), 'kind_name': 'Pt'},
                       {'position': (0., 0., 2.65059*BOHR_A), 'kind_name': 'Pt'}],
                kinds=[{'symbols': ('Fe',), 'weights': (1.,), 'mass': 55.845, 'name': 'Fe'},
                       {'symbols': ('Pt',), 'weights': (1.,), 'mass': 195.084, 'name': 'Pt'}],
                pbc=(True, True, False))

CASES = {
    # tests/workflows/test_scf_workchain.py + test_eos_workchain.py
    'si_scf_regression': (si(), {'atom': {'element': 'Si', 'rmt': 2.1, 'jri': 981,
                                          'lmax': 8, 'lnonsph': 6},
                                 'comp': {'kmax': 3.4},
                                 'kpt': {'div1': 10, 'div2': 10, 'div3': 10, 'tkb': 0.0005}}),
    # a bare structure, no parameters at all
    'si_no_params': (si(), None),
    # tests/calculation/test_inpgen.py
    'w_econfig_lo': (w(), {'atom': {'element': 'W', 'rmt': 2.1, 'jri': 981, 'lmax': 12,
                                    'lnonsph': 6,
                                    'econfig': '[Kr] 4d10 4f14 | 5s2 5p6 6s2 5d4',
                                    'lo': '5s 5p'},
                           'comp': {'kmax': 5.0, 'gmaxxc': 12.5, 'gmax': 15.0},
                           'kpt': {'div1': 3, 'div2': 3, 'div3': 3, 'tkb': 0.0005}}),
    'w_soc_only': (w(), {'soc': {'theta': 0.0, 'phi': 0.0}}),
    # the film the magnetic workchains use
    'fept_film': (fept_film(), {'comp': {'kmax': 4.0}, 'atom': {'element': 'Pt', 'rmt': 2.2}}),
    'fept_film_soc': (fept_film(), {'comp': {'kmax': 4.0},
                                    'soc': {'theta': 0.0, 'phi': 0.0}}),
    # docs/source/user_guide/calculations/parameter_example.py
    'si_docs_example': (si(), {'atom': {'element': 'Si', 'rmt': 2.1, 'jri': 981, 'lmax': 12,
                                        'lnonsph': 6, 'lo': '3s 3p',
                                        'econfig': '[He] 2s2 2p6 | 3s2 3p2'},
                               'comp': {'kmax': 4.7, 'gmaxxc': 12.0, 'gmax': 14.0},
                               'kpt': {'div1': 17, 'div2': 17, 'div3': 17, 'tkb': 0.0005}}),
}
