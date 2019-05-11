#!/usr/bin/env runaiida
# -*- coding: utf-8 -*-

from __future__ import absolute_import
from __future__ import print_function
__copyright__ = (u"Copyright (c), 2018, Forschungszentrum Jülich GmbH, "
                 "IAS-1/PGI-1, Germany. All rights reserved.")
__license__ = "MIT license, see LICENSE.txt file"
__version__ = "0.27"
__contributors__ = "Jens Broeder"

from aiida import load_dbenv, is_dbenv_loaded
if not is_dbenv_loaded():
    load_dbenv()

import os
import json

from aiida.common.example_helpers import test_and_get_code
from aiida.orm import Code
from aiida.plugins import DataFactory
from aiida_fleur.workflows.scf import fleur_scf_wc
from aiida.engine.run import submit
from aiida.engine.calculation.job import CalcJob

ParameterData = DataFactory('parameter')
FleurinpData = DataFactory('fleur.fleurinp')
# get code
# look in benchmark.jason
# if no benchmark: print('No benchmarks definded in benchmark.jason for computer {}.)
# run the benchmarks, ggf think about input selection


code = 'fleur_mpi_v0.28@claix'

code_node = test_and_get_code(code, 'fleur.fleur')



def run_fleur_benchmark(code, inp_files_folder_path_list, wf_para_base_dict_list):
    """
    Executes fleur_scf_wcs for every path given in the inp_files_folder_path_list.
    resources and so on are specificed in the dictionaries in the nested wf_para_base_dict_list (if you want multiple runs for that system).
    
    designed for running benchmarks from fleur input files.
    """
    
    # get the code
    # load the system (load an inp.xml file from the disk)
    # launch scf_wc on given systems
  
    all_res = []
                                                                            
    if len(inp_files_folder_path_list) != len(wf_para_base_dict_list):
        print('Input error: for every input folder path given you have to specify a scf workchian paranode! I abort.')
        return None
    
    code_node = test_and_get_code(code, 'fleur.fleur')
    #if isinstance(code, Code):
    #    code_node = code
    #else:
    #    code_node = Code.get_from_string(code)

    # create a fleurinp for each 
    for i, path in enumerate(inp_files_folder_path_list):
        files = os.listdir(path) 
        inpfiles = []
        for name in files:
            inpfiles.append(os.path.join(path, name))
        if inpfiles:
            fleurinp = FleurinpData(files=inpfiles)
            structure = fleurinp.get_structuredata_nwf()#fleurinp)
            formula = structure.get_formula()
        else:
            print(("No files found in {}".format(path)))
            continue
        scf_para = wf_para_base_dict_list[i]
        print(scf_para)
        label = 'fleur_scf_benchmark_run_{}'.format(formula)
        description = 'Fleur benchmark run on system {} with resources {}'.format(formula, scf_para['resources'])
        print(('submitting {}'.format(label)))
        res = submit(fleur_scf_wc, wf_parameters=Dict(dict=scf_para), fleurinp=fleurinp, fleur=code_node, _label=label, _description=description)
        all_res.append(res)
    return all_res

# TODO: set path, or use some scheme for finding the files

basepath = '../inp_xml_files/benchmarks/'
basepath = os.path.abspath(basepath)
benchmark_system = ['fleur_big_TiO', 
                    'fleur_big_TiO2', 
                    'fleur_mid_CuAg', 
                    'fleur_mid_GaAs', 
                    'fleur_small_AuAg', 
                    'fleur_tiny_NaCl']

bench_res_file = './fleur_benchmark_resources.json'
rf = open(bench_res_file, 'r')
benchmark_system_resources = json.load(rf)
rf.close()

# scf parameter node, change fleur_runmax and itmax_per_run to run several iterations and converge the calculation.
wf_para_base_benchmark = {'fleur_runmax' : 1, 
                          'density_criterion' : 0.00001,
                          'itmax_per_run' : 1,
                          'serial' : False}
                          #   'options' : {
                          #                         'resources': {"num_machines": 1},
                          ##                         'walltime_sec': 60*60,
                          #                        'queue_name': '',
                          #                         'custom_scheduler_commands' : '',
                          #                         'max_memory_kb' : None,
                          #                         'import_sys_environment' : False,
                          #                         'environment_variables' : {}},
                          #                     'serial' : False,
                          # 'itmax_per_run' : 30,
                          # 'inpxml_changes' : [],
                          
# select the systems to run # TODO maybe from input
systems_to_run = benchmark_system[-2:-1]
  
############################
# acctually run the benchmarks:

computer = code_node.get_computer()
clabel = computer.get_name()
#default_procs = computer.get_default_mpiprocs_per_machine()
benchmark_system_folders = []
#wf_para_all_list = []

for system in systems_to_run:
    sys_res = benchmark_system_resources.get(system, {}).get(clabel, {})
    if not sys_res:
        print(('INPUT VALIDATION WARNING: No benchmark to run on computer "{}" for system "{}"'.format(clabel, system)))
        continue
    benchmark_system_folder = os.path.join(basepath, system +'/input_files/')
    
    hpc_res =  sys_res.get('resources') 
    benchmark_system_folders_list, wf_para_benchmark_list = [], []
    
    # so far we assume that the lists for resources, walltime and scheduler commands have the same length
    for i, run_res in enumerate(hpc_res):
        wf_para_benchmark = wf_para_base_benchmark.copy()                     
        options = {}
        options['queue_name'] = sys_res.get('queue_name', '')
        options['resources'] = run_res
        options['walltime_sec'] = sys_res.get('walltime_sec')[i]
        options['custom_scheduler_commands'] = sys_res.get('custom_scheduler_commands')[i]
        options['environment_variables'] = sys_res.get('environment_variables')[i]
        options['max_memory_kb'] = sys_res.get('max_memory_kb')[i] 
        wf_para_benchmark['options'] = options
        print(wf_para_benchmark)
        benchmark_system_folders_list.append(benchmark_system_folder)
        wf_para_benchmark_list.append(wf_para_benchmark)
    #wf_para_all_list.append(wf_para_benchmark_list)
run_fleur_benchmark(code, benchmark_system_folders_list, wf_para_benchmark_list)                        
