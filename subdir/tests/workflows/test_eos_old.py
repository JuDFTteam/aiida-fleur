#!/usr/bin/env python
# -*- coding: utf-8 -*-
import numpy as np
from matplotlib.backends import _macosx
import matplotlib.pyplot as pp

from matplotlib.font_manager import FontProperties
from scipy.optimize import curve_fit
from pprint import pprint
from aiida import load_dbenv, is_dbenv_loaded
if not is_dbenv_loaded():
    load_dbenv()
from aiida.orm.querybuilder import QueryBuilder as QB
from aiida.orm import Node, User, DataFactory, Calculation, Computer, Code
from aiida.orm import load_node

from aiida.tools.codespecific.fleur.StructureData_util import eos_structures
from aiida.tools.codespecific.fleur.convergence import fleur_convergence
from aiida.tools.codespecific.fleur.calculate_lattice_con import lattice_constant
from aiida.tools.codespecific.fleur.convergence import fleur_convergence

from aiida.workflows2.run import async, run

ParameterData = DataFactory('parameter')

W_bcc_id = 24513#24423
W_bcc_id2 = 24422
W_fcc_id = 24

W_bcc = load_node(W_bcc_id)
print 'StructureData used:\n{}'.format(W_bcc)
print 'cell: {}\n'.format(W_bcc.cell)
print 'sites: {}\n'.format(W_bcc.sites)

# create a Parameternode or load one from the DB
W_para_id = 24507#without soc soc:24424
W_para = load_node(W_para_id)

print 'ParamterNode used:'
pprint(W_para.get_dict())

###############################
# Set your values here
codename = 'inpgen_mac_25_10_2016'
computer_name = 'local_mac'
#computer_name = 'iff003'
codename2 = 'fleur_mac_v0_27'
#codename2 = 'fleur_iff003_v0_27@iff003'
#codename2 = 'fleur_MPI_iff003_v0_27@iff003'
points = 3#9
step = 0.002
guess = 1.01
wf_dict = {'fleur_runmax' : 2, 'density_criterion' : 0.0000001, 'points' : points, 'step' : step, 'guess' : guess}
###############################

code = Code.get_from_string(codename)
code2 = Code.get_from_string(codename2)
computer = Computer.get(computer_name)
wf_para = ParameterData(dict=wf_dict)

#res = run(lattice_constant, wf_parameters=wf_para, structure=W_bcc,
#                calc_parameters=W_para, inpgen = code, fleur=code2)

#print res
'''
# other tests:
yfit_all = []
def func(x, a, b, c):
    return a*x**2 + b*x + c

def fit_latticeconstant(scale, eT):
    """
    """
    import numpy as np
    # call fitt pol2 # or something else
    #def func(x, a, b, c):
    #    return a*x**2 + b*x + c
    f1 = np.polyfit(scale,eT,2)
    a0 = f1[0]
    a1 = f1[1]
    a2 = f1[2]
    la = -0.5*a1/a0
    c = a2 - a1**2/a2
    return a0,la,c, f1

scale = [-1, 0, 1, 2, 3]
eT = [1.02, 0.03, 1.03, 4.02, 9.02]

a0,la,c, f1 = fit_latticeconstant(scale, eT)

print a0, la, c, f1
scaleAll.append(scale)
eT1_all.append(eT)
yfit = func(scale,a0,a1,a2)
yfit_all.append(yfit)

#### plot

nfiles = 1
save = False
labela = ['bla', 'blub']
# plot 1
pl = []
a = 1

fig = pp.figure()
ax = fig.add_subplot(111)
#pp.set_grid()
ax.set_title('Total Energy vs lattice constant', fontsize=16, alpha=a, ha='center')
ax.set_xlabel('Lattice Constant [a/3.16]', fontsize=15)
ax.set_ylabel('Total engery [htr]', fontsize=15)
ax.yaxis.set_tick_params(size = 4.0, width = 1.0, labelsize =14, length = 5)
ax.xaxis.set_tick_params(size = 4.0, width = 1.0, labelsize =14, length = 5)
#ax.ticklabel_format(style='sci', axis='x', scilimits=(4,4))
#ax.ticklabel_format(style='sci', axis='y', scilimits=(4,4))
ax.yaxis.get_major_formatter().set_powerlimits((0, 3))
ax.yaxis.get_major_formatter().set_useOffset(False)

for i in range(0,nfiles):
    p1 = pp.plot(scaleAll[i],eT1_all[i], 's-', label = labela[i], linewidth = 2.0, markersize = 4.0)
    pl.append(p1)
    
pp.legend(bbox_to_anchor=(0.85, 1), loc=2, borderaxespad=0., fancybox=True)#loc='best', fancybox=True) #, framealpha=0.5) #loc='upper right')

if save:
    pp.savefig('Et_la_kpts.pdf', format='pdf')
'''
'''
# plot 2

fig1 = pp.figure()
ax1 = fig1.add_subplot(111)
#pp.set_grid()
ax1.set_title('Lattice Constant vs Nkpts', fontsize=16, alpha=a, ha='center')
ax1.set_xlabel('Nkpts', fontsize=15)
ax1.set_ylabel('Lattice Constant [a/3.16]', fontsize=15)
ax1.yaxis.set_tick_params(size = 4.0, width = 1.0, labelsize =14, length = 5)
ax1.xaxis.set_tick_params(size = 4.0, width = 1.0, labelsize =14, length = 5)
ax1.yaxis.get_major_formatter().set_powerlimits((0, 3))
ax1.yaxis.get_major_formatter().set_useOffset(False)
pl1 = pp.plot(xnkpts, a1_all, 's', label = '', linewidth = 2.0, markersize = 4.0)

if save:
    pp.savefig('La_kpts.pdf', format='pdf')

# plot 3

fig2 = pp.figure()
ax2 = fig2.add_subplot(111)
#pp.set_grid()
ax2.set_title('Total Energy vs Nkpts', fontsize=16, alpha=a, ha='center')
ax2.set_xlabel('Nkpts', fontsize=15)
ax2.set_ylabel('Minimum Total Engery [htr]', fontsize=15)
ax2.yaxis.set_tick_params(size = 4.0, width = 1.0, labelsize =14, length = 5)
ax2.xaxis.set_tick_params(size = 4.0, width = 1.0, labelsize =14, length = 5)
ax2.yaxis.get_major_formatter().set_powerlimits((0, 3))
ax2.yaxis.get_major_formatter().set_useOffset(False)
pl2 = pp.plot(xnkpts, a2_allc, 's', label = '', linewidth = 2.0, markersize = 4.0)


if save:
    pp.savefig('Et_kpts.pdf', format='pdf')
'''
#pp.show()
