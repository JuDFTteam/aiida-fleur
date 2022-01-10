# -*- coding: utf-8 -*-
'fleur_runmax': 4,                   # Maximum number of fleur jobs/starts
'density_converged': 0.00002,        # Charge density convergence criterion
'energy_converged': 0.002,           # Total energy convergence criterion
'force_converged': 0.002,            # Largest force convergence criterion
'mode': 'density',                   # Parameter to converge: 'density', 'force' or 'energy'
'add_comp_para': {
    'only_even_MPI': False,          # True if suppress parallelisation having odd number of MPI
    'max_queue_nodes': 20,           # Max number of nodes allowed (used by automatic error fix)
    'max_queue_wallclock_sec': 86400 # Max number of walltime allowed (used by automatic error fix)
    },
'itmax_per_run': 30,                 # Maximum iterations run for one FleurCalculation
'force_dict': {'qfix': 2,            # parameters required for the 'force' mode
               'forcealpha': 0.5,
               'forcemix': 'BFGS'},
'inpxml_changes': [],                # Modifications to inp.xml
