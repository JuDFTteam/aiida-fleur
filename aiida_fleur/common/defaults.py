# -*- coding: utf-8 -*-
###############################################################################
# Copyright (c), Forschungszentrum Jülich GmbH, IAS-1/PGI-1, Germany.         #
#                All rights reserved.                                         #
# This file is part of the AiiDA-FLEUR package.                               #
#                                                                             #
# The code is hosted on GitHub at https://github.com/JuDFTteam/aiida-fleur    #
# For further information on the license, see the LICENSE.txt file            #
# For further information please visit http://www.flapw.de or                 #
# http://aiida-fleur.readthedocs.io/en/develop/                               #
###############################################################################
'''
Here default values are collected.
Meaning is to centralize the defaults throughout the plugin more, to allow in the
end that the user might be able to specify them in a file he provides
'''
default_options = {
    'resources': {
        'num_machines': 1,
        'num_mpiprocs_per_machine': 1
    },
    'max_wallclock_seconds': 6 * 60 * 60,
    'queue_name': '',
    'custom_scheduler_commands': '',
    'import_sys_environment': False,
    'environment_variables': {}
}
