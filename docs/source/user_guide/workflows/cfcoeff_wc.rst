.. _cfcoeff_wc:

Fleur crystal field workflow
-------------------------------------

* **Current version**: 0.2.0
* **Class**: :py:class:`~aiida_fleur.workflows.cfcoeff.FleurCFCoeffWorkChain`
* **String to pass to the** :py:func:`~aiida.plugins.WorkflowFactory`: ``fleur.cfcoeff``
* **Workflow type**: Scientific workchain
* **Aim**: Calculate 4f Crystal field coefficients

.. contents::

Import Example:

.. code-block:: python

    from aiida_fleur.workflows.cfcoeff import FleurCFCoeffWorkChain
    #or
    WorkflowFactory('fleur.cfcoeff')

Description/Purpose
^^^^^^^^^^^^^^^^^^^

Calculates the 4f crystal field coefficients for a given structure using the method.
described in C.E. Patrick, J.B. Staunton: J. Phys.: Condens. Matter 31, 305901 (2019).

This method boils down to the formula

.. math::
    B_{lm} = \sqrt{\frac{2l+1}{4\pi}} \int^{R_{MT}}\! dr r^2 V_{lm}(r)n_{4f}(r)

where :math:`V_{lm}(r)` is the potential of the surroundings of the 4f site and
:math:`n_{4f}(r)` is the spherical charge density of the 4f state. The potential
is calculated using one of two options:

    1. Calculate the potential of an analogue structure, where the 4f atom is
       replaced by a ytrrium atom.
    2. Calculate the potential from the system including the 4f atom directly.

This is done by first calculating the converged charge density for the 4f structure
and if used the analogue structure with the FleurScfWorkChain. Then a subsequent calculation
is done to extract the potentials/charge density. The calculation of the formula above
is done after with the :py:class:`~masci_tools.tools.cf_calculation.CFCalculation` tool in `masci-tools`.

Input nodes
^^^^^^^^^^^

The table below shows all the possible input nodes of the SCF workchain.

+-------------------------+--------------------------------------+--------------------------------------------------------------------------+----------+
| name                    | type                                 | description                                                              | required |
+=========================+======================================+==========================================================================+==========+
| scf                     | namespace                            | Inputs for the SCF workchain including the 4f atom                       | no       |
+-------------------------+--------------------------------------+--------------------------------------------------------------------------+----------+
| orbcontrol              | namespace                            | Inputs for the Orbcontrol workchain including the 4f atom                | no       |
+-------------------------+--------------------------------------+--------------------------------------------------------------------------+----------+
| scf_rare_earth_analogue | namespace                            | Inputs for the SCF workchain with the 4f atom replaced with the analogue | no       |
+-------------------------+--------------------------------------+--------------------------------------------------------------------------+----------+
| wf_parameters           | :py:class:`~aiida.orm.Dict`          | Settings of the workchain                                                | no       |
+-------------------------+--------------------------------------+--------------------------------------------------------------------------+----------+

One of the `scf` or `orbcontrol` input nodes is required.

Workchain parameters and its defaults
.....................................

* ``wf_parameters``: :py:class:`~aiida.orm.Dict` - Settings of the workflow behavior. All possible
  keys and their defaults are listed below:

  .. literalinclude:: code/cfcoeff_parameters.py


Returns nodes
^^^^^^^^^^^^^

The table below shows all the possible output nodes of the SCF workchain.

+------------------------------------+-------------------------------+---------------------------------------------+
| name                               | type                          | comment                                     |
+====================================+===============================+=============================================+
| output_cfcoeff_wc_para             | :py:class:`~aiida.orm.Dict`   | results of the workchain                    |
+------------------------------------+-------------------------------+---------------------------------------------+
| output_cfcoeff_wc_potentials       | :py:class:`~aiida.orm.XyData` | XyData with the calculated potentials       |
+------------------------------------+-------------------------------+---------------------------------------------+
| output_cfcoeff_wc_charge_densities | :py:class:`~aiida.orm.XyData` | XyData with the calculated charge densities |
+------------------------------------+-------------------------------+---------------------------------------------+

.. _cfcoeff_wc_layout:

Layout
^^^^^^

TODO

Error handling
^^^^^^^^^^^^^^
In case of failure the SCF WorkChain should throw one of the :ref:`exit codes<exit_codes>`:

+-----------+----------------------------------------------+
| Exit code | Reason                                       |
+===========+==============================================+
| 230       | Invalid workchain parameters                 |
+-----------+----------------------------------------------+
| 231       | Invalid input configuration                  |
+-----------+----------------------------------------------+
| 235       | Input file modification failed.              |
+-----------+----------------------------------------------+
| 236       | Input file was corrupted after modifications |
+-----------+----------------------------------------------+
| 345       | SCF workchain failed                         |
+-----------+----------------------------------------------+
| 451       | Orbcontrol workchain failed                  |
+-----------+----------------------------------------------+
| 452       | FleurBaseWorkChain for CF calculation failed |
+-----------+----------------------------------------------+

If your workchain crashes and stops in *Excepted* state, please open a new issue on the Github page
and describe the details of the failure.

Plot_fleur visualization
^^^^^^^^^^^^^^^^^^^^^^^^
  TODO

Database Node graph
^^^^^^^^^^^^^^^^^^^
  TODO

Example usage
^^^^^^^^^^^^^
  TODO
