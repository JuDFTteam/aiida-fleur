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
This module contains click option types specific to aiida-fleur
'''
import click
from aiida.cmdline.params import types
from aiida.cmdline.utils import echo
from aiida.common.exceptions import NotExistent
from aiida.plugins import DataFactory
from aiida.cmdline.utils.decorators import with_dbenv

wf_template_files = {
    'eos':
    '{"points": 9,\n'
    '"step": 0.002,\n'
    '"guess": 1.00}',
    'scf':
    '{"fleur_runmax": 4,\n'
    '"density_converged": 0.00002,\n'
    '"energy_converged": 0.002,\n'
    '"mode": "density",\n'
    '"itmax_per_run": 30}',
    'band':
    '{\n'
    '// Select your k-points\n'
    '"kpath": "auto"// This can be "auto" (meaning you try to pick a good choice automatically from inp.xml) or "seek" to use seek-k-path\n'
    '//"klistname": "path-3",//You can specify directly a list in the inp.xml/kpts.xml\n'
    '//"kpoints_number": 200,\n'
    '//"kpoints_distance": 0.1,\n'
    '//"kpoints_explicit": None\n}',
    'dos':
    '{\n'
    '// Select your k-points\n'
    '//"klistname": "path-3",//You can specify directly a list in the inp.xml/kpts.xml\n'
    '//"kpoints_number": 200,\n'
    '//"kpoints_distance": 0.1,\n'
    '// These parameters are relevant for the DOS mode\n'
    '"sigma": 0.005,\n'
    '"emin": -0.50,\n'
    '"emax": 0.90\n}',
    'relax':
    '{\n'
    '"film_distance_relaxation": "False", // if True, sets relaxXYZ="FFT" for all atoms\n'
    '"force_criterion": 0.049,            // Sets the threshold of the largest force\n'
    '"relax_iter": 5                      // Maximum number of optimization iterations\n'
    '}',
    'ssdisp_conv':
    '{\n'
    '"beta": {"all": 1.57079},   // set the angle of some or all atoms\n'
    '"q_vectors": {"label1": [0.0,0.0,0.0],  //set the q-vectors. Each has a label attached\n'
    '               "label2": [0.1,0.0,0.0]\n'
    '               }\n'
    '//"suppress_symmetries": False  // Only if you start from a structure: do not use symmetries\n'
    '}'
}


class OptionsType(click.ParamType):
    """
    Type to construct options for the computational resources to use
    """
    name = 'options for Computational resources'

    def convert(self, value, param, ctx):

        wf_options_template = '''{
"resources": {
    "num_machines": 1, //Number of computing nodes
    "num_mpiprocs_per_machine": 1, //Number of MPI processes per node
    "num_cores_per_mpiproc": 2 //Number of OMP threads per MPI process
},
"withmpi": true, //This flag makes sure that the process is submitted using MPI
"max_wallclock_seconds": 3600 //Maximum wallclock time in seconds
}'''

        try:
            #Perhaps a pk or uuid was given?
            return types.DataParamType(sub_classes=('aiida.data:core.dict',)).convert(value, param, ctx)
        except:
            pass  #Ok this failed, then we examine the argument as a filename

        if value == 'template.json':
            print('Writing template to wf_options.json')
            with open(f"wf_options.json", 'w') as f:
                f.write(wf_options_template)
            quit()

        import os
        if (os.path.isfile(value)):
            # a file was given. Create a dict from the file and use it
            try:
                with open(value) as f:
                    import json
                    from json_minify import json_minify

                    wf_options = json.loads(json_minify(f.read()))
            except RuntimeError as error:
                print(error)
                print(f"{value} could not be converted into a dict")
                os.abort()
            aiida_dict = DataFactory('dict')
            wf_dict = aiida_dict(wf_options)

            return wf_dict

        return None


class FleurinpType(click.ParamType):
    """
    Type to either load a fleurinp node or read an inp.xml file
    """
    name = 'FleurInp data/inp.xml file'

    def convert(self, value, param, ctx):
        try:
            return types.DataParamType(sub_classes=('aiida.data:fleur.fleurinp',)).convert(value, param, ctx)
        except:
            pass  #Ok this failed, so we try to read the file

        if value in ['inp.xml', '.', './']:
            from aiida_fleur.data.fleurinp import FleurinpData
            inp_files = ['inp.xml']
            #check if there are included files in this dir
            for file in ['kpts.xml', 'sym.xml', 'relax.xml']:
                import os.path
                if os.path.isfile(file):
                    inp_files.append(file)
            finp = FleurinpData(files=inp_files)
            return finp.store()
        return None


class RemoteType(click.ParamType):
    """
    Type for remote data. Might be specified by a uuid or a file in which this uuid is found
    """
    name = 'Remote folder'

    def convert(self, value, param, ctx):
        #Try to interpret value as uuid
        try:
            return types.DataParamType(sub_classes=('aiida.data:core.remote',)).convert(value, param, ctx)
        except:
            pass  #Ok this failed, so we try to read the file

        try:
            from aiida.orm import load_node
            with open(value) as f:
                import json
                dict_from_file = json.load(f)
            if 'SCF-uuid' in dict_from_file:
                scf_wf = load_node(dict_from_file['SCF-uuid'])
                return scf_wf.outputs.last_calc.remote_folder
            if 'retrieved-uuid' in dict_from_file:
                return dict_from_file['retrieved-uuid']
        except:
            return None


class WFParameterType(click.ParamType):
    """
    ParamType for giving workflow parameters
    """
    name = 'Workflow parameters'

    def convert(self, value, param, ctx):
        import os

        if value == 'template.json':
            if ctx.command.name in wf_template_files:
                with open(f"wf_{ctx.command.name}.json", 'w') as f:
                    f.write(wf_template_files[ctx.command.name])
            quit()

        if (os.path.isfile(value)):
            # a file was given. Create a dict from the file and use it
            try:
                with open(value) as f:
                    import json
                    from json_minify import json_minify

                    wf_param = json.loads(json_minify(f.read()))
            except RuntimeError as error:
                print(error)
                print(f"{value} could not be converted into a dict")
                os.abort()
            aiida_dict = DataFactory('dict')
            wf_dict = aiida_dict(wf_param)

            return wf_dict

        #Now load from aiida
        wf_dict = types.DataParamType(sub_classes=('aiida.data:core.dict',)).convert(value, param, ctx)

        return wf_dict


class StructureNodeOrFileParamType(click.ParamType):
    """
    The ParamType for identifying a structure by node or to extract it from a given file

    Pro: It is convenient
    Con: If users only use other formats to launch their workflows it will create many
    more structures in the database.
    """

    name = 'StructureFile'

    @with_dbenv()
    def convert(self, value, param, ctx):
        is_path = False
        # Alternative one could check if int or uuid
        # aiida allows also for shorten uuids
        from aiida.orm import StructureData, QueryBuilder

        if value in ['inp.xml', '.', './']:
            from aiida_fleur.data.fleurinp import FleurinpData
            inp_files = ['inp.xml']
            #check if there are included files in this dir
            for file in ['kpts.xml', 'sym.xml', 'relax.xml']:
                import os.path
                if os.path.isfile(file):
                    inp_files.append(file)
            finp = FleurinpData(files=inp_files)
            return finp.store()

        try:
            structure = types.DataParamType(sub_classes=('aiida.data:core.structure',)).convert(value, param, ctx)
        except (NotExistent, click.exceptions.BadParameter) as er:
            echo.echo(f'Tried to load node, could not find one for {value}. '
                      'I will further check if it is a filepath.')
            is_path = True

        if is_path:
            # If it is a path to a file try to convert the structure
            pathtype = click.Path(exists=True, dir_okay=False, resolve_path=True)
            filename = pathtype.convert(value, param, ctx)
            try:
                import ase.io
            except ImportError:
                echo.echo_critical('You have not installed the package ase. \nYou can install it with: pip install ase')

            try:
                asecell = ase.io.read(filename)
                structure = StructureData(ase=asecell)
            except ValueError as err:
                echo.echo_critical(str(err))
            # do not store structure, since this option is for calculation and workflow
            # input, which will store the structure anyway.

        # do not store again if structure is already there.
        duplicate = QueryBuilder().append(StructureData, filters={'extras._aiida_hash': structure._get_hash()}).first()  # pylint: disable=protected-access

        if duplicate:
            return duplicate[0]
        return structure
