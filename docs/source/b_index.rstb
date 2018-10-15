.. fleur_fleur documentation master file, created by
   sphinx-quickstart on Wed Aug 10 10:20:55 2016.
   You can adapt this file completely to your liking, but it should at least
   contain the root `toctree` directive.

##############################################
Welcome to the `AiiDA-FLEUR`_'s documentation!
##############################################


.. figure:: images/fleur.png
    :width: 25 %
    :align: center
.. figure:: images/MAX-orizz.eps
    :width: 50 %
    :align: center
.. figure:: images/AiiDA_transparent_logo.png
    :width: 50 %
    :align: center

.. _AiiDA: http://www.aiida.net
.. _FLEUR: http://www.flapw.de
.. _AIIDA-FLEUR: https://github.com/broeder-j/aiida-fleur



The aiida-fleur python package enables the use of the all-electron DFT code Fleur (http://www.flapw.de) with the AiiDA framework (http://www.aiida.net).
The package contains plugins for the Fleur code, inputgenerator and a datastructure. Further it contains basic workflows and utility. 
It open source under the MIT license and is available under (https://github.com/broeder-j/aiida-fleur). 
It is developed within the MaX EU Center of Excellence (www.max-center.eu) at Forschungszentrum Jülich GmbH (http://www.fz-juelich.de/pgi/pgi-1/DE/Home/home_node.html), (IAS-1/PGI-1), Germany.

.. note:: On these pages is the documentation of the aiida-fleur source code, some design description, usuage examples and tutorials of the plugin. For futher PGI-1 interal hints go to the Fleur wiki.

If you use this package please cite:

* for the plugin and workflows: (to come)
* for fleur: http:/www.flapw.de 


User's Guide
++++++++++++

.. toctree::



Developer's Guide
+++++++++++++++++




Requirements to use this code:
------------------------------

* A running AiiDA version (and postgresql database)
* Executables of the Fleur code

Other packages (in addition to all requirements of AiiDA):

* lxml
* ase

Acknowledgments:
----------------

We acknowledge partial support from the EU Centre of Excellence “MaX – Materials Design at the Exascale” (http://www.max-centre.eu). (Horizon 2020 EINFRA-5, Grant No. 676598)
We also thank the AiiDA team for their help.

Installation Instructions:
--------------------------

Install from pypi the latest release::

    $ pip install aiida-fleur


From the aiida-fleur folder use::

    $ pip install .
    # or which is very useful to keep track of the changes (developers)
    $ pip install -e . 

To uninstall use::

    $ pip uninstall aiida-fleur


To test if the installation was successful use::

$ verdi calculation plugins

   # example output:

   ## Pass as a further parameter one (or more) plugin names
   ## to get more details on a given plugin.
   * calculation
   * codtools.cifcellcontents
   * codtools.cifcodcheck
   * codtools.cifcodnumbers
   * codtools.ciffilter
   * codtools.cifsplitprimitive
   ...
   * fleur.fleur
   * fleur.inpgen


You should see fleur.* in the list

Also run the basics tests under aiida_fleur/aiida_fleur/tests/::

    $ ./run_all_cov.sh

Workflows tests under /aiida_fleur/aiida_fleur/tests/workflow_tests/ have to be currently run manual, 
after modifing run_workflow.sh with the code you want to use and workflows you want to test::

    $ ./run_all_workflow_tests.sh
    
after the workflow have finished running, either check manual, or execute::

    $ ./generate_workflow_test_report.sh



Contents:
---------

The Fleur plug-in
=================

.. toctree::
   :maxdepth: 4

   plugin/fleur_plugin
..
   examples

Common Fleur Workflows
======================

.. toctree::
   :maxdepth: 4

   workflows/index
..
   utility
   tests
   code  
   examples

Guides/tutorials
================
.. toctree::
   :maxdepth: 4

   guides/guides
..
  installation
  run inpgen
  run fleur
  change fleurinp
  extract results


Tools and utility
=================

.. toctree::
   :maxdepth: 4
   
   tools/tools
..
  plugin/utility

FAQ
===

.. toctree::
   :maxdepth: 4
   
   plugin/hints_faq

Source code documentation
=========================

.. toctree::
   :maxdepth: 4

   code

..   
   utility
   workflows
   documentation_fleur_plugin



Indices and tables
------------------

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`

