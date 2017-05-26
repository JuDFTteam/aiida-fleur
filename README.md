FLEUR with AiiDA
================
**Contains a plugin that enables the usage of the all-electron DFT [FLEUR code](http://www.flapw.de) with the [AiiDA framework](http://www.aiida.net). Further this package contains common workflows and some utility.**  
Developed at the Forschungszentrum Jülich GmbH  


Documentation
-------------
blas

License:
--------
MIT license.
See license file.


Comments/Disclaimer:
--------------------
The plug-in and the workflows will only work with a Fleur version using xml files as I/O.  
For example check out the Fleur version released withing MAX.

WARNING: This is a beta version, which runs, but is still under development.  
For anything contact j.broeder@fz-juelich.de feel free to write issues and contribute.


Contents
--------
1. [Introduction](#Introduction)
2. [Installation Instructions](#Installation)
3. [Code Dependencies](#Dependencies)
4. [Further Information](#FurtherInfo)

Introduction <a name="Introduction"></a>
========================================

This is the basic package (plugin plus workflows) to use the FLEUR-code with the AiiDA Framework.
The FLEUR-code is an all-electron DFT code using the FLAPW method,
and widely applied in the material science and physics community.  

The plugin :

The Fleur plug-in consists of a datastructure called FleurinpData and two plug-ins,  
one for the Fleur inputgenerator (inpgen) and one for a Fleur calculation itself.

Every plug-in has an input part and an output parser, see the AiiDA documentation for general info.


So far the following workflows are in this package:

scf : SCF-cycle of Fleur. Converge the charge density and the Total energy with multiple FLEUR runs

eos : Calculate and Equation of States (Lattice constant) with FLEUR
dos : Calculate a Density of States (DOS) with FLEUR
bands : Calculate a Band structure with FLEUR
relaxation : Relax a crystal structure with FLEUR

See the AiiDA documentation for general info about the AiiDA workflow system or how to write workflows.


Utility/tools:

Structure_util.py : constains some methods to handle AiiDA structures 
(some of them might now be methods of the AiiDA structureData, if so use them from there!)

merge_parameter.py : methods to handle parameterData nodes, i.e merge them. Which is very useful for all-electron codes, because instead of pseudo potentialsfamilies you can create now families of parameter nodes for the periodic table.

xml_util.py : all xml functions that are used, by parsers and other tools are in here. Some are 'general' some a very specific to Fleur.

read_cif.py : this can be used as stand-alone to create StructureData nodes from .cif files from an directory tree. 

Installation Instructions <a name="Installation"></a>
=====================================================

From the aiida-fleur folder use:

    $ pip install .
    # or which is very useful to keep track of the changes (developers)
    $ pip install -e . 

To uninstall use:

    $ pip uninstall aiida-fleur

Soon (When package on pypi):
    $ pip install aiida-fleur

Alternative (old)
The python source files of the plug-in have to be placed in the AiiDA source code in certain places. 
You might use the copy_plugin_files.sh script to do so.

To test wether the installation was successful use::

   $ verdi calculation plugins 

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
   * fleur.scf
   * fleur.eos
   * fleur.band
   * fleur.dos

You should see fleur.* in the list


Files/Contents
--------------

Plugin files:

Data:
fleurinpData : aiida_fleur.data.fleurinp.py
fleurinpModifier : aiida_fleur.data.fleurinpmodifier.py

Calculations:
FleurinputgenCalculation: aiida_fleur.calculation.fleurinputgen.py  
FleurCalculation: aiida_fleur.calculation.fleur.py  

Parsers:
FleurinpgenParser: aiida_fleur.parsers.fleur_inputgen.py  
FleurParser: aiida_fleur.parsers.fleur.py   

XML Schema Files:

In the folder fleur_schema

The Fleur code needs a XMLSchema file, the plugin searches (walks) for them in your PYTHONPATH.
Therefore make sure the plugin folder under you PYTHONPATH env variable. 
If nothing works add a path to search_path in fleurinp.py (hack).

Workflows/workchains:

fleur_scf_wc : aiida_fleur.workflows.scf.py
fleur_eos_wc : aiida_fleur.workflows.eos.py
fleur_dos_wc : aiida_fleur.workflows.dos.py
fleur_band_wc : aiida_fleur.workflows.band.py
fleur_relax_wc : aiida_fleur.workflows.relax.py


Utility under '/aiida_fleur/tools/':

Structure_util.py
merge_parameter.py
read_cif.py
...


Code Dependencies <a name="Dependencies"></a>
=============================================

Requirements are listed in 'requirements.txt'.

aiida_core
lxml
ase

Mainly AiiDA:

1. Download from [www.aiida.net/?page_id=264](www.aiida.net -> Download)
2. install and setup -> [http://aiida-core.readthedocs.org/en/stable/](aiida's documentation)

For easy ploting we recommend installing 'plot_methods':
https://bitbucket.org/broeder-j/plot_methods

Further Information <a name="FurtherInfo"></a>
=============================================

The plug-in source code documentation is here [].  
also some documentation of the plug-in, further things can be found at www.flapw.de.   
Two usage examples are shown in 'examples'.







