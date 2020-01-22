=================================
AiiDA-FLEUR Data Plugins
=================================

AiiDA-FLEUR data plugins include:

#. :py:class:`~aiida_fleur.data.fleurinp.FleurinpData` structure (:ref:`fleurinp_data`)
#. :py:class:`~aiida_fleur.data.fleurinpmodifier.FleurinpModifier` structure (:ref:`fleurinp_mod`)

:py:class:`~aiida_fleur.data.fleurinp.FleurinpData` is a
:py:class:`~aiida.orm.Data` type that represents input files needed for the FLEUR code and
methods to work with them. They include inp.xml and some other situational files.
Finally, :py:class:`~aiida_fleur.data.fleurinpmodifier.FleurinpModifier` consists of methods to
change existing :py:class:`~aiida_fleur.data.fleurinp.FleurinpData` in
a way to preserve data provenance.

.. toctree::
    :maxdepth: 4

    fleurinp_data
    fleurinp_modifier
