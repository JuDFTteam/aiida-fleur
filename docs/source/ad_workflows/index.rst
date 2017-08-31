.. fleur_plugin documentation master file, created by
   sphinx-quickstart on Wed Aug 10 10:20:55 2016.
   You can adapt this file completely to your liking, but it should at least
   contain the root `toctree` directive.


Welcome to the documentation of corelevel Workflows for Fleur!
==========================================================

.. image:: images/fleur.png
    :width: 20%
    :align: left
    :height: 60px
.. image:: images/MAX-orizz.jpeg
    :width: 35%
    :align: right
    :height: 200px
.. image:: images/AiiDA_transparent_logo.png
    :width: 35%
    :align: center
    :height: 300px


..


Framework for computational science

..




The workflows you find here enable you to run certain simulations with the all-electron DFT code Fleur (http://www.flapw.de) and the AiiDA framework (http://www.aiida.net).
The workflows are all in python, under the MIT license (see license file) and are availabe on github (https://github.com/broeder-j/aiida_fleur_basewf). They are developed at Forschungszentrum Juelich, (IAS-1/PGI-1), Germany.

.. note:: On these pages is (only) the documentation of the source code so far. For design description, usuage examples and tutorials go to the Fleur website.

If you use these workflows please cite:

* the aiida_fleur_plugin: (to come)
* for fleur: http:/www.flapw.de 


Requirements to use this code:

* A running AiiDA version
* The Fleur plugin for AiiDA
* Basic Fleur workflows
* Executables of the Fleur code


Python Packages (in addition to all requirements of AiiDA):

* aiida
* aiida_fleur
* aiida_fleur_basewf

Installation:

pip install aiida_fleur_corewf

Acknowlegments:

We acknowledge partial support from the EU Centre of Excellence “MaX – Materials Design at the Exascale” (http://www.max-centre.eu). (Horizon 2020 EINFRA-5, Grant No. 676598)
We also thank the AiiDA team for their help, guidance on the software side and the IEK-4 at Forschungszentrum Juelich for their support.


Contents:

Common Fleur Workflows and Tools
++++++++++++++++++++++++++++++++

.. toctree::
   :maxdepth: 4

   workflows
   utility
   tests
.. 
   code  
   examples



Indices and tables
==================

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`

