"""Helper for regenerating inp.xml files
"""
from aiida import load_profile

load_profile()

from aiida.orm import load_node
from aiida.engine import run
from aiida.plugins import CalculationFactory
from aiida_fleur.data.fleurinp import FleurinpData

inpgenc = CalculationFactory('fleur.inpgen')
path = './inp.xml'

fleurinp = FleurinpData(inpxml=path)

struc = fleurinp.get_structuredata_ncf()
param = fleurinp.get_parameterdata_ncf()
inpgen_code = load_node()

runa = run(inpgenc, code=inpgen_code, structure=struc, calc_parameter=param)
