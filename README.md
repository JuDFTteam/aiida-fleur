# FLEUR with AiiDA

[![MIT license](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)
[![GitHub release](https://img.shields.io/github/release/broeder-j/aiida-fleur.svg)](https://github.com/broeder-j/aiida-fleur/releases)
[![PyPI version](https://badge.fury.io/py/aiida-fleur.svg)](https://badge.fury.io/py/aiida-fleur)
[![Build develop](https://travis-ci.org/JuDFTteam/aiida-fleur.svg?branch=master)](https://travis-ci.org/JuDFTteam/aiida-fleur)
[![Coveralls github branch](https://github.com/JuDFTteam/aiida-fleur/blob/develop/aiida_fleur/tests/coverage.svg)](https://github.com/JuDFTteam/aiida-fleur/tree/develop)
[![Code quality pylint](https://github.com/JuDFTteam/aiida-fleur/blob/develop/aiida_fleur/tests/pylint.svg)](https://github.com/JuDFTteam/aiida-fleur/tree/develop)
[![Documentation Status](https://readthedocs.org/projects/aiida-fleur/badge/?version=develop)](https://aiida-fleur.readthedocs.io/en/develop/?badge=develop)


This software contains a plugin that enables the usage of the all-electron
DFT [FLEUR code](http://www.flapw.de) with the [AiiDA framework](http://www.aiida.net).

Developed at [Forschungszentrum Jülich GmbH](http://www.fz-juelich.de/pgi/pgi-1/DE/Home/home_node.html)


### Documentation

Hosted at http://aiida-fleur.readthedocs.io/en/develop/index.html.
For other information see the AiiDA-core docs or http://www.flapw.de.

### License:

MIT license.
See the license file.

### How to cite:
If you use this package please consider citing:
```
J. Broeder, D. Wortmann, and S. Blügel,
Using the AiiDA-FLEUR package for all-electron ab initio electronic structure
data generation and processing in materials science,
In Extreme Data Workshop 2018 Proceedings, 2019, vol 40, p 43-48
```


### Comments/Disclaimer:

The plug-in and the workflows will only work with a Fleur version using xml files as I/O.


### Contents

1. [Introduction](#Introduction)
2. [Installation Instructions](#Installation)
3. [Code Dependencies](#Dependencies)
4. [Further Information](#FurtherInfo)

## Introduction <a name="Introduction"></a>

This is a python package (AiiDA plugin, workflows and utility)
allowing to use the FLEUR-code in the AiiDA Framework.
The FLEUR-code is an all-electron DFT code using the FLAPW method,
that is widely applied in the material science and physics community.

### The plugin :

The Fleur plugin consists of:

    1. A data-structure representing input files and called FleurinpData.
    2. inpgen calculation
    3. FLEUR calculation
    4. Workchains
    5. utility

### Workchains in this package:

workflow entry point name | Description
--------------|------------
fleur.scf | SCF-cycle of Fleur. Converge the charge density and the Total energy with multiple FLEUR runs
fleur.eos | Calculate and Equation of States with FLEUR (currently cubic systems only)
fleur.dos | Calculate a Density of States (DOS) with FLEUR
fleur.band | Calculate a Band structure with FLEUR
fleur.relax | Relaxation of the atomic positions of a crystal structure with FLEUR
fleur.init_cls | Calculate initial corelevel shifts and formation energies with FLEUR
fleur.corehole | Workflow for corehole calculations, calculation of Binding energies with FLEUR
fleur.dmi | Calculates Dzyaloshinskii–Moriya Interaction energy dispersion of a spin spiral
fleur.ssdisp | Calculates exchange interaction energy dispersion of a spin spiral
fleur.mae | Calculates Magnetic Anisotropy Energy

See the AiiDA documentation for general info about the AiiDA workflow system or how to write workflows.


### Utility/tools:

filename | Description
---------|------------
Structure_util.py | Constains some methods to handle AiiDA structures (some of them might now be methods of the AiiDA structureData, if so use them from there!)
merge_parameter.py | Methods to handle parameterData nodes, i.e merge them. Which is very useful for all-electron codes, because instead of pseudo potentialsfamilies you can create now families of parameter nodes for the periodic table.
xml_util.py | All xml functions that are used, by parsers and other tools are in here. Some are 'general' some a very specific to Fleur.
read_cif.py | This can be used as stand-alone to create StructureData nodes from .cif files from an directory tree.

Utility and tools, which are independend of AiiDA are moved to the [masci-tools](https://github.com/JuDFTteam/masci-tools) (material science tools) repository,
which is a dependency of aiida-fleur.

## Installation Instructions <a name="Installation"></a>

From the aiida-fleur folder (after downloading the code, recommended) use:

    $ pip install .
    # or which is very useful to keep track of the changes (developers)
    $ pip install -e .

To uninstall use:

    $ pip uninstall aiida-fleur

Or install latest release version from pypi:

    $ pip install aiida-fleur

### Test Installation
To test rather the installation was successful use:
```bash
$ verdi plugins list aiida.calculations
```
```bash
   # example output:

   ## Pass as a further parameter one (or more) plugin names
   ## to get more details on a given plugin.
   ...
   * fleur.fleur
   * fleur.inpgen
```
You should see 'fleur.*' in the list

The other entry points can be checked with the AiiDA Factories (Data, Workflow, Calculation, Parser).
(this is done in test_entry_points.py)

We suggest to run all the (unit)tests in the aiida-fleur/aiida_fleur/tests/ folder.

    $ bash run_all_cov.sh

___

## Code Dependencies <a name="Dependencies"></a>

Requirements are listed in 'setup_requirements.txt' and setup.json.

most important are:

* aiida_core >= 1.0.1
* lxml
* ase
* masci-tools

Mainly AiiDA:

1. Download from [www.aiida.net -> Download](www.aiida.net)
2. install and setup -> [aiida's documentation](http://aiida-core.readthedocs.org/en/stable)

Easy plotting and other useful routines that do not depend on aiida_core are part of
the [masci-tools](https://github.com/JuDFTteam/masci-tools) (material science tools) repository.

For easy ploting we recommend using 'plot_methods' from masci-tools, which are also deployed by the 'plot_fleur(<node(s)>)' function.

## Further Information <a name="FurtherInfo"></a>

The plug-in source code documentation is [here](http://aiida-fleur.readthedocs.io/en/develop/index.html).
also some documentation of the plug-in, further things can be found at www.flapw.de.
Usage examples are shown in 'examples'.


## Acknowledgements

Besides the Forschungszentrum Juelich, this work is supported by the [MaX
European Centre of Excellence](<http://www.max-centre.eu/>) funded by the Horizon 2020 EINFRA-5 program,
Grant No. 676598.

For this work essential is AiiDA, which itself is supported by the [MARVEL National Centre for Competency in Research](<http://nccr-marvel.ch>) funded by the [Swiss National Science Foundation](<http://www.snf.ch/en>).


![MaX](docs/source/images/MaX.png)
