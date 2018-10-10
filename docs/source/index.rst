.. fleur_fleur documentation master file, created by
   sphinx-quickstart on Wed Aug 10 10:20:55 2016.
   You can adapt this file completely to your liking, but it should at least
   contain the root `toctree` directive.

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
.. _registry: https://aiidateam.github.io/aiida-registry


The aiida-fleur python package enables the use of the all-electron DFT code Fleur (http://www.flapw.de) with the `AiiDA`_ framework (http://www.aiida.net).
The package contains plugins for the `FLEUR`_ code, inputgenerator and a datastructure. Further it contains basic workflows and utility. 
It open source under the MIT license and is available under (https://github.com/broeder-j/aiida-fleur). 
It is developed within the MaX EU Center of Excellence (www.max-center.eu) at Forschungszentrum Jülich GmbH (http://www.fz-juelich.de/pgi/pgi-1/DE/Home/home_node.html), (IAS-1/PGI-1), Germany.
Check out the AiiDA `registry`_ to find out more about what other packages for AiiDA exists, that might be helpful for you.

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
* masci-tools

Installation Instructions:
--------------------------

Install from pypi the latest release::

    $ pip install aiida-fleur


or from the aiida-fleur source folder any branch::

    $ pip install .
    # or which is very useful to keep track of the changes (developers)
    $ pip install -e . 

Acknowledgments:
----------------

We acknowledge partial support from the EU Centre of Excellence “MaX – Materials Design at the Exascale” (http://www.max-centre.eu). (Horizon 2020 EINFRA-5, Grant No. 676598)
We thank the AiiDA team for their help and work. Also the vial exchange with developers of AiiDA packages for other codes was inspireing.

User's Guide
############

.. toctree::
   :maxdepth: 4

   user_guide/index

  
Developer's Guide
#################

.. toctree::
   :maxdepth: 4

   devel_guide/index

Module reference (API)
######################

.. toctree::
   :maxdepth: 4

   module_guide/code
      


Indices and tables
##################

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`

