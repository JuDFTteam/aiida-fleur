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
.. _registry: https://aiidateam.github.io/aiida-registry
.. _OQMD: http://oqmd.org

The AiiDA-FLEUR python package enables the use of the all-electron Density Functional Theory (DFT)
code FLEUR (http://www.flapw.de) with the `AiiDA`_ framework (http://www.aiida.net).

It is open source under the MIT license and is available under
(https://github.com/JuDFTteam/aiida-fleur).
The package is developed within the MaX EU Center of Excellence (www.max-center.eu) at
Forschungszentrum Jülich GmbH (http://www.fz-juelich.de/pgi/pgi-1/DE/Home/home_node.html),
(IAS-1/PGI-1), Germany.
Check out the AiiDA `registry`_ to find out more about what other packages for AiiDA exists,
that might be helpful for you.


If you use this package please cite:

* The plugin and workflows: 
  
  J. Broeder, D. Wortmann, and S. Blügel, 
  Using the AiiDA-FLEUR package for all-electron ab initio electronic structure 
  data generation and processing in materials science, 
  In Extreme Data Workshop 2018 Proceedings, 2019, vol 40, p 43-48
  


* The FLEUR code: http:/www.flapw.de

****************************************
Features, Illustrations, Usage examples:
****************************************


.. topic:: Example 1, Full Provenance tracking trough AiiDA:

    AiiDA graph visualization of a small database containing about 130 000 nodes
    from Fleur calculations. (Visualized with Gephi)

    .. figure:: images/aiida_work2_ed.png
        :width: 100 %
        :align: center

.. topic:: Example 2, Material screening:

    Fleur SCF convergence of 1362 different screened Binary systems managed by the scf workchain

    .. figure:: images/convergence_all_MP_metals.png
        :width: 100 %
        :align: center


.. topic:: Example 3 Method robustness, tuning:

    FLAPW muffin tin radii for all materials (>820000) in the `OQMD`_ .

    .. figure:: images/all_rmts_oqmd.png
        :width: 100 %
        :align: center


.. topic:: Example 4, DFT Code Interoperability:

    If an DFT code has an AiiDA plugin,
    one can run successive calculations using different codes.
    For example, it is possible to perform a structure relaxation with VASP or Quantum Espresso and
    run an all-electron FLEUR workflow for the output structure.

    .. figure:: images/plot_fleur_capabilities.png
        :width: 100 %
        :align: center

.. topic:: Example 5, Quick Visualizations:

    AiiDA-FLEUR contains a function ('plot_fleur') to get a quick visualization of some database node(s).
    For example, to make a convergence plot of one or several SCF runs in your scripts, or notebook.::

       plot_fleur(scf_node)

    .. figure:: images/plot_fleur_scf1.png
        :width: 80 %
        :align: center

    ::

       plot_fleur(scf_node_list)

    .. figure:: images/plot_fleur_scf_m1.png
        :width: 80 %
        :align: center

**************
Basic overview
**************


Requirements to use this code:
==============================

* A running AiiDA version (and postgresql database)
* Executables of the Fleur code

Other packages (in addition to all requirements of AiiDA):

* lxml
* ase
* masci-tools

AiiDA-package Layout:
=====================

#. :ref:`Fleur input generator<inpgen_plugin>`
#. :ref:`FleurinpData structure<fleurinp_data>`
#. :ref:`Fleur code<fleurcode_plugin>`

The overall plugin for Fleur consists out of three AiiDA plugins. One for the Fleur input generator
(inpgen), one data structure (fleurinpData) representing the inp.xml file and a plugin for
the Fleur code (fleur, fleur_MPI).
Other codes from the Fleur family (GFleur) or which build on top (Spex) are
not supported.

The package also contains workflows

#. :ref:`Fleur base workchain<base_wc>`
#. :ref:`Self-Consistent Field<scf_wc>` (Scf)
#. :ref:`Density Of States<dos_band_wc>` (DOS)
#. :ref:`Structure optimization<relax_wc>` (relax)
#. :ref:`Band structure<dos_band_wc>`
#. :ref:`Equation of States<eos_wc>` (EOS)
#. :ref:`Initial corelevel shifts<init_cl_wc>`
#. :ref:`Corehole<corehole_wc>`
#. Force-theorem :ref:`Magnetic Anisotropy Energy<mae_wc>`
#. Force-theorem :ref:`Spin Spiral Dispersion<ssdisp_wc>`
#. Force-theorem :ref:`Dzjaloshinskii-Moriya Interaction energy dispersion<dmi_wc>`
#. Scf :ref:`Magnetic Anisotropy Energy<mae_conv_wc>`
#. Scf :ref:`Spin Spiral Dispersion<ssdisp_conv_wc>`

The package also contains AiiDA dependent tools around the workflows and plugins.
All tools independent on aiida-core are moved to the masci-tools repository,
to be available to other non AiiDA related projects and tools.

Acknowledgments:
================

We acknowledge partial support from the EU Centre of Excellence “MaX – Materials Design at the
Exascale” (http://www.max-centre.eu). (Horizon 2020 EINFRA-5, Grant No. 676598).
We thank the AiiDA team for their help and work. Also the vial exchange with developers of AiiDA
packages for other codes was inspiring.

************
User's Guide
************

Everything you need for using AiiDA-FLEUR

.. toctree::
   :maxdepth: 4

   user_guide/ug_index

*****************
Developer's Guide
*****************

Some things to notice for AiiDA-FLEUR developers.
Conventions, programming style, Integrated testing, things that should not be forgotten

.. toctree::
   :maxdepth: 4

   devel_guide/dg_index

**********************
Module reference (API)
**********************

Automatic generated documentation for all modules, classes and functions with
reference to the source code. The search is your friend.

.. toctree::
   :maxdepth: 4

   module_guide/mg_index
..   apidoc/aiida_fleur


******************
Indices and tables
******************

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`
