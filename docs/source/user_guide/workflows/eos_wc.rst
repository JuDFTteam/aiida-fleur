.. _eos_wc:

Fleur equation of states (eos) workflow
---------------------------------------

* **Current version**: 0.3.4
* **Class**: :py:class:`~aiida_fleur.workflows.eos.FleurEosWorkChain`
* **String to pass to the** :py:func:`~aiida.plugins.WorkflowFactory`: ``fleur.eos``
* **Workflow type**:  Technical
* **Aim**: Vary the cell volume, to fit an equation of states, (Bulk modulus, ...)
* **Computational demand**: 5-10 ``Fleur SCF workchains`` in parallel
* **Database footprint**: Outputnode with information, full provenance, ``~ (10+10*FLEUR Jobs)*points`` nodes
* **File repository footprint**: no addition to the ``JobCalculations`` run

.. contents::

Import Example:

.. code-block:: python

    from aiida_fleur.workflows.eos import fleur_eos_wc
    #or
    WorkflowFactory('fleur.eos')

Description/Purpose
^^^^^^^^^^^^^^^^^^^
  Calculates an equation of state for a given crystal structure.

  First, an input structure is scaled and a list of scaled structures is constructed.
  Then, total energies of all the scaled structures are calculated via
  ``FleurScfWorkChain``. Finally, resulting total energies are fitted via the Birch–Murnaghan
  equation of state and the cell volume corresponding to the lowest energy is evaluated.
  Other fit options are also available.

  * ``fleur``: :py:class:`~aiida.orm.Code` - Fleur code using the ``fleur.fleur`` plugin
  * ``inpgen``: :py:class:`~aiida.orm.Code`, optional - Inpgen code using the ``fleur.inpgen``
    plugin
  * ``wf_parameters``: :py:class:`~aiida.orm.Dict`, optional - Settings
    of the workflow behavior
  * ``structure``: :py:class:`~aiida.orm.StructureData`, optional: Crystal structure
    data node.
  * ``calc_parameters``: :py:class:`~aiida.orm.Dict`, optional -
    FLAPW parameters, used by inpgen
  * ``fleurinp``: :py:class:`~aiida_fleur.data.fleurinp.FleurinpData`, optional: Fleur input data
    object representing the FLEUR input files
  * ``remote_data``: :py:class:`~aiida.orm.RemoteData`, optional - The remote folder of
    the previous calculation
  * ``options``: :py:class:`~aiida.orm.Dict`, optional - AiiDA options
    (queues, cpus)
  * ``settings``: :py:class:`~aiida.orm.Dict`, optional - special settings
    for Fleur calculations.

Returns nodes
^^^^^^^^^^^^^
  * ``output_eos_wc_para``: :py:class:`~aiida.orm.Dict` - Information of
    workflow results like success, list with convergence behavior
  * ``output_eos_wc_structure``: :py:class:`~aiida.orm.StructureData` - Crystal
    structure with the volume of the lowest total energy.

Layout
^^^^^^
  .. figure:: /images/Workchain_charts_eos_wc.png
    :width: 50 %
    :align: center

Database Node graph
^^^^^^^^^^^^^^^^^^^
  .. code-block:: python

    from aiida_fleur.tools.graph_fleur import draw_graph

    draw_graph(49670)

  .. figure:: /images/eos_49670.pdf
    :width: 100 %
    :align: center

Plot_fleur visualization
^^^^^^^^^^^^^^^^^^^^^^^^
  Single node

  .. code-block:: python

    from aiida_fleur.tools.plot import plot_fleur

    plot_fleur(49670)

  .. figure:: /images/plot_fleur_eos_sn.png
    :width: 60 %
    :align: center

  Multi node

  .. code-block:: python

    from aiida_fleur.tools.plot import plot_fleur

    plot_fleur(eos_pk_list)

  .. figure:: /images/plot_fleur_eos_mn.png
    :width: 60 %
    :align: center


Example usage
^^^^^^^^^^^^^
  .. include:: ../../../../examples/tutorial/workflows/tutorial_submit_eos.py
     :literal:


Output node example
^^^^^^^^^^^^^^^^^^^
  .. include:: /images/eos_wc_outputnode.py
     :literal:

Error handling
^^^^^^^^^^^^^^
  Still has to be documented...

  Total energy check:

  The workflow quickly checks the behavior of the total energy for outliers.
  Which might occur, because the chosen FLAPW parameters might not be good for
  all volumes. Also local Orbital setup and so on might matter.

  * Not enough points for fit
  * Some calculations did not converge
  * Volume ground state does not lie in the calculated interval, interval refinement

