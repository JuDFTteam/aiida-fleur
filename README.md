# FLEUR with AiiDA

[![MIT license](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)
[![GitHub release](https://img.shields.io/github/release/broeder-j/aiida-fleur.svg)](https://github.com/broeder-j/aiida-fleur/releases)
[![PyPI version](https://img.shields.io/pypi/v/aiida-fleur.svg)](https://pypi.python.org/pypi/aiida-fleur)
[![Build develop](https://travis-ci.org/broeder-j/aiida-fleur.svg?branch=develop)](https://travis-ci.org/broeder-j/aiida-fleur)
[![Coveralls github branch](https://github.com/broeder-j/aiida-fleur/blob/develop/aiida_fleur/tests/coverage.svg)](https://github.com/broeder-j/aiida-fleur/tree/develop)
[![Documentation Status](https://readthedocs.org/projects/aiida-fleur/badge/?version=develop)](http://aiida-fleur.readthedocs.io/en/develop/?badge=develop)
[![Code quality pylint](https://github.com/broeder-j/aiida-fleur/blob/develop/aiida_fleur/tests/pylint.svg)](https://github.com/broeder-j/aiida-fleur/tree/develop)


This software contains a plugin that enables the usage of the all-electron DFT [FLEUR code](http://www.flapw.de) with the [AiiDA framework](http://www.aiida.net). Further this package contains common workflows and some utility.

Developed at [Forschungszentrum Jülich GmbH](http://www.fz-juelich.de/pgi/pgi-1/DE/Home/home_node.html)


### Documentation

Hosted at http://aiida-fleur.readthedocs.io/en/develop/index.html.
For other information checkout the AiiDA docs or http://www.flapw.de.

### License:

MIT license.
See license file.


### Comments/Disclaimer:

The plug-in and the workflows will only work with a Fleur version using xml files as I/O.
For example check out the Fleur version released withing MAX.

**Notice:** This is still under heavy development.
For anything contact j.broeder@fz-juelich.de and feel free to write issues and contribute.


### Contents

1. [Introduction](#Introduction)
2. [Installation Instructions](#Installation)
3. [Code Dependencies](#Dependencies)
4. [Further Information](#FurtherInfo)

## Introduction <a name="Introduction"></a>

This is a python package (AiiDA plugin plus workflows plus utility) to use the FLEUR-code with the AiiDA Framework.
The FLEUR-code is an all-electron DFT code using the FLAPW method,
and widely applied in the material science and physics community.

### The plugin :

The Fleur plug-in consists of a datastructure called FleurinpData and two plug-ins,
one for the Fleur inputgenerator (inpgen) and one for a Fleur calculation itself.

Every plug-in has an input part (defines the calculation) and an output parser, see the AiiDA documentation for general info.


### Workflows in this package:

workflow name | Description
--------------|------------
scf | SCF-cycle of Fleur. Converge the charge density and the Total energy with multiple FLEUR runs
eos | Calculate and Equation of States (Lattice constant) with FLEUR
dos | Calculate a Density of States (DOS) with FLEUR
bands | Calculate a Band structure with FLEUR
relax | Relaxation of a crystal structure with FLEUR

See the AiiDA documentation for general info about the AiiDA workflow system or how to write workflows.


### Utility/tools:

filename | Description
---------|------------
Structure_util.py | Constains some methods to handle AiiDA structures (some of them might now be methods of the AiiDA structureData, if so use them from there!)
merge_parameter.py | Methods to handle parameterData nodes, i.e merge them. Which is very useful for all-electron codes, because instead of pseudo potentialsfamilies you can create now families of parameter nodes for the periodic table.
xml_util.py | All xml functions that are used, by parsers and other tools are in here. Some are 'general' some a very specific to Fleur.
read_cif.py | This can be used as stand-alone to create StructureData nodes from .cif files from an directory tree.
...

## Installation Instructions <a name="Installation"></a>

From the aiida-fleur folder (after downloading the code, recommended) use:

    $ pip install .
    # or which is very useful to keep track of the changes (developers)
    $ pip install -e .

To uninstall use:

    $ pip uninstall aiida-fleur

Or install lates release version from pypi:

    $ pip install aiida-fleur

### Test Installation
To test wether the installation was successful use:
```bash
$ verdi calculation plugins
```
```bash
   # example output:

   ## Pass as a further parameter one (or more) plugin names
   ## to get more details on a given plugin.
   * codtools.cifcellcontents
   * codtools.cifcodcheck
   * codtools.cifcodnumbers
   * codtools.ciffilter
   * codtools.cifsplitprimitive
   * quantumespresso.cp
   * quantumespresso.pw
   * quantumespresso.pwimmigrant
   * simpleplugins.templatereplace
   ...
   * fleur.fleur
   * fleur.inpgen
```
You should see 'fleur.*' in the list

The other entry points can be checked with the AiiDA Factories (Data, Workflow, Calculation, Parser).
(this is done in test_entry_points.py)

We suggest to run all the (unit)tests in the aiida-fleur/aiida_fleur/tests/ folder.

    $ bash run_all_cov.sh

## Files/Contents
A short sum up of the most important classes and where to find them, how to import them.

___
### Plugin files:

#### Data:
fleurinpData : aiida_fleur.data.fleurinp.py
fleurinpModifier : aiida_fleur.data.fleurinpmodifier.py

#### Calculations:
FleurinputgenCalculation : aiida_fleur.calculation.fleurinputgen.py
FleurCalculation : aiida_fleur.calculation.fleur.py

#### Parsers:
FleurinpgenParser: aiida_fleur.parsers.fleur_inputgen.py
FleurParser: aiida_fleur.parsers.fleur.py

#### XML Schema Files:
in fleur_schema folder

The Fleur code needs a XMLSchema file, the plugin searches (walks) for them in this fleur_schema folder.
If nothing works add a path to schemafile_index.py, or search_paths (fleurinp).
Also if you want to use/need different schemas add them to this folder.

___
### Workflows/workchains:

Class name | file name
-----------|----------
fleur_scf_wc | aiida_fleur.workflows.scf.py
fleur_eos_wc | aiida_fleur.workflows.eos.py
fleur_dos_wc | aiida_fleur.workflows.dos.py
fleur_band_wc | aiida_fleur.workflows.band.py
fleur_relax_wc | aiida_fleur.workflows.relax.py
...

### Utility under '/aiida_fleur/tools/':

Structure_util.py
merge_parameter.py
read_cif.py
...

___
## Code Dependencies <a name="Dependencies"></a>

Requirements are listed in 'setup_requirements.txt' and setup.json.

most important are:

* aiida_core >= 0.9
* lxml
* ase
...

Mainly AiiDA:

1. Download from [www.aiida.net/?page_id=264](www.aiida.net -> Download)
2. install and setup -> [http://aiida-core.readthedocs.org/en/stable/](aiida's documentation)

For easy ploting we recommend installing 'plot_methods' (not yet integrated into this package):
https://bitbucket.org/broeder-j/plot_methods

## Further Information <a name="FurtherInfo"></a>

The plug-in source code documentation is [here](http://aiida-fleur.readthedocs.io/en/develop/index.html).
also some documentation of the plug-in, further things can be found at www.flapw.de.
Usage examples are shown in 'examples'.







