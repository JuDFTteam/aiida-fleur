# -*- coding: utf-8 -*-
{
    'configurations': {'all-Nd-3': [[(1,1,1,1,0,0,0),       #Lists of used configurations
                                     (1,1,1,0,1,0,0),       #for all LDA+U orbitals and spin
                                     ...],
                                    [(0,0,0,0,0,0,0),
                                     (0,0,0,0,0,0,0),
                                     ...]]},
    'total_energy': [
        -38166.542950054,
        -38166.345602746,
        ...
    ],
    'total_energy_units': 'Htr',
    'distance_charge': [
        0.000001,
        0.0000023,
        ...
    ],
    'distance_charge_units': 'me/bohr^3',
    'successful_configs': [0,1,2,3,...],                   #Which configurations successfully converged
    'non_converged_configs': [],                           #Which configurations did not converge
    'failed_configs': [],                                  #Which configurations failed for another reason
    'info': [],
    'warnings': [],
    'errors': [],
    'workflow_name': 'FleurOrbControlWorkChain',
    'workflow_version': '0.1.0'
}
