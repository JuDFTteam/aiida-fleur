.. _corehole_wc:

Fleur core-hole workflow
------------------------

Class name, import from:
  ::

    from aiida_fleur.workflows.corehole import FleurCoreholeWorkChain
    #or
    WorkflowFactory('fleur.corehole')

Description/Purpose
^^^^^^^^^^^^^^^^^^^
The core-hole workflow can be deployed to calculate absolute core-level binding energies.

Such core-hole calculations are performed through a super-cell setup. 
The workflow allows for arbitrary corehole charges and of valence and charged type core-holes. 
From a computational cost perspective it may be cheaper to calculate all relative initial-state 
shifts of a structure and then launch one core-hole calculation on the structure to get an 
absolute reference energy instead of performing expensive core-hole calculations 
for all atom-types in the structure.
The core-hole workflow implements the usual FLEUR workflow interface with a workflow 
control parameter node.


Layout
^^^^^^
  .. figure:: /images/Workchain_charts_corehole_wc.png
    :width: 50 %
    :align: center

Input nodes
^^^^^^^^^^^

+-----------------+----------------------------------------------------+-----------------------------------------+----------+
| name            | type                                               | description                             | required |
+=================+====================================================+=========================================+==========+
| inpgen          | :py:class:`~aiida.orm.Code`                        | Inpgen code                             | yes      |
+-----------------+----------------------------------------------------+-----------------------------------------+----------+
| fleur           | :py:class:`~aiida.orm.Code`                        | Fleur code                              | yes      |
+-----------------+----------------------------------------------------+-----------------------------------------+----------+
| wf_parameters   | :py:class:`~aiida.orm.Dict`                        | Settings of the workchain               | no       |
+-----------------+----------------------------------------------------+-----------------------------------------+----------+
| fleurinp        | :py:class:`~aiida_fleur.data.fleurinp.FleurinpData`| :ref:`FLEUR input<fleurinp_data>`       | no       |
+-----------------+----------------------------------------------------+-----------------------------------------+----------+
| structure       | :py:class:`~aiida.orm.StructureData`               | Crystal structure                       | no       |
+-----------------+----------------------------------------------------+-----------------------------------------+----------+
| calc_parameters | :py:class:`~aiida.orm.Dict`                        | FLAPW parameters for given structure    | no       |
+-----------------+----------------------------------------------------+-----------------------------------------+----------+
| options         | :py:class:`~aiida.orm.Dict`                        | AiiDA options (computational resources) | no       |
+-----------------+----------------------------------------------------+-----------------------------------------+----------+

More details:
  * ``fleur`` (*aiida.orm.Code*): Fleur code using the ``fleur.fleur`` plugin
  * ``inpgen`` (*aiida.orm.Code*): Inpgen code using the ``fleur.inpgen`` plugin
  * ``wf_parameters`` (*Dict*, optional): Some settings of the workflow behavior 

  * ``structure`` (*StructureData*, path 1): Crystal structure data node.
  * ``calc_parameters`` (*Dict*, optional): Longer description of the workflow

  * ``fleurinp`` (*FleurinpData*, path 2): Label of the workflow


Workchain parameters and its defaults
.....................................

``wf_parameters``
,,,,,,,,,,,,,,,,,

``wf_parameters``: :py:class:`~aiida.orm.Dict` - Settings of the workflow behavior. All possible
keys and their defaults are listed below:

.. literalinclude:: code/corehole_parameters.py

``options``
,,,,,,,,,,,

``options``: :py:class:`~aiida.orm.Dict` - AiiDA options (computational resources).
Example:

.. code-block:: python

      'resources': {"num_machines": 1, "num_mpiprocs_per_machine": 1},
      'max_wallclock_seconds': 6*60*60,
      'queue_name': '',
      'custom_scheduler_commands': '',
      'import_sys_environment': False,
      'environment_variables': {}

Returns nodes
^^^^^^^^^^^^^
  * ``output_corehole_wc_para`` (*Dict*): Information of workchain results

More details:

  * ``output_corehole_wc_para``: :py:class:`~aiida.orm.Dict` -  Main results of the workchain. Contains
    Binding energies, band gaps, core-levels, atom-type information, 
    errors, warnings, other information. An example:

    .. literalinclude:: code/corehole_wc_outputnode.py


Database Node graph
^^^^^^^^^^^^^^^^^^^
  .. code-block:: python

    from aiida_fleur.tools.graph_fleur import draw_graph

    draw_graph(30528)

  .. figure:: /images/corehole_si_30528.pdf
    :width: 100 %
    :align: center

Plot_fleur visualization
^^^^^^^^^^^^^^^^^^^^^^^^
  Currently there is no visualization directly implemented for plot fleur.
  Through there in masci-tools there are methods to visualize spectra and binding energies

Example usage
^^^^^^^^^^^^^
  .. include:: code/corehole_submission.py
     :literal:

Error handling
^^^^^^^^^^^^^^
  Still has to be documented
