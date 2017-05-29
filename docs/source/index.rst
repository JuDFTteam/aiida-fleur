.. fleur_fleur documentation master file, created by
   sphinx-quickstart on Wed Aug 10 10:20:55 2016.
   You can adapt this file completely to your liking, but it should at least
   contain the root `toctree` directive.


Welcome to the AiiDA-FLEUR 's documentation!
++++++++++++++++++++++++++++++++++++++++++++

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




The aiida-fleur python package enables the use of the all-electron DFT code Fleur (http://www.flapw.de) with the AiiDA framework (http://www.aiida.net).
The package contains plugins for the Fleur code, inpgen and a datastructure. Further it contains basic workflows and utility. 
It stands under the MIT license and is available under (https://github.com/broeder-j/aiida-fleur). 
It is developed within the MaX EU Center of Excellence (www.max-center.eu) at Forschungszentrum Jülich GmbH (http://www.fz-juelich.de/pgi/pgi-1/DE/Home/home_node.html), (IAS-1/PGI-1), Germany.

.. note:: On these pages is the documentation of the aiida-fleur source code, some design description, usuage examples and tutorials of the plugin. For futher PGI-1 interal hints go to the Fleur wiki.

If you use this package please cite:

* for the plugin and workflows: (to come)
* for fleur: http:/www.flapw.de 


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

From the aiida-fleur folder use::

    $ pip install .
    # or which is very useful to keep track of the changes (developers)
    $ pip install -e . 

To uninstall use::

    $ pip uninstall aiida-fleur

Soon (When package on pypi)::

    $ pip install aiida-fleur

Alternative (old):
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

