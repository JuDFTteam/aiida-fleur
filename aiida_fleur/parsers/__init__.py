# -*- coding: utf-8 -*-
'''
FLEUR plug-in
'''

from aiida.parsers.exceptions import OutputParsingError

__copyright__ = u"Copyright (c), 2016-2017, Forschungszentrum Jülich GmbH, IAS-1/PGI-1, Germany. All rights reserved."
__license__ = "MIT license, see LICENSE.txt file"
__contributors__ = "Jens Broeder"
__paper__ = ""
__paper_short__ = ""


#mainly created this Outputparsing error, that the user sees, that it comes from parsing a fleur calculation.
class FleurOutputParsingError(OutputParsingError):
    pass
    # if you want to do something special here do it
