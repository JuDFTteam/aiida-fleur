=================================
AiiDA FLEUR Code and Data Plugins
=================================

Layout:

#. Fleur input generator (:ref:`inpgen_plugin`)
#. FleurinpData structure (:ref:`fleurinp_data`)
#. Fleur code (:ref:`fleurcode_plugin`)

The overall plugin for Fleur consists out of three AiiDA plugins. One for the Fleur input generator (inpgen), one datastructure (:py:class:`~aiida_fleur.data.fleurinp.FleurinpData`) representing the inp.xml file and a plugin for the Fleur code (fleur, fleur_MPI). See www.flapw.de.
Other codes from the Fleur family (GFleur) or which build ontop (Spex) are
not supported.

.. toctree::
    :maxdepth: 4

    inpgen_plugin
    fleurinp_data
    fleurcode_plugin
