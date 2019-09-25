'sqa_ref': [0.7, 0.7],                      # set SQA for the reference calculation
'use_soc_ref': False,                       # True, if include SOC terms into the reference calculation
'input_converged' : False,                  # True, if input charge density is converged
'fleur_runmax': 10,                         # needed for SCF
'sqas_theta': [0.0, 1.57079, 1.57079],      # sets SOC theta values
'sqas_phi': [0.0, 0.0, 1.57079],            # sets SOC phi values
'alpha_mix': 0.05,                          # sets mixing parameter alpha
'density_converged': 0.00005,               # needed for SCF
'serial': False,                            # needed for SCF
'itmax_per_run': 30,                        # needed for SCF
'soc_off': [],                              # switches off SOC on a given atom
'inpxml_changes': [],                       # needed for SCF