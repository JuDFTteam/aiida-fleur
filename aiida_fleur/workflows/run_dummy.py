# -*- coding: utf-8 -*-
###############################################################################
# Copyright (c), Forschungszentrum Jülich GmbH, IAS-1/PGI-1, Germany.         #
#                All rights reserved.                                         #
# This file is part of the AiiDA-FLEUR package.                               #
#                                                                             #
# The code is hosted on GitHub at https://github.com/broeder-j/aiida-fleur    #
# For further information on the license, see the LICENSE.txt file            #
# For further information please visit http://www.flapw.de or                 #
# http://aiida-fleur.readthedocs.io/en/develop/                               #
###############################################################################

# import dummy_wc from where ever it is
from aiida_fleur.workflows.dummy import dummy_wc
from pprint import pprint
from aiida.orm.data.base import Str
from aiida.work.run import submit

input_s = Str('hello world!')


res = dummy_wc.run(str_display=input_s)

# if you check the output nodes of the submit run, there will be none
res1 = submit(dummy_wc, str_display=input_s)

#res2 = async(dummy_wc, str_display=input_s)
