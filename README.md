# FLEUR with AiiDA

[![MIT license](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)
[![GitHub release](https://img.shields.io/github/release/JuDFTteam/aiida-fleur.svg)](https://github.com/JuDFTteam/aiida-fleur/releases)
[![PyPI version](https://badge.fury.io/py/aiida-fleur.svg)](https://badge.fury.io/py/aiida-fleur)
[![Conda Version](https://img.shields.io/conda/vn/conda-forge/aiida-fleur.svg)](https://anaconda.org/conda-forge/aiida-fleur)
[![PyPI pyversions](https://img.shields.io/pypi/pyversions/aiida-fleur.svg)](https://pypi.python.org/pypi/aiida-fleur)
[![Fleur Compatibility][Fleur v1.2]](https://www.flapw.de/rel)
[![Build status](https://github.com/JuDFTteam/aiida-fleur/workflows/aiida-fleur/badge.svg?branch=develop&event=push)](https://github.com/JuDFTteam/aiida-fleur/actions)
[![Documentation Status](https://readthedocs.org/projects/aiida-fleur/badge/?version=develop)](https://aiida-fleur.readthedocs.io/en/develop/?badge=develop)
[![codecov](https://codecov.io/gh/JuDFTteam/aiida-fleur/branch/develop/graph/badge.svg)](https://codecov.io/gh/JuDFTteam/aiida-fleur)
[![DOI](https://zenodo.org/badge/DOI/10.5281/zenodo.5531549.svg)](https://doi.org/10.5281/zenodo.5531549)

This software contains a plugin that enables the usage of the all-electron
DFT [FLEUR code](http://www.flapw.de) with the [AiiDA framework](http://www.aiida.net).

Developed at [Forschungszentrum Jülich GmbH](http://www.fz-juelich.de/pgi/pgi-1/DE/Home/home_node.html)

## Compatibility matrix

| FLEUR Plugin | AiiDA CORE | Python | FLEUR/XML file version | 
|-|-|-|-|
| `v2.0.0 < v3.0.0` | ![Compatibility for v2.0][AiiDA v2.0] |  [![PyPI pyversions](https://img.shields.io/badge/python-3.8_\|_3.9_\|_3.10-blue)](https://pypi.org/project/aiida-fleur.svg) |![Fleur Compatibility][Fleur v2.0]/`<=0.37` |
| `v1.2.0 < v2.0.0` | ![Compatibility for v1.2][AiiDA v1.2] |  [![PyPI pyversions](https://img.shields.io/pypi/pyversions/aiida-fleur.svg)](https://pypi.org/project/aiida-fleur) | ![Fleur Compatibility][Fleur v1.2]/`<=0.35` |
| `v1.0.0 < v1.2.0` | ![Compatibility for v1.0][AiiDA v1.0] |  [![PyPI pyversions](https://img.shields.io/badge/python-3.6_\|_3.7_\|_3.8_\|_3.9-blue)](https://pypi.org/project/aiida-fleur/1.2.0) | ![Fleur Compatibility][Fleur v1.0]/`<=0.33` |
| `< v0.6.3` | ![Compatibility for v0.6.3][AiiDA v0.6.3] | [![PyPI pyversions](https://img.shields.io/badge/python-2.7-blue)](https://pypi.python.org/pypi/aiida-fleur/0.6.3/) | ![Fleur Compatibility][Fleur v0.6.3]/`<=0.31` |

### Documentation and User Support

Hosted at http://aiida-fleur.readthedocs.io/en/develop/index.html.
For other information see the AiiDA-core docs or http://www.flapw.de.

Users can post any questions in the Fleur user [forum](http://fleur.xobor.de/)

For bugs, feature requests and further issues please use the issue tracker on github of the aiida-fleur repository.

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

The plug-in and the workflows will only work with a Fleur version using xml files as I/O, i.e >v0.27.


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
read_cif.py | This can be used as stand-alone to create StructureData nodes from .cif files from an directory tree.

Utility and tools, which are independend of AiiDA are moved to the [masci-tools](https://github.com/JuDFTteam/masci-tools) (material science tools) repository,
which is a dependency of aiida-fleur.


### Command line interface (CLI)

Besides the python API, aiida-fleur comes with a builtin CLI: `aiida-fleur`. 
This interface is built using the click library and supports tab-completion. 

To enable tab-completion, add the following to your shell loading script, e.g. the .bashrc or virtual environment activate script:

    eval "$(_AIIDA_FLEUR_COMPLETE=source aiida-fleur)"

the main subcommands include:

    data: Commands to create and inspect data nodes
        fleurinp   Commands to handle `FleurinpData` nodes.
        parameter  Commands to create and inspect `Dict` nodes containing FLAPW parameters
        structure  Commands to create and inspect `StructureData` nodes.
    launch: Commands to launch workflows and calcjobs of aiida-fleur

        banddos          Launch a banddos workchain
        corehole         Launch a corehole workchain
        create_magnetic  Launch a create_magnetic workchain
        dmi              Launch a dmi workchain
        eos              Launch a eos workchain
        fleur            Launch a base_fleur workchain.
        init_cls         Launch an init_cls workchain
        inpgen           Launch an inpgen calcjob on given input If no    code is...
        mae              Launch a mae workchain
        relax            Launch a base relax workchain # TODO final scf    input
        scf              Launch a scf workchain
        ssdisp           Launch a ssdisp workchain
    
    plot: Invoke the plot_fleur command on given nodes
    
    workflow: Commands to inspect aiida-fleur workchains and prepare inputs

for example to launch an scf workchain on a given structure execute:
    
    $ aiida-fleur launch scf -i <inpgenpk> -f <fleurpk> -S <structurepk>

the command can also process structures in any format `ase` can handle, this includes `Cif`, `xsf` and `poscar` files. In such a case simply parse the path to the file:

    $ aiida-fleur launch scf -i <inpgenpk> -f <fleurpk> -S ./structure/Cu.cif

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

Requirements are listed in `pyproject.toml`

most important are:

* aiida_core >= 2.0
* lxml
* ase
* masci-tools

Mainly AiiDA:

1. Download from [www.aiida.net -> Download](www.aiida.net)
2. install and setup -> [aiida's documentation](http://aiida-core.readthedocs.org/en/stable)

Easy plotting and other useful routines that do not depend on aiida_core are part of
the [masci-tools](https://github.com/JuDFTteam/masci-tools) (material science tools) repository.

For easy plotting we recommend using 'plot_methods' from masci-tools, which are also deployed by the 'plot_fleur(<node(s)>)' function.

## Further Information <a name="FurtherInfo"></a>

The plug-in source code documentation is [here](http://aiida-fleur.readthedocs.io/en/develop/index.html).
also some documentation of the plug-in, further things can be found at www.flapw.de.
Usage examples are shown in 'examples'.


## Acknowledgements

Besides the Forschungszentrum Juelich, this work is supported by the European MaX Centre of Excellence 'Materials design at the Exascale' [MaX](<http://www.max-centre.eu/>) funded by the Horizon 2020 EINFRA-5 program, Grant No. 676598 and under grant agreement No. 824143. This work is further supported by the Joint Lab Virtual Materials Design (JLVMD) of the Forschungszentrum Jülich.

For this work essential is AiiDA, which itself is supported by the [MARVEL National Centre for Competency in Research](<http://nccr-marvel.ch>) funded by the [Swiss National Science Foundation](<http://www.snf.ch/en>).


<img src="docs/source/images/MAX-orizz.png" alt="MaX" width="200"/>
<img src="docs/source/images/Logo-JLVMD.png" alt="JLVMD" width="200"/>

[Fleur v2.0]: https://img.shields.io/badge/->=MaX--1,<=MaX--6.2-darkblue?logoWidth=30&labelColor=white&logo=data:image/png;base64,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

[Fleur v1.2]: https://img.shields.io/badge/->=MaX--1,<=MaX--6-darkblue?logoWidth=30&labelColor=white&logo=data:image/png;base64,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

[Fleur v1.0]: https://img.shields.io/badge/->=MaX--1,<=MaX--4-darkblue?logoWidth=30&labelColor=white&logo=data:image/png;base64,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

[Fleur v0.6.3]: https://img.shields.io/badge/->=MaX--1,<=MaX--3-darkblue?logoWidth=30&labelColor=white&logo=data:image/png;base64,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

[AiiDA v2.0]: https://img.shields.io/badge/AiiDA->=2.0.0,<3.0.0-007ec6.svg?logo=data%3Aimage%2Fpng%3Bbase64%2CiVBORw0KGgoAAAANSUhEUgAAACMAAAAhCAYAAABTERJSAAAABHNCSVQICAgIfAhkiAAAAAlwSFlzAAAFhgAABYYBG6Yz4AAAABl0RVh0U29mdHdhcmUAd3d3Lmlua3NjYXBlLm9yZ5vuPBoAAAUbSURBVFiFzZhrbFRVEMd%2Fc%2B5uu6UUbIFC%2FUAUVEQCLbQJBIiBDyiImJiIhmohYNCkqJAQxASLF8tDgYRHBLXRhIcKNtFEhVDgAxBJqgmVh4JEKg3EIn2QYqBlt917xg%2BFss%2ByaDHOtzsz5z%2B%2FuZl7ztmF%2F5HJvxVQN6cPYX8%2FPLnOmsvNAvqfwuib%2FbNIk9cQeQnLcKRL5xLIV%2Fic9eJeunjPYbRs4FjQSpTB3aS1IpRKeeOOewajy%2FKKEO8Q0DuVdKy8IqsbPulxGHUfCBBu%2BwUYGuFuBTK7wQnht6PEbf4tlRomVRjCbXNjQEB0AyrFQOL5ENIJm7dTLZE6DPJCnEtFZVXDLny%2B4Sjv0PmmYu1ZdUek9RiMgoDmJ8V0L7XJqsZ3UW8YsBOwEeHeeFce7jEYXBy0m9m4BbXqSj2%2Bxnkg26MCVrN6DEZcwggtd8pTFx%2Fh3B9B50YLaFOPwXQKUt0tBLegtSomfBlfY13PwijbEnhztGzgJsK5h9W9qeWwBqjvyhB2iBs1Qz0AU974DciRGO8CVN8AJhAeMAdA3KbrKEtvxhsI%2B9emWiJlGBEU680Cfk%2BSsVqXZvcFYGXjF8ABVJ%2BTNfVXehyms1zzn1gmIOxLEB6E31%2FWBe5rnCarmo7elf7dJEeaLh80GasliI5F6Q9cAz1GY1OJVNDxTzQTw7iY%2FHEZRQY7xqJ9RU2LFe%2FYqakdP911ha0XhjjiTVAkDwgatWfCGeYocx8M3glG8g8EXhSrLrHnEFJ5Ymow%2FkhIYv6ttYUW1iFmEqqxdVoUs9FmsDYSqmtmJh3Cl1%2BVtl2s7owDUdocR5bceiyoSivGTT5vzpbzL1uoBpmcAAQgW7ArnKD9ng9rc%2BNgrobSNwpSkkhcRN%2BvmXLjIsDovYHHEfmsYFygPAnIDEQrQPzJYCOaLHLUfIt7Oq0LJn9fxkSgNCb1qEIQ5UKgT%2Fs6gJmVOOroJhQBXVqw118QtWLdyUxEP45sUpSzqP7RDdFYMyB9UReMiF1MzPwoUqHt8hjGFFeP5wZAbZ%2F0%2BcAtAAcji6LeSq%2FMYiAvSsdw3GtrfVSVFUBbIhwRWYR7yOcr%2FBi%2FB1MSJZ16JlgH1AGM3EO2QnmMyrSbTSiACgFBv4yCUapZkt9qwWVL7aeOyHvArJjm8%2Fz9BhdI4XcZgz2%2FvRALosjsk1ODOyMcJn9%2FYI6IrkS5vxMGdUwou2YKfyVqJpn5t9aNs3gbQMbdbkxnGdsr4bTHm2AxWo9yNZK4PXR3uzhAh%2BM0AZejnCrGdy0UvJxl0oMKgWSLR%2B1LH2aE9ViejiFs%2BXn6bTjng3MlIhJ1I1TkuLdg6OcAbD7Xx%2Bc3y9TrWAiSHqVkbZ2v9ilCo6s4AjwZCzFyD9mOL305nV9aonvsQeT2L0gVk4OwOJqXXVRW7naaxswDKVdlYLyMXAnntteYmws2xcVVZzq%2BtHPAooQggmJkc6TLSusOiL4RKgwzzYU1iFQgiUBA1H7E8yPau%2BZl9P7AblVNebtHqTgxLfRqrNvZWjsHZFuqMqKcDWdlFjF7UGvX8Jn24DyEAykJwNcdg0OvJ4p5pQ9tV6SMlP4A0PNh8aYze1ArROyUNTNouy8tNF3Rt0CSXb6bRFl4%2FIfQzNMjaE9WwpYOWQnOdEF%2BTdJNO0iFh7%2BI0kfORzQZb6P2kymS9oTxzBiM9rUqLWr1WE5G6ODhycQd%2FUnNVeMbcH68hYkGycNoUNWc8fxaxfwhDbHpfwM5oeTY7rUX8QAAAABJRU5ErkJggg%3D%3D

[AiiDA v1.2]: https://img.shields.io/badge/AiiDA->=1.3.0,<2.0.0-007ec6.svg?logo=data%3Aimage%2Fpng%3Bbase64%2CiVBORw0KGgoAAAANSUhEUgAAACMAAAAhCAYAAABTERJSAAAABHNCSVQICAgIfAhkiAAAAAlwSFlzAAAFhgAABYYBG6Yz4AAAABl0RVh0U29mdHdhcmUAd3d3Lmlua3NjYXBlLm9yZ5vuPBoAAAUbSURBVFiFzZhrbFRVEMd%2Fc%2B5uu6UUbIFC%2FUAUVEQCLbQJBIiBDyiImJiIhmohYNCkqJAQxASLF8tDgYRHBLXRhIcKNtFEhVDgAxBJqgmVh4JEKg3EIn2QYqBlt917xg%2BFss%2ByaDHOtzsz5z%2B%2FuZl7ztmF%2F5HJvxVQN6cPYX8%2FPLnOmsvNAvqfwuib%2FbNIk9cQeQnLcKRL5xLIV%2Fic9eJeunjPYbRs4FjQSpTB3aS1IpRKeeOOewajy%2FKKEO8Q0DuVdKy8IqsbPulxGHUfCBBu%2BwUYGuFuBTK7wQnht6PEbf4tlRomVRjCbXNjQEB0AyrFQOL5ENIJm7dTLZE6DPJCnEtFZVXDLny%2B4Sjv0PmmYu1ZdUek9RiMgoDmJ8V0L7XJqsZ3UW8YsBOwEeHeeFce7jEYXBy0m9m4BbXqSj2%2Bxnkg26MCVrN6DEZcwggtd8pTFx%2Fh3B9B50YLaFOPwXQKUt0tBLegtSomfBlfY13PwijbEnhztGzgJsK5h9W9qeWwBqjvyhB2iBs1Qz0AU974DciRGO8CVN8AJhAeMAdA3KbrKEtvxhsI%2B9emWiJlGBEU680Cfk%2BSsVqXZvcFYGXjF8ABVJ%2BTNfVXehyms1zzn1gmIOxLEB6E31%2FWBe5rnCarmo7elf7dJEeaLh80GasliI5F6Q9cAz1GY1OJVNDxTzQTw7iY%2FHEZRQY7xqJ9RU2LFe%2FYqakdP911ha0XhjjiTVAkDwgatWfCGeYocx8M3glG8g8EXhSrLrHnEFJ5Ymow%2FkhIYv6ttYUW1iFmEqqxdVoUs9FmsDYSqmtmJh3Cl1%2BVtl2s7owDUdocR5bceiyoSivGTT5vzpbzL1uoBpmcAAQgW7ArnKD9ng9rc%2BNgrobSNwpSkkhcRN%2BvmXLjIsDovYHHEfmsYFygPAnIDEQrQPzJYCOaLHLUfIt7Oq0LJn9fxkSgNCb1qEIQ5UKgT%2Fs6gJmVOOroJhQBXVqw118QtWLdyUxEP45sUpSzqP7RDdFYMyB9UReMiF1MzPwoUqHt8hjGFFeP5wZAbZ%2F0%2BcAtAAcji6LeSq%2FMYiAvSsdw3GtrfVSVFUBbIhwRWYR7yOcr%2FBi%2FB1MSJZ16JlgH1AGM3EO2QnmMyrSbTSiACgFBv4yCUapZkt9qwWVL7aeOyHvArJjm8%2Fz9BhdI4XcZgz2%2FvRALosjsk1ODOyMcJn9%2FYI6IrkS5vxMGdUwou2YKfyVqJpn5t9aNs3gbQMbdbkxnGdsr4bTHm2AxWo9yNZK4PXR3uzhAh%2BM0AZejnCrGdy0UvJxl0oMKgWSLR%2B1LH2aE9ViejiFs%2BXn6bTjng3MlIhJ1I1TkuLdg6OcAbD7Xx%2Bc3y9TrWAiSHqVkbZ2v9ilCo6s4AjwZCzFyD9mOL305nV9aonvsQeT2L0gVk4OwOJqXXVRW7naaxswDKVdlYLyMXAnntteYmws2xcVVZzq%2BtHPAooQggmJkc6TLSusOiL4RKgwzzYU1iFQgiUBA1H7E8yPau%2BZl9P7AblVNebtHqTgxLfRqrNvZWjsHZFuqMqKcDWdlFjF7UGvX8Jn24DyEAykJwNcdg0OvJ4p5pQ9tV6SMlP4A0PNh8aYze1ArROyUNTNouy8tNF3Rt0CSXb6bRFl4%2FIfQzNMjaE9WwpYOWQnOdEF%2BTdJNO0iFh7%2BI0kfORzQZb6P2kymS9oTxzBiM9rUqLWr1WE5G6ODhycQd%2FUnNVeMbcH68hYkGycNoUNWc8fxaxfwhDbHpfwM5oeTY7rUX8QAAAABJRU5ErkJggg%3D%3D

[AiiDA v1.0]: https://img.shields.io/badge/AiiDA->=1.3.0,<2.0.0-007ec6.svg?logo=data%3Aimage%2Fpng%3Bbase64%2CiVBORw0KGgoAAAANSUhEUgAAACMAAAAhCAYAAABTERJSAAAABHNCSVQICAgIfAhkiAAAAAlwSFlzAAAFhgAABYYBG6Yz4AAAABl0RVh0U29mdHdhcmUAd3d3Lmlua3NjYXBlLm9yZ5vuPBoAAAUbSURBVFiFzZhrbFRVEMd%2Fc%2B5uu6UUbIFC%2FUAUVEQCLbQJBIiBDyiImJiIhmohYNCkqJAQxASLF8tDgYRHBLXRhIcKNtFEhVDgAxBJqgmVh4JEKg3EIn2QYqBlt917xg%2BFss%2ByaDHOtzsz5z%2B%2FuZl7ztmF%2F5HJvxVQN6cPYX8%2FPLnOmsvNAvqfwuib%2FbNIk9cQeQnLcKRL5xLIV%2Fic9eJeunjPYbRs4FjQSpTB3aS1IpRKeeOOewajy%2FKKEO8Q0DuVdKy8IqsbPulxGHUfCBBu%2BwUYGuFuBTK7wQnht6PEbf4tlRomVRjCbXNjQEB0AyrFQOL5ENIJm7dTLZE6DPJCnEtFZVXDLny%2B4Sjv0PmmYu1ZdUek9RiMgoDmJ8V0L7XJqsZ3UW8YsBOwEeHeeFce7jEYXBy0m9m4BbXqSj2%2Bxnkg26MCVrN6DEZcwggtd8pTFx%2Fh3B9B50YLaFOPwXQKUt0tBLegtSomfBlfY13PwijbEnhztGzgJsK5h9W9qeWwBqjvyhB2iBs1Qz0AU974DciRGO8CVN8AJhAeMAdA3KbrKEtvxhsI%2B9emWiJlGBEU680Cfk%2BSsVqXZvcFYGXjF8ABVJ%2BTNfVXehyms1zzn1gmIOxLEB6E31%2FWBe5rnCarmo7elf7dJEeaLh80GasliI5F6Q9cAz1GY1OJVNDxTzQTw7iY%2FHEZRQY7xqJ9RU2LFe%2FYqakdP911ha0XhjjiTVAkDwgatWfCGeYocx8M3glG8g8EXhSrLrHnEFJ5Ymow%2FkhIYv6ttYUW1iFmEqqxdVoUs9FmsDYSqmtmJh3Cl1%2BVtl2s7owDUdocR5bceiyoSivGTT5vzpbzL1uoBpmcAAQgW7ArnKD9ng9rc%2BNgrobSNwpSkkhcRN%2BvmXLjIsDovYHHEfmsYFygPAnIDEQrQPzJYCOaLHLUfIt7Oq0LJn9fxkSgNCb1qEIQ5UKgT%2Fs6gJmVOOroJhQBXVqw118QtWLdyUxEP45sUpSzqP7RDdFYMyB9UReMiF1MzPwoUqHt8hjGFFeP5wZAbZ%2F0%2BcAtAAcji6LeSq%2FMYiAvSsdw3GtrfVSVFUBbIhwRWYR7yOcr%2FBi%2FB1MSJZ16JlgH1AGM3EO2QnmMyrSbTSiACgFBv4yCUapZkt9qwWVL7aeOyHvArJjm8%2Fz9BhdI4XcZgz2%2FvRALosjsk1ODOyMcJn9%2FYI6IrkS5vxMGdUwou2YKfyVqJpn5t9aNs3gbQMbdbkxnGdsr4bTHm2AxWo9yNZK4PXR3uzhAh%2BM0AZejnCrGdy0UvJxl0oMKgWSLR%2B1LH2aE9ViejiFs%2BXn6bTjng3MlIhJ1I1TkuLdg6OcAbD7Xx%2Bc3y9TrWAiSHqVkbZ2v9ilCo6s4AjwZCzFyD9mOL305nV9aonvsQeT2L0gVk4OwOJqXXVRW7naaxswDKVdlYLyMXAnntteYmws2xcVVZzq%2BtHPAooQggmJkc6TLSusOiL4RKgwzzYU1iFQgiUBA1H7E8yPau%2BZl9P7AblVNebtHqTgxLfRqrNvZWjsHZFuqMqKcDWdlFjF7UGvX8Jn24DyEAykJwNcdg0OvJ4p5pQ9tV6SMlP4A0PNh8aYze1ArROyUNTNouy8tNF3Rt0CSXb6bRFl4%2FIfQzNMjaE9WwpYOWQnOdEF%2BTdJNO0iFh7%2BI0kfORzQZb6P2kymS9oTxzBiM9rUqLWr1WE5G6ODhycQd%2FUnNVeMbcH68hYkGycNoUNWc8fxaxfwhDbHpfwM5oeTY7rUX8QAAAABJRU5ErkJggg%3D%3D

[AiiDA v0.6.3]: https://img.shields.io/badge/AiiDA->=0.12,<1.0.0-007ec6.svg?logo=data%3Aimage%2Fpng%3Bbase64%2CiVBORw0KGgoAAAANSUhEUgAAACMAAAAhCAYAAABTERJSAAAABHNCSVQICAgIfAhkiAAAAAlwSFlzAAAFhgAABYYBG6Yz4AAAABl0RVh0U29mdHdhcmUAd3d3Lmlua3NjYXBlLm9yZ5vuPBoAAAUbSURBVFiFzZhrbFRVEMd%2Fc%2B5uu6UUbIFC%2FUAUVEQCLbQJBIiBDyiImJiIhmohYNCkqJAQxASLF8tDgYRHBLXRhIcKNtFEhVDgAxBJqgmVh4JEKg3EIn2QYqBlt917xg%2BFss%2ByaDHOtzsz5z%2B%2FuZl7ztmF%2F5HJvxVQN6cPYX8%2FPLnOmsvNAvqfwuib%2FbNIk9cQeQnLcKRL5xLIV%2Fic9eJeunjPYbRs4FjQSpTB3aS1IpRKeeOOewajy%2FKKEO8Q0DuVdKy8IqsbPulxGHUfCBBu%2BwUYGuFuBTK7wQnht6PEbf4tlRomVRjCbXNjQEB0AyrFQOL5ENIJm7dTLZE6DPJCnEtFZVXDLny%2B4Sjv0PmmYu1ZdUek9RiMgoDmJ8V0L7XJqsZ3UW8YsBOwEeHeeFce7jEYXBy0m9m4BbXqSj2%2Bxnkg26MCVrN6DEZcwggtd8pTFx%2Fh3B9B50YLaFOPwXQKUt0tBLegtSomfBlfY13PwijbEnhztGzgJsK5h9W9qeWwBqjvyhB2iBs1Qz0AU974DciRGO8CVN8AJhAeMAdA3KbrKEtvxhsI%2B9emWiJlGBEU680Cfk%2BSsVqXZvcFYGXjF8ABVJ%2BTNfVXehyms1zzn1gmIOxLEB6E31%2FWBe5rnCarmo7elf7dJEeaLh80GasliI5F6Q9cAz1GY1OJVNDxTzQTw7iY%2FHEZRQY7xqJ9RU2LFe%2FYqakdP911ha0XhjjiTVAkDwgatWfCGeYocx8M3glG8g8EXhSrLrHnEFJ5Ymow%2FkhIYv6ttYUW1iFmEqqxdVoUs9FmsDYSqmtmJh3Cl1%2BVtl2s7owDUdocR5bceiyoSivGTT5vzpbzL1uoBpmcAAQgW7ArnKD9ng9rc%2BNgrobSNwpSkkhcRN%2BvmXLjIsDovYHHEfmsYFygPAnIDEQrQPzJYCOaLHLUfIt7Oq0LJn9fxkSgNCb1qEIQ5UKgT%2Fs6gJmVOOroJhQBXVqw118QtWLdyUxEP45sUpSzqP7RDdFYMyB9UReMiF1MzPwoUqHt8hjGFFeP5wZAbZ%2F0%2BcAtAAcji6LeSq%2FMYiAvSsdw3GtrfVSVFUBbIhwRWYR7yOcr%2FBi%2FB1MSJZ16JlgH1AGM3EO2QnmMyrSbTSiACgFBv4yCUapZkt9qwWVL7aeOyHvArJjm8%2Fz9BhdI4XcZgz2%2FvRALosjsk1ODOyMcJn9%2FYI6IrkS5vxMGdUwou2YKfyVqJpn5t9aNs3gbQMbdbkxnGdsr4bTHm2AxWo9yNZK4PXR3uzhAh%2BM0AZejnCrGdy0UvJxl0oMKgWSLR%2B1LH2aE9ViejiFs%2BXn6bTjng3MlIhJ1I1TkuLdg6OcAbD7Xx%2Bc3y9TrWAiSHqVkbZ2v9ilCo6s4AjwZCzFyD9mOL305nV9aonvsQeT2L0gVk4OwOJqXXVRW7naaxswDKVdlYLyMXAnntteYmws2xcVVZzq%2BtHPAooQggmJkc6TLSusOiL4RKgwzzYU1iFQgiUBA1H7E8yPau%2BZl9P7AblVNebtHqTgxLfRqrNvZWjsHZFuqMqKcDWdlFjF7UGvX8Jn24DyEAykJwNcdg0OvJ4p5pQ9tV6SMlP4A0PNh8aYze1ArROyUNTNouy8tNF3Rt0CSXb6bRFl4%2FIfQzNMjaE9WwpYOWQnOdEF%2BTdJNO0iFh7%2BI0kfORzQZb6P2kymS9oTxzBiM9rUqLWr1WE5G6ODhycQd%2FUnNVeMbcH68hYkGycNoUNWc8fxaxfwhDbHpfwM5oeTY7rUX8QAAAABJRU5ErkJggg%3D%3D
