'fleur_runmax': 4,                   # needed for SCF
'alpha_mix': 0.015,                  # Sets alpha mixing parameter
'relax_iter': 5,                     # Maximum number of optimization iterations
'force_criterion': 0.001,            # Sets the threshold of the largest force
'force_converged' : 0.002,           # needed for SCF
'serial' : False,                    # needed for SCF
'force_dict': {'qfix': 2,            # needed for SCF
               'forcealpha': 0.5,
               'forcemix': 'BFGS'},
'film_distance_relaxation' : False,  # Sets relaxXYZ="FFT" for all atoms
'itmax_per_run' : 30,                # needed for SCF
'inpxml_changes' : [],               # needed for SCF