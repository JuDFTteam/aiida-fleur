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
Module with CLI commands to launch for calcjob and workflows of aiida-fleur.
'''
# TODO: these launch commands should be put in separate files, if this one becomes to large..

import click
from ..util import options, utils, defaults
from aiida_fleur.tools.dict_util import clean_nones
from aiida.orm import Dict
from aiida.plugins import WorkflowFactory
from aiida.plugins import CalculationFactory
from aiida_fleur.data.fleurinp import FleurinpData


@click.command('inpgen')
@options.STRUCTURE_OR_FILE(default=defaults.get_si_bulk_structure, show_default=True)
@options.INPGEN()
@options.CALC_PARAMETERS()
@options.SETTINGS()
@options.DAEMON()
@options.OPTION_NODE()
@options.QUEUE_NAME()
def launch_inpgen(structure, inpgen, calc_parameters, settings, daemon, option_node, queue):
    """
    Launch an inpgen calcjob on given input

    If no code is given it queries the DB for inpgen codes and uses the one with
    the newest creation time.

    Either structure or anysource_structure can be specified.
    Default structure is Si bulk.
    """

    options_d = {
        'withmpi': False,
        'max_wallclock_seconds': 6000,
        'resources': {
            'num_machines': 1,
            'num_mpiprocs_per_machine': 1
        },
        'queue_name': queue
    }
    if option_node:
        opt_dict = option_node.get_dict()
        for key, val in opt_dict.items():
            options_d[key] = val

    process_class = CalculationFactory('fleur.inpgen')
    inputs = {
        'code': inpgen,
        'structure': structure,
        'parameters': calc_parameters,
        'settings': settings,
        'metadata': {
            'options': options_d
        }
    }

    inputs = clean_nones(inputs)
    builder = process_class.get_builder()
    builder.update(inputs)
    utils.launch_process(builder, daemon)


@click.command('fleur')
@options.FLEURINP()
@options.FLEUR()
@options.REMOTE()
@options.SETTINGS()
@options.DAEMON()
@options.MAX_NUM_MACHINES()
@options.MAX_WALLCLOCK_SECONDS()
@options.NUM_MPIPROCS_PER_MACHINE()
@options.OPTION_NODE()
@options.WITH_MPI()
@options.QUEUE_NAME()
@click.option('--launch_base/--no-launch_base',
              is_flag=True,
              default=True,
              show_default=True,
              help=('Run the base_fleur workchain, which also handles errors instead '
                    'of a single fleur calcjob.'))
def launch_fleur(fleurinp, fleur, parent_folder, settings, daemon, max_num_machines, max_wallclock_seconds,
                 num_mpiprocs_per_machine, option_node, with_mpi, launch_base, queue):
    """
    Launch a base_fleur workchain.
    If launch_base is False launch a single fleur calcjob instead.

    """

    process_class = CalculationFactory('fleur.fleur')
    workchain_class = WorkflowFactory('fleur.base')

    options_d = {
        'withmpi': with_mpi,
        'queue_name': queue,
        'max_wallclock_seconds': max_wallclock_seconds,
        'resources': {
            'num_machines': max_num_machines,
            'num_mpiprocs_per_machine': num_mpiprocs_per_machine,
        }
    }
    if option_node:
        opt_dict = option_node.get_dict()
        for key, val in opt_dict.items():
            options_d[key] = val

    inputs = {
        'code': fleur,
        'fleurinp': fleurinp,
        'parent_folder': parent_folder,
        'settings': settings,
        'metadata': {
            'options': options_d
        }
    }

    if not launch_base:
        inputs = clean_nones(inputs)
        builder = process_class.get_builder()
        builder.update(inputs)
    else:
        if option_node is None:
            option_node = Dict({
                'withmpi': with_mpi,
                'max_wallclock_seconds': max_wallclock_seconds,
                'resources': {
                    'num_machines': max_num_machines,
                    'num_mpiprocs_per_machine': num_mpiprocs_per_machine
                }
            })

        inputs_base = {
            'code': fleur,
            'fleurinp': fleurinp,
            'parent_folder': parent_folder,
            'settings': settings,
            'options': option_node
        }
        inputs_base = clean_nones(inputs_base)
        builder = workchain_class.get_builder()
        builder.update(**inputs_base)

    utils.launch_process(builder, daemon)


@click.command('scf')
@options.STRUCTURE_OR_FILE(default='inp.xml', show_default=True)
@options.INPGEN()
@options.CALC_PARAMETERS()
@options.SETTINGS()
@options.FLEURINP()
@options.FLEUR()
@options.WF_PARAMETERS()
@options.REMOTE()
@options.DAEMON()
@options.SETTINGS()
@options.OPTION_NODE()
def launch_scf(structure, inpgen, calc_parameters, fleurinp, fleur, wf_parameters, parent_folder, daemon, settings,
               option_node):
    """
    Launch a scf workchain
    """
    fleurinp = None

    if isinstance(structure, FleurinpData):
        fleurinp = structure
        structure = None
        inpgen = None

    workchain_class = WorkflowFactory('fleur.scf')
    inputs = {
        'inpgen': inpgen,
        'fleur': fleur,
        'structure': structure,
        'fleurinp': fleurinp,
        'wf_parameters': wf_parameters,
        'calc_parameters': calc_parameters,
        'remote_data': parent_folder,
        'settings': settings,
        'options': option_node
    }

    inputs = clean_nones(inputs)
    builder = workchain_class.get_builder()
    builder.update(inputs)
    pk = utils.launch_process(builder, daemon)

    #Now create output files
    if fleurinp and not daemon:
        from aiida.orm import load_node
        wf = load_node(pk)
        scf_output = wf.outputs.output_scf_wc_para.get_dict()
        scf_output['SCF-uuid'] = wf.uuid

        #json with dict
        import json
        with open('scf.json', 'w') as file:
            json.dump(scf_output, file, indent=2)
        #plot
        from aiida_fleur.tools.plot.fleur import plot_fleur
        plot_fleur(wf, save=True, show=False)

        #store files
        for file in ['out.xml', 'cdn1', 'cdn_last.hdf']:
            if file in wf.outputs.last_calc.retrieved.list_object_names():
                with open(file, 'wb') as f:
                    f.write(wf.outputs.last_calc.retrieved.get_object_content(file, 'rb'))


@click.command('relax')
@options.STRUCTURE_OR_FILE(default='inp.xml', show_default=True)
@options.INPGEN()
@options.CALC_PARAMETERS()
@options.FLEUR()
@options.WF_PARAMETERS()
@options.SCF_PARAMETERS()
@options.DAEMON()
@options.SETTINGS()
@options.OPTION_NODE()
def launch_relax(structure, inpgen, calc_parameters, fleur, wf_parameters, scf_parameters, daemon, settings,
                 option_node):
    """
    Launch a base relax workchain

    # TODO final scf input
    """
    from aiida_fleur.workflows.relax import FleurRelaxWorkChain

    if isinstance(structure, FleurinpData):
        fleurinp = structure
        structure = None
        inpgen = None

    # we need a scf_paramters dict to change the forcemix if required later
    if scf_parameters == None:
        scf_parameters = Dict(dict={'force_dict': {'forcemix': 'BFGS'}, 'inpxml_changes': []})

    #workchain_class = WorkflowFactory('fleur.base_relax')
    inputs = {
        'scf': {
            'fleurinp': fleurinp,
            'wf_parameters': scf_parameters,
            'structure': structure,
            'calc_parameters': calc_parameters,
            'options': option_node,
            'inpgen': inpgen,
            'fleur': fleur
        },
        'wf_parameters': wf_parameters
    }

    inputs = clean_nones(inputs)
    builder = FleurRelaxWorkChain.get_builder()
    builder.update(inputs)
    pk = utils.launch_process(builder, daemon)

    #Now create output files
    if fleurinp and not daemon:
        from aiida.orm import load_node
        wf = load_node(pk)
        relax_output = wf.outputs.output_relax_wc_para.get_dict()
        relax_output['Relax-uuid'] = wf.uuid
        relax_output['retrieved-uuid'] = wf.outputs.last_scf.last_calc.retrieved.uuid

        #json with dict
        import json
        with open('relax.json', 'w') as file:
            json.dump(relax_output, file, indent=2)
        #plot
        from aiida_fleur.tools.plot.fleur import plot_fleur
        plot_fleur([wf], save=True, show=False)

        #store files
        for file in ['relax.xml', 'out.xml', 'cdn1', 'cdn_last.hdf']:
            if file in wf.outputs.last_scf.last_calc.retrieved.list_object_names():
                with open(file, 'wb') as f:
                    f.write(wf.outputs.last_scf.last_calc.retrieved.get_object_content(file, 'rb'))


@click.command('eos')
@options.STRUCTURE_OR_FILE(default='inp.xml', show_default=True)
@options.INPGEN()
@options.CALC_PARAMETERS()
@options.FLEUR()
@options.WF_PARAMETERS()
@options.SCF_PARAMETERS()
@options.DAEMON()
@options.SETTINGS()
@options.OPTION_NODE()
def launch_eos(structure, inpgen, calc_parameters, fleur, wf_parameters, scf_parameters, daemon, settings, option_node):
    """
    Launch a eos workchain
    """

    workchain_class = WorkflowFactory('fleur.eos')

    fleurinp = None

    if isinstance(structure, FleurinpData):
        fleurinp = structure
        structure = None

    inputs = {
        'scf': {
            'wf_parameters': scf_parameters,
            'calc_parameters': calc_parameters,
            'options': option_node,
            'inpgen': inpgen,
            'fleur': fleur
        },
        'wf_parameters': wf_parameters,
        'structure': structure,
        'fleurinp': fleurinp
    }
    inputs = clean_nones(inputs)
    builder = workchain_class.get_builder()
    builder.update(inputs)
    pk = utils.launch_process(builder, daemon)

    #Now create output files
    if fleurinp and not daemon:
        from aiida.orm import load_node
        wf = load_node(pk)
        eos_output = wf.outputs.output_eos_wc_para.get_dict()
        #json with dict
        import json
        with open('eos.json', 'w') as file:
            json.dump(eos_output, file, indent=2)
        #cif file
        if 'output_eos_wc_structure' in wf.outputs:
            import os.path
            if os.path.isfile('opt_struct.cif'):
                os.remove('opt_struct.cif')
            cif_struct = wf.outputs.output_eos_wc_structure.get_cif()
            cif_struct.export('opt_struct.cif')
        #plot
        if eos_output['volume_gs'] > 0:
            from aiida_fleur.tools.plot.fleur import plot_fleur
            plot_fleur(wf, save=True, show=False)

        for i, uuid in enumerate(eos_output['calculations']):
            scf = load_node(uuid)
            scale = eos_output['scaling'][i]
            with open(f"out_{scale}.xml", 'w') as f:
                f.write(scf.outputs.last_calc.retrieved.get_object_content('out.xml'))


@click.command('dos')
@options.FLEURINP(default='inp.xml')
@options.FLEUR()
@options.WF_PARAMETERS()
@options.REMOTE()
@options.DAEMON()
@options.SETTINGS()
@options.OPTION_NODE()
def launch_dos(fleurinp, fleur, wf_parameters, parent_folder, daemon, settings, option_node):
    """
    Launch a banddos workchain (special command to set the dos as a default mode)
    """
    if wf_parameters == None:
        wf_parameters = Dict({'mode': 'dos'})
    else:
        wf_dict = wf_parameters.get_dict()
        wf_dict['mode'] = 'dos'
        wf_parameters = Dict(wf_dict)

    launch_banddos(fleurinp, fleur, wf_parameters, parent_folder, daemon, settings, option_node)


@click.command('band')
@options.FLEURINP(default='inp.xml')
@options.FLEUR()
@options.WF_PARAMETERS()
@options.REMOTE()
@options.DAEMON()
@options.SETTINGS()
@options.OPTION_NODE()
def launch_band(fleurinp, fleur, wf_parameters, parent_folder, daemon, settings, option_node):
    """
    Launch a banddos workchain in 'band' mode
    """
    #Band is default
    launch_banddos(fleurinp, fleur, wf_parameters, parent_folder, daemon, settings, option_node)


def launch_banddos(fleurinp, fleur, wf_parameters, parent_folder, daemon, settings, option_node):
    """
    Launch a banddos workchain
    """
    workchain_class = WorkflowFactory('fleur.banddos')
    inputs = {
        'wf_parameters': wf_parameters,
        'fleur': fleur,
        'remote': parent_folder,
        'fleurinp': fleurinp,
        'options': option_node
    }
    inputs = clean_nones(inputs)
    builder = workchain_class.get_builder()
    builder.update(inputs)
    pk = utils.launch_process(builder, daemon)

    #Now create output files
    from aiida.orm import load_node
    wf = load_node(pk)
    banddos_output = wf.outputs.output_banddos_wc_para.get_dict()
    #json with dict
    import json
    with open('banddos.json', 'w') as file:
        json.dump(banddos_output, file, indent=2)
    #the banddos.hdf file
    with open(f"banddos.hdf", 'wb') as f:
        f.write(wf.outputs.banddos_calc.retrieved.get_object_content('banddos.hdf', 'rb'))

    #plot
    from aiida_fleur.tools.plot.fleur import plot_fleur
    plot_fleur(wf, save=True, show=False)


@click.command('init_cls')
@options.STRUCTURE_OR_FILE(default=defaults.get_si_bulk_structure, show_default=True)
@options.INPGEN()
@options.CALC_PARAMETERS()
@options.FLEURINP()
@options.FLEUR()
@options.WF_PARAMETERS()
@options.DAEMON()
@options.SETTINGS()
@options.OPTION_NODE()
def launch_init_cls(structure, inpgen, calc_parameters, fleurinp, fleur, wf_parameters, daemon, settings, option_node):
    """
    Launch an init_cls workchain
    """
    workchain_class = WorkflowFactory('fleur.init_cls')
    inputs = {
        'calc_parameters': calc_parameters,
        'options': option_node,
        'inpgen': inpgen,
        'fleur': fleur,
        'wf_parameters': wf_parameters,
        'structure': structure
    }
    inputs = clean_nones(inputs)
    builder = workchain_class.get_builder()
    builder.update(inputs)
    utils.launch_process(builder, daemon)


@click.command('corehole')
@options.STRUCTURE_OR_FILE(default=defaults.get_si_bulk_structure, show_default=True)
@options.INPGEN()
@options.CALC_PARAMETERS()
@options.FLEURINP()
@options.FLEUR()
@options.WF_PARAMETERS()
@options.DAEMON()
@options.SETTINGS()
@options.OPTION_NODE()
def launch_corehole(structure, inpgen, calc_parameters, fleurinp, fleur, wf_parameters, daemon, settings, option_node):
    """
    Launch a corehole workchain
    """
    workchain_class = WorkflowFactory('fleur.corehole')
    inputs = {
        'calc_parameters': calc_parameters,
        'options': option_node,
        'inpgen': inpgen,
        'fleur': fleur,
        'wf_parameters': wf_parameters,
        'structure': structure
    }
    inputs = clean_nones(inputs)
    builder = workchain_class.get_builder()
    builder.update(inputs)
    utils.launch_process(builder, daemon)


@click.command('mae')
@options.STRUCTURE_OR_FILE(default=defaults.get_fept_film_structure, show_default=True)
@options.INPGEN()
@options.CALC_PARAMETERS()
@options.FLEURINP()
@options.FLEUR()
@options.WF_PARAMETERS()
@options.SCF_PARAMETERS()
@options.REMOTE()
@options.DAEMON()
@options.SETTINGS()
@options.OPTION_NODE()
def launch_mae(structure, inpgen, calc_parameters, fleurinp, fleur, wf_parameters, scf_parameters, parent_folder,
               daemon, settings, option_node):
    """
    Launch a mae workchain
    """
    workchain_class = WorkflowFactory('fleur.mae')
    inputs = {
        'scf': {
            'wf_parameters': scf_parameters,
            'structure': structure,
            'calc_parameters': calc_parameters,
            'settings': settings,
            'inpgen': inpgen,
            'fleur': fleur
        },
        'wf_parameters': wf_parameters,
        'fleurinp': fleurinp,
        'remote': parent_folder,
        'fleur': fleur,
        'options': option_node
    }

    inputs = clean_nones(inputs)
    builder = workchain_class.get_builder()
    builder.update(inputs)
    utils.launch_process(builder, daemon)


@click.command('create_magnetic')
@options.INPGEN()
@options.CALC_PARAMETERS()
@options.FLEUR()
@options.WF_PARAMETERS(required=True)
@options.EOS_PARAMETERS()
@options.SCF_PARAMETERS()
@options.RELAX_PARAMETERS()
@options.DAEMON()
@options.OPTION_NODE()
def launch_create_magnetic(inpgen, calc_parameters, fleur, wf_parameters, eos_parameters, scf_parameters,
                           relax_parameters, daemon, option_node):
    """
    Launch a create_magnetic workchain
    """
    workchain_class = WorkflowFactory('fleur.create_magnetic')
    inputs = {
        'eos': {
            'scf': {
                'wf_parameters': scf_parameters,
                'calc_parameters': calc_parameters,
                'options': option_node,
                'inpgen': inpgen,
                'fleur': fleur
            },
            'wf_parameters': eos_parameters
        },
        'relax': {
            'scf': {
                'wf_parameters': scf_parameters,
                'calc_parameters': calc_parameters,
                'options': option_node,
                'inpgen': inpgen,
                'fleur': fleur
            },
            'wf_parameters': relax_parameters,
            'label': 'relaxation',
        },
        'wf_parameters': wf_parameters
    }

    inputs = clean_nones(inputs)
    builder = workchain_class.get_builder()
    builder.update(inputs)
    utils.launch_process(builder, daemon)


@click.command('ssdisp')
@options.STRUCTURE_OR_FILE(default=defaults.get_fept_film_structure, show_default=True)
@options.INPGEN()
@options.CALC_PARAMETERS()
@options.FLEUR()
@options.WF_PARAMETERS(required=True)
@options.SCF_PARAMETERS()
@options.DAEMON()
@options.OPTION_NODE()
def launch_ssdisp(structure, inpgen, calc_parameters, fleur, wf_parameters, scf_parameters, daemon, option_node):
    """
    Launch a ssdisp workchain
    """
    workchain_class = WorkflowFactory('fleur.ssdisp')
    inputs = {
        'scf': {
            'wf_parameters': scf_parameters,
            'structure': structure,
            'calc_parameters': calc_parameters,
            'options': option_node,
            'inpgen': inpgen,
            'fleur': fleur
        },
        'wf_parameters': wf_parameters,
        'fleur': fleur,
        'options': option_node
    }
    inputs = clean_nones(inputs)
    builder = workchain_class.get_builder()
    builder.update(inputs)
    utils.launch_process(builder, daemon)


@click.command('ssdisp_conv')
@options.STRUCTURE_OR_FILE(default='inp.xml', show_default=True)
@options.INPGEN()
@options.CALC_PARAMETERS()
@options.FLEUR()
@options.WF_PARAMETERS(required=True)
@options.SCF_PARAMETERS()
@options.DAEMON()
@options.OPTION_NODE()
def launch_ssdisp(structure, inpgen, calc_parameters, fleur, wf_parameters, scf_parameters, daemon, option_node):
    """
    Launch a ssdisp_conv workchain
    """
    workchain_class = WorkflowFactory('fleur.ssdisp_conv')

    fleurinp = None
    if (isinstance(structure, FleurinpData)):
        fleurinp = structure
        structure = None
        inpgen = None
        calc_parameters = None

    inputs = {
        'scf': {
            'wf_parameters': scf_parameters,
            'calc_parameters': calc_parameters,
            'options': option_node,
            'inpgen': inpgen,
            'structure': structure,
            'fleurinp': fleurinp,
            'fleur': fleur
        },
        'wf_parameters': wf_parameters,
    }
    inputs = clean_nones(inputs)
    builder = workchain_class.get_builder()
    builder.update(inputs)
    pk = utils.launch_process(builder, daemon)

    if not daemon:
        from aiida.orm import load_node
        wf = load_node(pk)
        ssdisp_output = wf.outputs.output_ssdisp_conv_wc_para.get_dict()
        #json with dict
        import json
        with open('ssdisp_conv.json', 'w') as file:
            json.dump(ssdisp_output, file, indent=2)
        #TODO plotting would be nice here


@click.command('dmi')
@options.STRUCTURE_OR_FILE(default=defaults.get_fept_film_structure, show_default=True)
@options.INPGEN()
@options.CALC_PARAMETERS()
@options.FLEUR()
@options.WF_PARAMETERS(required=True)
@options.SCF_PARAMETERS()
@options.DAEMON()
@options.OPTION_NODE()
def launch_dmi(structure, inpgen, calc_parameters, fleur, wf_parameters, scf_parameters, daemon, option_node):
    """
    Launch a dmi workchain
    """
    click.echo('Not implemented yet, sorry. Please implement me!')
    workchain_class = WorkflowFactory('fleur.dmi')
    inputs = {
        'scf': {
            'wf_parameters': scf_parameters,
            'structure': structure,
            'calc_parameters': calc_parameters,
            'options': option_node,
            'inpgen': inpgen,
            'fleur': fleur
        },
        'wf_parameters': wf_parameters,
        'fleur': fleur,
        'options': option_node
    }
    inputs = clean_nones(inputs)
    builder = workchain_class.get_builder()
    builder.update(inputs)
    utils.launch_process(builder, daemon)
