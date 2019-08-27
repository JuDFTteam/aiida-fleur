=================================
AiiDA-FLEUR Code and Data Plugins
=================================

AiiDA-FLEUR plugin consists of three main parts:

#. FLEUR input generator (:ref:`inpgen_plugin`)
#. FleurinpData structure (:ref:`fleurinp_data`)
#. Fleurinpmodifier structure (:ref:`fleurinp_mod`)
#. FLEUR code (:ref:`fleurcode_plugin`)

Fleur input generator represents inpgen code, FLEUR code represents fleur and fleur_MPI codes.
FleurinpData is a DataStructure type that represents input files needed for the FLEUR code and
methods to work with them. They include inp.xml and some other situational files.
Finally, Fleurinpmodifier consists of methods to change existing FleurinpData in a way to
preserve data provinance.

Other codes from the Fleur family (GFleur) or which are built on top of FLEUR (Spex) are
not supported yet.

.. toctree::
    :maxdepth: 4

    inpgen_plugin
    fleurinp_data
    fleurcode_plugin
