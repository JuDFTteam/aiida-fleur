FLEUR AiiDA plug-in
===================
**Enables the usage of the [FLEUR code](http://www.flapw.de) with the [AiiDA framework](http://www.aiida.net)**  
Developed at the Forschungszentrum Jülich GmbH  

License:
--------
MIT license.
See license file.


Comments/Disclaimer:
--------------------
The plug-in will only work with a Fleur version using xml files as I/O.  
For example check out the Fleur version released withing MAX. 

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

This is an AiiDA plug-in for the Fleur code.  

The Fleur plug-in consists of a datastructure called FleurinpData and two plug-ins,  
one for the Fleur inputgenerator (inpgen) and one for a Fleur calculation itself.

Every plug-in has an input part and an output parser, see the AiiDA documentation for general info.

Installation Instructions <a name="Installation"></a>
=====================================================

today:
The python source files of the plug-in have to be placed in the AiiDA source code in certain places. 
You might use the copy_plugin_files.py script to do so.

in the near future:
pip install aiida_fleur


Files
-----

fleurinpData : aiida.orm.data.fleurinp.__init__.py   
fleurinpModifier : aiida.orm.data.fleurinp.fleurinpmodifier.py

fleurinpgen calculation: aiida.orm.calculation.job.fleur_inp.fleurinputgen.py  
fleurinpgen output parser: aiida.parsers.plugins.fleur_inp.fleur_inputgen.py  

fleur calculation: aiida.orm.calculation.job.fleur_inp.fleur.py  
fleur output parser: aiida.parsers.plugins.fleur_inp.fleur.py   

The Fleur code needs a XMLSchema file, place them under:  
aiida.orm.calculation.job.fleur_inp.fleur_schema

Also some common routines '/aiida_fleur/tools/' used by some classes have to be placed currently under:
aiida.tools.codespecific.fleur 


Code Dependencies <a name="Dependencies"></a>
=============================================

Requirements are listed in 'fleur_plugin_requirements.txt'.

Further Information <a name="FurtherInfo"></a>
=============================================

The plug-in source code documentation is here (will be on read_the_docs soon).  
A full documentation of the plug-in and its usage is found at www.flapw.de.   
Two usage examples are shown in 'examples'.







