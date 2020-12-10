.. _eos_wc:

Fleur equation of states (eos) workflow
---------------------------------------

* **Current version**: 0.3.5
* **Class**: :py:class:`~aiida_fleur.workflows.eos.FleurEosWorkChain`
* **String to pass to the** :py:func:`~aiida.plugins.WorkflowFactory`: ``fleur.eos``
* **Workflow type**:  Technical
* **Aim**: Vary the cell volume, to fit an equation of states, (Bulk modulus, ...)

.. contents::

Import Example:

.. code-block:: python

    from aiida_fleur.workflows.eos import fleur_eos_wc
    #or
    WorkflowFactory('fleur.eos')

Description/Purpose
^^^^^^^^^^^^^^^^^^^

Calculates equation of states for a given crystal structure.

First, an input structure is scaled and a list of scaled structures is constructed.
Then, total energies of all the scaled structures are calculated via
:py:class:`~aiida_fleur.workflows.scf.FleurScfWorkChain` (:ref:`SCF<scf_wc>`). Finally,
resulting total energies are fitted via the Birch–Murnaghan
equation of state and the cell volume corresponding to the lowest energy is evaluated.
Other fit options are also available.


.. _exposed: https://aiida.readthedocs.io/projects/aiida-core/en/latest/working/workflows.html#working-workchains-expose-inputs-outputs

Input nodes
^^^^^^^^^^^
The :py:class:`~aiida_fleur.workflows.eos.FleurEosWorkChain` employs
`exposed`_ feature of the AiiDA-core, thus inputs for the
:ref:`SCF<scf_wc>` sub-workchain should be passed in the namespace called
``scf`` (see :ref:`example of usage<example_use_eos>`). Please note that the `structure` input node
is excluded from the `scf` namespace since the EOS workchain should process input structure before
performing energy calculations.

+-----------------+--------------------------------------+------------------------------------------------------------------+----------+
| name            | type                                 | description                                                      | required |
+=================+======================================+==================================================================+==========+
| scf             | namespace                            | inputs for nested SCF WorkChain. structure input is excluded     | no       |
+-----------------+--------------------------------------+------------------------------------------------------------------+----------+
| wf_parameters   | :py:class:`~aiida.orm.Dict`          | Settings of the workchain                                        | no       |
+-----------------+--------------------------------------+------------------------------------------------------------------+----------+
| structure       | :py:class:`~aiida.orm.StructureData` | input structure                                                  | no       |
+-----------------+--------------------------------------+------------------------------------------------------------------+----------+

Returns nodes
^^^^^^^^^^^^^

+-------------------------+----------------------------------------+--------------------------------------------------------------+
| name                    | type                                   | comment                                                      |
+=========================+========================================+==============================================================+
| output_eos_wc_para      | :py:class:`~aiida.orm.Dict`            | results of the workchain                                     |
+-------------------------+----------------------------------------+--------------------------------------------------------------+
| output_eos_wc_structure | :py:class:`~aiida.orm.StructureData`   | Crystal structure with the volume of the lowest total energy |
+-------------------------+----------------------------------------+--------------------------------------------------------------+

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


.. _example_use_eos:

Example usage
^^^^^^^^^^^^^
   .. literalinclude:: code/tutorial_submit_eos.py


Output node example
^^^^^^^^^^^^^^^^^^^
  .. include:: /images/eos_wc_outputnode.py
     :literal:

Error handling
^^^^^^^^^^^^^^

Total energy check:

The workflow quickly checks the behavior of the total energy for outliers.
Which might occur, because the chosen FLAPW parameters might not be good for
all volumes. Also local Orbital setup and so on might matter.

* Not enough points for fit
* Some calculations did not converge
* Volume ground state does not lie in the calculated interval, interval refinement

Exit codes
^^^^^^^^^^

A list of implemented :ref:`exit codes<exit_codes>`:

+------+------------------------------------------------------------------------------------------+
| Code | Meaning                                                                                  |
+======+==========================================================================================+
| 230  | Invalid workchain parameters                                                             |
+------+------------------------------------------------------------------------------------------+
