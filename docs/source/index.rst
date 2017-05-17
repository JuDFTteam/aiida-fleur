.. fleur_plugin documentation master file, created by
   sphinx-quickstart on Wed Aug 10 10:20:55 2016.
   You can adapt this file completely to your liking, but it should at least
   contain the root `toctree` directive.


Welcome to Fleur plug-in's documentation!
=========================================

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




This plugin enables the use of the all-electron DFT code Fleur (http://www.flapw.de) with the AiiDA framework (http://www.aiida.net).
The plugin is all in python, under the MIT license and is available under (https://github.com/broeder-j/aiida_fleur_plugin). It is developed at Forschungszentrum Juelich, (IAS-1/PGI-1), Germany.

.. note:: On these pages is the documentation of the plugin source code, some design description, usuage examples and tutorials of the plugin. For futher PGI-1 interal hints go to the Fleur website. Basic AiiDA workflows for Fleur are available on https://github.com/broeder-j/aiida_fleur_basewf .

If you use this plugin please cite:

* for the plugin: (to come)
* for fleur: http:/www.flapw.de 


Requirements to use this code:
..............................

* A running AiiDA version
* Executables of the Fleur code

Other packages (in addition to all requirements of AiiDA):

* lxml

Acknowledgments:
...............

We acknowledge partial support from the EU Centre of Excellence “MaX – Materials Design at the Exascale” (http://www.max-centre.eu). (Horizon 2020 EINFRA-5, Grant No. 676598)
We also thank the AiiDA team for their help.

Contents:
.........

The Fleur plug-in
+++++++++++++++++

.. toctree::
   :maxdepth: 4

   plugin/fleur_plugin
..
   examples

Guides
++++++
.. toctree::
   :maxdepth: 4

..
  installation
  run inpgen
  run fleur
  change fleurinp
  extract results


Tools and utility
+++++++++++++++++

.. toctree::
   :maxdepth: 4

..
  plugin/utility

Code documentation
++++++++++++++++++

.. toctree::
   :maxdepth: 4

   code

..   
   utility
   workflows
   documentation_fleur_plugin


Indices and tables
==================

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`

