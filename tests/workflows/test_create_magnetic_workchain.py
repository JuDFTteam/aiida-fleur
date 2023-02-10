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
''' Contains tests for the FleurCreateMagneticWorkChain '''

import pytest
import aiida_fleur
import os
from aiida.orm import Int
from aiida.engine import run_get_node
from aiida_fleur.workflows.create_magnetic_film import FleurCreateMagneticWorkChain

aiida_path = os.path.dirname(aiida_fleur.__file__)
TEST_INP_XML_PATH = os.path.join(aiida_path, 'tests/files/inpxml/Si/inp.xml')
CALC_ENTRY_POINT = 'fleur.fleur'
CALC2_ENTRY_POINT = 'fleur.inpgen'


# tests
@pytest.mark.usefixtures('aiida_profile', 'clear_database')
class Test_FleurCreateMagneticWorkChain:
    """
    Regression tests for the FleurCreateMagneticWorkChain
    """

    @pytest.mark.skip(reason='Caching does not work. After the EOS workchain finishes the structure'
                      '(probably) has a different hash due to numerical differences')
    @pytest.mark.regression_test
    @pytest.mark.timeout(9000, method='thread')
    def test_fleur_create_mag_FePt(self, enable_archive_cache, fleur_local_code, inpgen_local_code,
                                   show_workchain_summary):
        """
        full example using scf workflow with just a fleurinp data as input.
        Several fleur runs needed till convergence
        """
        from aiida.orm import Dict

        # input from examples, just with less computations

        fleur_inp = fleur_local_code
        inpgen_inp = inpgen_local_code

        ###
        wf_para = {
            'lattice': 'fcc',
            'directions': [[-1, 1, 0], [0, 0, 1], [1, 1, 0]],
            'host_symbol': 'Pt',
            'latticeconstant': 0,
            'size': (1, 1, 5),
            'replacements': {
                1: 'Fe',
                -1: 'Fe'
            },
            'decimals': 5,
            'pop_last_layers': 1,
            'total_number_layers': 8,
            'num_relaxed_layers': 3
        }

        wf_para = Dict(wf_para)

        wf_eos = {'points': 5, 'step': 0.015, 'guess': 1.00}

        wf_eos_scf = {'fleur_runmax': 4, 'density_converged': 0.002, 'itmax_per_run': 50, 'inpxml_changes': []}

        wf_eos_scf = Dict(wf_eos_scf)

        wf_eos = Dict(wf_eos)

        calc_eos = {
            'comp': {
                'kmax': 3.2,
            },
            'kpt': {
                'div1': 4,
                'div2': 4,
                'div3': 4
            }
        }

        calc_eos = Dict(calc_eos)

        options_eos = {
            'resources': {
                'num_machines': 1,
                'num_mpiprocs_per_machine': 1,
                'num_cores_per_mpiproc': 1
            },
            'queue_name': '',
            'custom_scheduler_commands': '',
            'max_wallclock_seconds': 1 * 60 * 60,
            'withmpi': False
        }

        options_eos = Dict(options_eos)

        wf_relax = {'film_distance_relaxation': False, 'force_criterion': 0.049}  #, 'use_relax_xml': True}

        wf_relax_scf = {
            'fleur_runmax': 2,
            'itmax_per_run': 100,
            #'alpha_mix': 0.015,
            #'relax_iter': 25,
            'density_converged': 0.02,
            'force_converged': 0.001,
            'force_dict': {
                'qfix': 2,
                'forcealpha': 0.75,
                'forcemix': 'straight'
            },
            'inpxml_changes': []
        }

        wf_relax = Dict(wf_relax)
        wf_relax_scf = Dict(wf_relax_scf)

        calc_relax = {
            'comp': {
                'kmax': 3.2,
            },
            'kpt': {
                'div1': 6,
                'div2': 5,
                'div3': 1
            },
            'atom': {
                'element': 'Pt',
                'rmt': 2.2,
                'lmax': 10,
                'lnonsph': 6,
                'econfig': '[Kr] 5s2 4d10 4f14 5p6| 5d9 6s1',
            },
            'atom2': {
                'element': 'Fe',
                'rmt': 2.1,
                'lmax': 10,
                'lnonsph': 6,
                'econfig': '[Ne] 3s2 3p6| 3d6 4s2',
            },
        }

        calc_relax = Dict(calc_relax)

        options_relax = {
            'resources': {
                'num_machines': 1,
                'num_mpiprocs_per_machine': 1,
                'num_cores_per_mpiproc': 1
            },
            'queue_name': '',
            'custom_scheduler_commands': '',
            'max_wallclock_seconds': 1 * 60 * 60,
            'withmpi': False
        }

        options_relax = Dict(options_relax)

        settings = Dict({})

        inputs = {
            'eos': {
                'scf': {
                    'wf_parameters': wf_eos_scf,
                    'calc_parameters': calc_eos,
                    'options': options_eos,
                    'inpgen': inpgen_inp,
                    'fleur': fleur_inp
                },
                'wf_parameters': wf_eos
            },
            'relax': {
                'scf': {
                    'wf_parameters': wf_relax_scf,
                    'calc_parameters': calc_relax,
                    'options': options_relax,
                    'inpgen': inpgen_inp,
                    'fleur': fleur_inp
                },
                'wf_parameters': wf_relax,
                'label': 'relaxation',
                'description': 'describtion',
                'max_iterations': Int(5)
            },
            'wf_parameters': wf_para,
            'distance_suggestion': Dict({
                'Pt': {
                    'Pt': 4.0,
                    'Fe': 4.0
                },
                'Fe': {
                    'Pt': 4.0,
                    'Fe': 4.0
                }
            })
        }

        with enable_archive_cache('fleur_create_magnetic_FePt.tar.gz'):
            # now run calculation
            out, node = run_get_node(FleurCreateMagneticWorkChain, **inputs)

        show_workchain_summary(node, verbose=True)
        assert node.is_finished_ok

        print(out)
        print(node)

        magnetic_struc = out.get('magnetic_structure', None)
        assert magnetic_struc is not None

        assert magnetic_struc.sites == [{
            'kind_name': 'Fe',
            'position': [0.0, 0.0, -6.32946436]
        }, {
            'kind_name': 'Pt',
            'position': [1.84976249, 2.61595921, -4.76652996]
        }, {
            'kind_name': 'Pt',
            'position': [0.0, 0.0, -2.91934811]
        }, {
            'kind_name': 'Pt',
            'position': [1.84976249, 2.61595921, -1.06958561]
        }, {
            'kind_name': 'Pt',
            'position': [0.0, 0.0, 0.78017688]
        }, {
            'kind_name': 'Pt',
            'position': [1.84976249, 2.61595921, 2.62993937]
        }, {
            'kind_name': 'Pt',
            'position': [0.0, 0.0, 4.47970187]
        }, {
            'kind_name': 'Pt',
            'position': [1.84976249, 2.61595921, 6.32946436]
        }]
        # outpara = out.get('output_eos_wc_para', None)
        # assert outpara is not None
        # outpara = outpara.get_dict()
        # print(outpara)

        # outstruc = out.get('output_eos_wc_structure', None)
        # assert outstruc is not None

        # assert False
        # check output
        #distance, bulk modulus, optimal structure, opt scaling
        #assert abs(outpara.get('scaling_gs') - 0.99268546558578) < 10**14
        #assert outpara.get('warnings') == ['Groundstate volume was not in the scaling range.']
        #assert outpara.get('info') == ['Consider rerunning around point 0.9926854655857787']

    @pytest.mark.skip
    @pytest.mark.timeout(500, method='thread')
    def test_fleur_create_mag_validation_wrong_inputs(self, fleur_local_code, inpgen_local_code, generate_structure2):
        """
        Test the validation behavior of FleurCreateMagneticWorkChain if wrong input is provided it should throw
        an exitcode and not start a Fleur run or crash
        """
        from aiida.orm import Dict

        # prepare input nodes and dicts
        options = {
            'resources': {
                'num_machines': 1,
                'num_mpiprocs_per_machine': 1
            },
            'max_wallclock_seconds': 5 * 60,
            'withmpi': False,
            'custom_scheduler_commands': ''
        }
        options = Dict(dict=options).store()

        wf_parameters = Dict({'points': 9, 'step': 0.002, 'guess': 1.00, 'wrong_key': None})
        wf_parameters.store()
        structure = generate_structure2()
        structure.store()

        ################
        # Create builders
        # interface of exposed scf is tested elsewhere

        # 1. create builder with wrong wf parameters
        builder_additionalkeys = FleurCreateMagneticWorkChain.get_builder()
        builder_additionalkeys.structure = structure
        builder_additionalkeys.wf_parameters = wf_parameters
        builder_additionalkeys.scf.fleur = fleur_local_code
        builder_additionalkeys.scf.inpgen = inpgen_local_code

        ###################
        # now run the builders all should fail early with exit codes

        # 1. structure and fleurinp given
        out, node = run_get_node(builder_additionalkeys)
        assert out == {}
        assert node.is_finished
        assert not node.is_finished_ok
        assert node.exit_status == 230
