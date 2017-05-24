FLEUR AiiDA basic workflow
===================
**Common workflows with the all-electron DFT [FLEUR code](http://www.flapw.de) using the [AiiDA framework](http://www.aiida.net)**  
Developed at the Forschungszentrum Jülich GmbH  

License:
--------
MIT license.
See license file.


Comments/Disclaimer:
--------------------
The workflows will only work with a Fleur version using xml files as I/O,  
For example check out the Fleur version released withing MAX. 
It also needs the AiiDA Fleur plugin and a running AiiDA version.

WARNING: This is a beta version, which runs, but is still under development.  
For anything contact j.broeder@fz-juelich.de


Contents
--------
1. [Introduction](#Introduction)
2. [Installation Instructions](#Installation)
3. [Code Dependencies](#Dependencies)
4. [Further Information](#FurtherInfo)

Introduction <a name="Introduction"></a>
========================================

This are basic workflows for the FLEUR-code,
which is an all-electron DFT code using the FLAPW method.
FLEUR is used in the material science and physics community.

So far the following workflows are in this package:

convergence : SCF-cycle of Fleur. Converge the charge density and the Total energy with multiple FLEUR runs

eos : Calculate and Equation of States (Lattice constant) with FLEUR
dos : Calculate a Density of States (DOS) with FLEUR
bands : Calculate a Band structure with FLEUR
relaxation : Relax a crystal structure with FLEUR

See the AiiDA documentation for general info about the AiiDA workflow system or how to write workflows.

Installation Instructions <a name="Installation"></a>
=====================================================

today:
The python source files of the plug-in have to be placed in the AiiDA source code in certain places. 
You might use the copy_plugin_files.sh script to do so.

in the near future:
pip install aiida_fleur_basicwf


Files
-----
...

Also some common routines '/aiida_fleur/tools/' used by some classes have to be placed currently under:
aiida.tools.codespecific.fleur 


Code Dependencies <a name="Dependencies"></a>
=============================================

Requirements are listed in 'requirements.txt'.

Further Information <a name="FurtherInfo"></a>
=============================================

The source code documentation is here (will be on read_the_docs soon).  
A full documentation of the usage is found at www.flapw.de.   
Some examples can be found in 'examples'.







